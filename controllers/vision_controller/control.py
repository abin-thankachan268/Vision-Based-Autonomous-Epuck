"""Closed-loop lane control and safety-oriented navigation state machine."""

from __future__ import annotations

from dataclasses import dataclass

from .config import ControllerConfig
from .models import ControlCommand, ControllerState, ObstacleMotion, PerceptionResult


@dataclass
class PID:
    kp: float
    ki: float
    kd: float
    integral_limit: float
    integral: float = 0.0
    previous_error: float = 0.0

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = 0.0

    def update(self, error: float, dt: float) -> float:
        safe_dt = max(dt, 1e-3)
        self.integral += error * safe_dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        derivative = (error - self.previous_error) / safe_dt
        self.previous_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative


class VisionControllerCore:
    """Pure control core that has no dependency on Webots or Supervisor data."""

    def __init__(self, config: ControllerConfig | None = None):
        self.config = config or ControllerConfig()
        control = self.config.control
        self.pid = PID(control.kp, control.ki, control.kd, control.integral_limit)
        self.state = ControllerState.FOLLOW_LANE
        self.state_elapsed = 0.0
        self.lost_lane_count = 0
        self.clear_obstacle_count = 0
        self.rejoin_confirm_count = 0
        self.stationary_obstacle_count = 0
        self.last_lane_error = 0.0
        self.avoidance_direction = 1.0
        self.avoidance_track_ids: set[int] = set()
        self.avoidance_colors: set[str] = set()

    def _transition(self, state: ControllerState) -> None:
        if state == self.state:
            return
        self.state = state
        self.state_elapsed = 0.0
        self.clear_obstacle_count = 0
        self.rejoin_confirm_count = 0
        self.stationary_obstacle_count = 0
        if state in (ControllerState.REJOIN, ControllerState.FAILSAFE, ControllerState.FINISHED):
            self.pid.reset()
        if state != ControllerState.AVOID:
            self.avoidance_track_ids.clear()
            self.avoidance_colors.clear()

    def _bounded(self, value: float) -> float:
        maximum = self.config.control.maximum_speed
        return max(-maximum, min(maximum, value))

    @staticmethod
    def _visible_obstacles(result: PerceptionResult):
        if result.obstacles:
            return tuple(obstacle for obstacle in result.obstacles if obstacle.present)
        return (result.obstacle,) if result.obstacle.present else ()

    @staticmethod
    def _has_unclassified_or_moving(obstacles) -> bool:
        return any(
            obstacle.motion in (ObstacleMotion.UNKNOWN, ObstacleMotion.MOVING)
            for obstacle in obstacles
        )

    def _choose_avoidance_direction(self, result: PerceptionResult) -> float:
        obstacles = self._visible_obstacles(result)
        image_center = max(result.frame_width / 2.0, 1.0)
        if not obstacles:
            return self.avoidance_direction
        left_edge = min(
            obstacle.bbox[0]
            for obstacle in obstacles
            if obstacle.bbox is not None
        )
        right_edge = max(
            obstacle.bbox[0] + obstacle.bbox[2]
            for obstacle in obstacles
            if obstacle.bbox is not None
        )
        free_left = max(0.0, left_edge)
        free_right = max(0.0, result.frame_width - right_edge)
        if abs(free_left - free_right) > result.frame_width * 0.05:
            return 1.0 if free_right > free_left else -1.0
        obstacle_x = (
            result.obstacle.centroid[0]
            if result.obstacle.centroid is not None
            else image_center
        )
        return 1.0 if obstacle_x <= image_center else -1.0

    def _start_avoidance(self, result: PerceptionResult) -> None:
        self._transition(ControllerState.AVOID)
        self.avoidance_track_ids = {
            obstacle.track_id
            for obstacle in self._visible_obstacles(result)
            if obstacle.track_id >= 0 and obstacle.motion == ObstacleMotion.STATIONARY
        }
        self.avoidance_colors = {
            obstacle.observed_color
            for obstacle in self._visible_obstacles(result)
            if obstacle.motion == ObstacleMotion.STATIONARY
        }
        self.avoidance_direction = self._choose_avoidance_direction(result)

    def _lane_command(self, result: PerceptionResult, speed: float, dt: float, reason: str) -> ControlCommand:
        raw_error = result.lane.normalized_error
        error = 0.0 if abs(raw_error) <= self.config.control.steering_deadband else raw_error
        correction = self.pid.update(error, dt)
        self.last_lane_error = raw_error
        return ControlCommand(
            left_speed=self._bounded(speed + correction),
            right_speed=self._bounded(speed - correction),
            state=self.state,
            reason=reason,
        )

    def step(
        self,
        result: PerceptionResult,
        dt: float,
        finish_detected: bool = False,
    ) -> ControlCommand:
        control = self.config.control
        self.state_elapsed += max(dt, 0.0)

        if finish_detected and self.state not in (ControllerState.FAILSAFE, ControllerState.FINISHED):
            self._transition(ControllerState.FINISHED)

        if self.state == ControllerState.FINISHED:
            return ControlCommand(0.0, 0.0, self.state, "finish reached")
        if self.state == ControllerState.FAILSAFE:
            return ControlCommand(0.0, 0.0, self.state, "failsafe stop")

        obstacle = result.obstacle
        obstacles = self._visible_obstacles(result)
        lane_confident = result.lane.confidence >= self.config.perception.minimum_lane_confidence

        if self.state == ControllerState.FOLLOW_LANE:
            if obstacles:
                if result.path_blocked or self._has_unclassified_or_moving(obstacles):
                    self._transition(ControllerState.STOP_WAIT)
                elif obstacle.motion == ObstacleMotion.STATIONARY:
                    self._start_avoidance(result)
                else:
                    self._transition(ControllerState.STOP_WAIT)
            elif not lane_confident:
                self.lost_lane_count += 1
                if self.lost_lane_count >= control.lost_lane_frames:
                    self._transition(ControllerState.REJOIN)
            else:
                self.lost_lane_count = 0

            if self.state == ControllerState.FOLLOW_LANE:
                speed = control.cruise_speed if result.lane.confidence >= 0.65 else control.cautious_speed
                return self._lane_command(result, speed, dt, "camera lane following")

        if self.state == ControllerState.STOP_WAIT:
            if result.path_blocked:
                self.clear_obstacle_count = 0
                self.stationary_obstacle_count = 0
            elif obstacles:
                self.clear_obstacle_count = 0
                if not self._has_unclassified_or_moving(obstacles):
                    self.stationary_obstacle_count += 1
                    if self.stationary_obstacle_count >= control.stationary_confirm_frames:
                        self._start_avoidance(result)
                else:
                    self.stationary_obstacle_count = 0
            else:
                self.clear_obstacle_count += 1
                if self.clear_obstacle_count >= control.clear_obstacle_frames:
                    self._transition(ControllerState.REJOIN)
            if (
                self.state == ControllerState.STOP_WAIT
                and self.state_elapsed >= control.stop_wait_timeout_seconds
            ):
                self._transition(ControllerState.FAILSAFE)
            if self.state == ControllerState.STOP_WAIT:
                reason = (
                    "multiple obstacles block the visible lane"
                    if result.path_blocked
                    else "waiting for moving or unclassified obstacles to clear"
                )
                return ControlCommand(0.0, 0.0, self.state, reason)

        if self.state == ControllerState.AVOID:
            unexpected_moving = any(
                obstacle.track_id not in self.avoidance_track_ids
                and obstacle.observed_color not in self.avoidance_colors
                and obstacle.motion in (ObstacleMotion.UNKNOWN, ObstacleMotion.MOVING)
                for obstacle in obstacles
            )
            if result.path_blocked or unexpected_moving:
                self._transition(ControllerState.STOP_WAIT)
                return ControlCommand(
                    0.0,
                    0.0,
                    self.state,
                    "new moving or blocking obstacle detected during avoidance",
                )
            if obstacles and self.state_elapsed <= max(dt, 0.0) + 1e-9:
                self.avoidance_direction = self._choose_avoidance_direction(result)

            committed = self.state_elapsed >= control.avoidance_commit_seconds
            if committed and not obstacles:
                self.clear_obstacle_count += 1
                if self.clear_obstacle_count >= control.clear_obstacle_frames:
                    self._transition(ControllerState.REJOIN)
            elif obstacles:
                self.clear_obstacle_count = 0
            if self.state_elapsed >= control.avoidance_timeout_seconds:
                self._transition(ControllerState.FAILSAFE)
            if self.state == ControllerState.AVOID:
                direction = self.avoidance_direction
                if self.state_elapsed >= control.avoidance_leg_seconds:
                    direction *= -1.0
                turn = control.avoidance_turn_speed * direction
                return ControlCommand(
                    self._bounded(control.cautious_speed + turn),
                    self._bounded(control.cautious_speed - turn),
                    self.state,
                    "camera-guided stationary obstacle avoidance",
                )

        if self.state == ControllerState.REJOIN:
            if obstacles:
                if result.path_blocked or self._has_unclassified_or_moving(obstacles):
                    self._transition(ControllerState.STOP_WAIT)
                elif obstacle.motion == ObstacleMotion.STATIONARY:
                    self._start_avoidance(result)
                else:
                    self._transition(ControllerState.STOP_WAIT)
                return ControlCommand(0.0, 0.0, self.state, "obstacle detected during rejoin")

            if lane_confident:
                self.rejoin_confirm_count += 1
                if self.rejoin_confirm_count >= control.rejoin_confirm_frames:
                    self._transition(ControllerState.FOLLOW_LANE)
                    return self._lane_command(result, control.cautious_speed, dt, "lane reacquired")
                return self._lane_command(result, control.cautious_speed, dt, "confirming lane reacquisition")

            self.rejoin_confirm_count = 0
            if self.state_elapsed >= control.rejoin_timeout_seconds:
                self._transition(ControllerState.FAILSAFE)
                return ControlCommand(0.0, 0.0, self.state, "lane recovery timeout")
            direction = 1.0 if self.last_lane_error >= 0.0 else -1.0
            search = control.search_turn_speed * direction
            return ControlCommand(search, -search, self.state, "searching for lane")

        return ControlCommand(0.0, 0.0, self.state, "safe default stop")
