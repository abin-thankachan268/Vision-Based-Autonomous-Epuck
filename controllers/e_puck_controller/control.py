"""PD lane steering and a small, explainable navigation state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .vision import MotionClass, SceneObservation


class NavigationState(str, Enum):
    FOLLOW_LANE = "FOLLOW_LANE"
    STOP_WAIT = "STOP_WAIT"
    AVOID = "AVOID"
    REJOIN = "REJOIN"
    FINISHED = "FINISHED"
    FAILSAFE = "FAILSAFE"


@dataclass(frozen=True)
class ControlConfig:
    maximum_speed: float = 6.28
    cruise_speed: float = 4.2
    cautious_speed: float = 2.2
    kp: float = 7.2
    kd: float = 0.055
    steering_deadband: float = 0.008
    maximum_steering_correction: float = 2.0
    minimum_lane_confidence: float = 0.65
    lost_lane_frames: int = 5
    clear_frames: int = 8
    rejoin_confirm_frames: int = 5
    rejoin_timeout_seconds: float = 10.0
    stop_wait_timeout_seconds: float = 18.0
    avoidance_timeout_seconds: float = 9.0
    avoidance_first_leg_seconds: float = 0.75
    avoidance_straight_seconds: float = 0.95
    avoidance_commit_seconds: float = 2.45
    avoidance_turn_speed: float = 0.95
    search_turn_speed: float = 0.55
    rejoin_forward_speed: float = 1.60
    rejoin_manoeuvre_speed: float = 2.5
    rejoin_turn_seconds: float = 1.0
    rejoin_straight_seconds: float = 1.5
    proximity_danger_threshold: float = 180.0
    proximity_clear_threshold: float = 120.0
    proximity_emergency_threshold: float = 700.0
    proximity_pause_seconds: float = 0.25
    post_avoidance_grace_seconds: float = 4.0
    handled_obstacle_clear_frames: int = 90
    minimum_finish_time_seconds: float = 5.0


@dataclass(frozen=True)
class MotorCommand:
    left_speed: float
    right_speed: float
    state: NavigationState
    reason: str


class PDController:
    """Proportional-derivative steering with no integral accumulation."""

    def __init__(self, kp: float, kd: float):
        self.kp = float(kp)
        self.kd = float(kd)
        self.previous_error = 0.0
        self.has_previous = False

    def reset(self) -> None:
        self.previous_error = 0.0
        self.has_previous = False

    def update(self, error: float, dt: float) -> float:
        safe_dt = max(float(dt), 1e-3)
        derivative = (error - self.previous_error) / safe_dt if self.has_previous else 0.0
        self.previous_error = error
        self.has_previous = True
        return self.kp * error + self.kd * derivative


class SimpleNavigator:
    """Camera-first controller using proximity only for close-range safety."""

    def __init__(self, config: ControlConfig | None = None):
        self.config = config or ControlConfig()
        self.pd = PDController(self.config.kp, self.config.kd)
        self.state = NavigationState.FOLLOW_LANE
        self.state_elapsed = 0.0
        self.lost_lane_count = 0
        self.clear_count = 0
        self.rejoin_count = 0
        self.last_lane_error = 0.0
        self.avoidance_direction = 1.0
        self.rejoin_direction = 1.0
        self.proximity_grace_remaining = 0.0
        self.ignore_red_obstacle = False
        self.ignored_red_clear_count = 0
        self.rejoining_after_avoidance = False

    def _transition(self, state: NavigationState) -> None:
        if state == self.state:
            return
        previous_state = self.state
        self.state = state
        self.state_elapsed = 0.0
        self.clear_count = 0
        self.rejoin_count = 0
        if state in (NavigationState.REJOIN, NavigationState.FINISHED, NavigationState.FAILSAFE):
            self.pd.reset()
        if state == NavigationState.REJOIN:
            # After avoidance, steer back toward the lane instead of spinning
            # farther toward the side selected for the bypass.
            self.rejoin_direction = (
                -self.avoidance_direction
                if previous_state == NavigationState.AVOID
                else (
                    0.0
                    if abs(self.last_lane_error) <= self.config.steering_deadband
                    else (1.0 if self.last_lane_error > 0.0 else -1.0)
                )
            )
            if previous_state == NavigationState.AVOID:
                self.rejoining_after_avoidance = True
                self.proximity_grace_remaining = self.config.post_avoidance_grace_seconds
                self.ignore_red_obstacle = True
                self.ignored_red_clear_count = 0
        elif state == NavigationState.FOLLOW_LANE:
            self.rejoining_after_avoidance = False

    def _bounded(self, value: float) -> float:
        return max(-self.config.maximum_speed, min(self.config.maximum_speed, value))

    @staticmethod
    def _readings(values) -> tuple[float, ...]:
        if len(values) != 8:
            raise ValueError("eight e-puck proximity readings are required")
        return tuple(max(0.0, float(value)) for value in values)

    @staticmethod
    def _proximity_summary(readings: tuple[float, ...]) -> tuple[float, float, float, float]:
        # ps0/ps1 are front-right, ps6/ps7 front-left, ps2/ps5 the flanks.
        right = readings[0] + 0.75 * readings[1] + 0.20 * readings[2]
        left = readings[7] + 0.75 * readings[6] + 0.20 * readings[5]
        front_peak = max(readings[0], readings[1], readings[6], readings[7])
        side_peak = max(readings[2], readings[5])
        return left, right, front_peak, side_peak

    def _turn_away_from_proximity(self, left_energy: float, right_energy: float) -> float:
        if abs(left_energy - right_energy) < 1e-6:
            return self.avoidance_direction
        return 1.0 if left_energy > right_energy else -1.0

    def _choose_camera_direction(self, scene: SceneObservation) -> float:
        if scene.obstacle.centroid is None or scene.obstacle.bbox is None:
            return self.avoidance_direction
        obstacle_x, _obstacle_y, obstacle_width, _obstacle_height = scene.obstacle.bbox
        lane_left = scene.lane.left_x if scene.lane.left_x is not None else 0.0
        lane_right = (
            scene.lane.right_x
            if scene.lane.right_x is not None
            else float(scene.frame_width)
        )
        free_left = max(0.0, float(obstacle_x) - lane_left)
        free_right = max(0.0, lane_right - float(obstacle_x + obstacle_width))
        clearance_margin = max(8.0, scene.frame_width * 0.04)
        if free_right > free_left + clearance_margin:
            return 1.0
        if free_left > free_right + clearance_margin:
            return -1.0
        # The circuit is travelled counter-clockwise. On an approximately
        # centred obstacle, prefer the inside (left) shoulder so that a small
        # error cannot send the robot across the outer edge of the arena.
        return -1.0

    def _start_avoidance(self, scene: SceneObservation) -> None:
        self.avoidance_direction = self._choose_camera_direction(scene)
        self._transition(NavigationState.AVOID)

    def _lane_command(self, scene: SceneObservation, speed: float, dt: float, reason: str) -> MotorCommand:
        raw_error = scene.lane.error
        error = 0.0 if abs(raw_error) <= self.config.steering_deadband else raw_error
        correction = self.pd.update(error, dt)
        correction_limit = min(
            self.config.maximum_steering_correction,
            max(0.0, speed * 0.75),
        )
        correction = max(-correction_limit, min(correction_limit, correction))
        self.last_lane_error = raw_error
        return MotorCommand(
            self._bounded(speed + correction),
            self._bounded(speed - correction),
            self.state,
            reason,
        )

    def step(
        self,
        scene: SceneObservation,
        proximity_values,
        dt: float,
        finish_detected: bool = False,
    ) -> MotorCommand:
        readings = self._readings(proximity_values)
        left_energy, right_energy, front_peak, side_peak = self._proximity_summary(readings)
        proximity_danger = max(front_peak, side_peak) >= self.config.proximity_danger_threshold
        proximity_clear = max(front_peak, side_peak) <= self.config.proximity_clear_threshold
        self.state_elapsed += max(float(dt), 0.0)
        self.proximity_grace_remaining = max(
            0.0, self.proximity_grace_remaining - max(float(dt), 0.0)
        )

        if finish_detected and self.state not in (NavigationState.FINISHED, NavigationState.FAILSAFE):
            self._transition(NavigationState.FINISHED)
        if self.state == NavigationState.FINISHED:
            return MotorCommand(0.0, 0.0, self.state, "finish marker reached")
        if self.state == NavigationState.FAILSAFE:
            return MotorCommand(0.0, 0.0, self.state, "failsafe stop")

        obstacle = scene.obstacle
        if self.ignore_red_obstacle:
            if obstacle.present and obstacle.color == "red":
                self.ignored_red_clear_count = 0
            else:
                self.ignored_red_clear_count += 1
                if self.ignored_red_clear_count >= self.config.handled_obstacle_clear_frames:
                    self.ignore_red_obstacle = False
                    self.ignored_red_clear_count = 0
        obstacle_blocking = obstacle.present and not (
            self.ignore_red_obstacle and obstacle.color == "red"
        )
        proximity_blocking = proximity_danger and (
            self.proximity_grace_remaining <= 0.0
            or front_peak >= self.config.proximity_emergency_threshold
        )
        lane_visible = (
            scene.lane.visible
            and scene.lane.confidence >= self.config.minimum_lane_confidence
        )

        if self.state == NavigationState.FOLLOW_LANE:
            if obstacle_blocking:
                if obstacle.color == "blue" or obstacle.motion in (
                    MotionClass.MOVING,
                    MotionClass.UNKNOWN,
                ):
                    self._transition(NavigationState.STOP_WAIT)
                elif obstacle.motion == MotionClass.STATIONARY:
                    self._start_avoidance(scene)
            elif proximity_blocking:
                # A close object outside the useful camera angle causes a safe stop.
                self._transition(NavigationState.STOP_WAIT)
            elif not lane_visible:
                self.lost_lane_count += 1
                if self.lost_lane_count >= self.config.lost_lane_frames:
                    self._transition(NavigationState.REJOIN)
            else:
                self.lost_lane_count = 0
            if self.state == NavigationState.FOLLOW_LANE:
                speed = self.config.cruise_speed if scene.lane.confidence >= 0.65 else self.config.cautious_speed
                return self._lane_command(scene, speed, dt, "PD lane following")

        if self.state == NavigationState.STOP_WAIT:
            if (
                obstacle_blocking
                and obstacle.color != "blue"
                and obstacle.motion == MotionClass.STATIONARY
            ):
                self._start_avoidance(scene)
            elif obstacle_blocking or proximity_blocking:
                self.clear_count = 0
                if (
                    not obstacle_blocking
                    and proximity_blocking
                    and self.state_elapsed >= self.config.proximity_pause_seconds
                ):
                    # First stop, then use the sensor imbalance to escape a
                    # close object that has moved outside the camera ROI.
                    self.avoidance_direction = self._turn_away_from_proximity(
                        left_energy, right_energy
                    )
                    self._transition(NavigationState.AVOID)
            elif proximity_clear:
                self.clear_count += 1
                if self.clear_count >= self.config.clear_frames:
                    self._transition(NavigationState.REJOIN)
            if self.state == NavigationState.STOP_WAIT:
                if self.state_elapsed >= self.config.stop_wait_timeout_seconds:
                    self._transition(NavigationState.FAILSAFE)
                    return MotorCommand(0.0, 0.0, self.state, "obstacle wait timeout")
                return MotorCommand(
                    0.0,
                    0.0,
                    self.state,
                    "moving/unclassified object or proximity danger: stop and wait",
                )

        if self.state == NavigationState.AVOID:
            if obstacle.present and obstacle.color == "blue":
                self._transition(NavigationState.STOP_WAIT)
                return MotorCommand(0.0, 0.0, self.state, "moving object detected during avoidance")
            if self.state_elapsed >= self.config.avoidance_timeout_seconds:
                self._transition(NavigationState.FAILSAFE)
                return MotorCommand(0.0, 0.0, self.state, "avoidance timeout")
            if front_peak >= self.config.proximity_emergency_threshold:
                self.avoidance_direction = self._turn_away_from_proximity(
                    left_energy, right_energy
                )
                turn = 0.70 * self.avoidance_direction
                rear_peak = max(readings[3], readings[4])
                if rear_peak < self.config.proximity_emergency_threshold:
                    return MotorCommand(
                        self._bounded(-1.20 + turn),
                        self._bounded(-1.20 - turn),
                        self.state,
                        "emergency proximity reverse-turn",
                    )
                return MotorCommand(
                    self._bounded(turn),
                    self._bounded(-turn),
                    self.state,
                    "emergency proximity pivot; rear blocked",
                )
            if front_peak >= self.config.proximity_danger_threshold:
                self.avoidance_direction = self._turn_away_from_proximity(left_energy, right_energy)
                direction = self.avoidance_direction
                return MotorCommand(
                    self._bounded(0.75 + 1.65 * direction),
                    self._bounded(0.75 - 1.65 * direction),
                    self.state,
                    "proximity-guided turn around stationary obstacle",
                )
            if self.state_elapsed >= self.config.avoidance_commit_seconds and not obstacle.present:
                self.clear_count += 1
                if self.clear_count >= self.config.clear_frames:
                    self._transition(NavigationState.REJOIN)
            else:
                self.clear_count = 0
            if self.state == NavigationState.AVOID:
                turn_out_end = self.config.avoidance_first_leg_seconds
                straight_end = turn_out_end + self.config.avoidance_straight_seconds
                manoeuvre_end = straight_end + self.config.avoidance_first_leg_seconds
                if self.state_elapsed < turn_out_end:
                    direction = self.avoidance_direction
                elif self.state_elapsed < straight_end:
                    direction = 0.0
                elif self.state_elapsed < manoeuvre_end:
                    direction = -self.avoidance_direction
                else:
                    direction = 0.0
                turn = self.config.avoidance_turn_speed * direction
                return MotorCommand(
                    self._bounded(self.config.cautious_speed + turn),
                    self._bounded(self.config.cautious_speed - turn),
                    self.state,
                    "road-constrained S-curve stationary-obstacle avoidance",
                )

        if self.state == NavigationState.REJOIN:
            if obstacle_blocking:
                if obstacle.color != "blue" and obstacle.motion == MotionClass.STATIONARY:
                    self._start_avoidance(scene)
                else:
                    self._transition(NavigationState.STOP_WAIT)
                return MotorCommand(0.0, 0.0, self.state, "obstacle encountered while rejoining")
            # Re-evaluate this condition here because AVOID can transition to
            # REJOIN earlier in the same step and start its proximity grace
            # period. Reusing the pre-transition boolean caused an immediate,
            # unnecessary STOP_WAIT while the cleared obstacle was alongside.
            rejoin_proximity_blocking = proximity_danger and (
                self.proximity_grace_remaining <= 0.0
                or front_peak >= self.config.proximity_emergency_threshold
            )
            if rejoin_proximity_blocking:
                self._transition(NavigationState.STOP_WAIT)
                return MotorCommand(0.0, 0.0, self.state, "proximity danger while rejoining")
            strict_lane_visible = lane_visible and (
                scene.lane.left_x is not None and scene.lane.right_x is not None
            )
            lane_ready = strict_lane_visible if self.rejoining_after_avoidance else lane_visible
            if lane_ready:
                self.rejoin_count += 1
                if self.rejoin_count >= self.config.rejoin_confirm_frames:
                    self._transition(NavigationState.FOLLOW_LANE)
                    return self._lane_command(scene, self.config.cautious_speed, dt, "lane reacquired")
                return self._lane_command(scene, self.config.cautious_speed, dt, "confirming lane")
            self.rejoin_count = 0
            if self.rejoining_after_avoidance and scene.lane.visible:
                return self._lane_command(
                    scene,
                    self.config.rejoin_forward_speed,
                    dt,
                    "single-boundary guidance during rejoin",
                )
            if self.state_elapsed >= self.config.rejoin_timeout_seconds:
                self._transition(NavigationState.FAILSAFE)
                return MotorCommand(0.0, 0.0, self.state, "lane recovery timeout")
            if self.rejoining_after_avoidance:
                search = self.config.search_turn_speed * self.rejoin_direction
                return MotorCommand(
                    self._bounded(self.config.rejoin_forward_speed + search),
                    self._bounded(self.config.rejoin_forward_speed - search),
                    self.state,
                    "curved search toward lane after avoidance",
                )
            search = self.config.search_turn_speed * self.rejoin_direction
            return MotorCommand(
                self._bounded(self.config.rejoin_forward_speed + search),
                self._bounded(self.config.rejoin_forward_speed - search),
                self.state,
                "forward arc toward lane",
            )

        return MotorCommand(0.0, 0.0, self.state, "safe default stop")
