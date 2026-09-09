"""Pure proximity-sensor safety overlay for camera-derived motor commands."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.vision_controller.models import ControlCommand, ControllerState


@dataclass(frozen=True)
class ProximityConfig:
    # Background readings in the supplied world are approximately 60-78.
    # These margins react early enough to prevent a moving-object graze while
    # remaining above the measured free-space noise floor.
    activation_threshold: float = 105.0
    clear_threshold: float = 85.0
    emergency_threshold: float = 300.0
    side_activation_threshold: float = 105.0
    rear_activation_threshold: float = 105.0
    clear_frames: int = 3
    avoidance_forward_speed: float = 1.6
    avoidance_turn_speed: float = 1.6
    emergency_reverse_speed: float = 1.5
    emergency_turn_speed: float = 0.7
    rear_clear_threshold: float = 180.0
    side_escape_forward_speed: float = 4.4
    side_escape_turn_speed: float = 1.0
    rear_escape_forward_speed: float = 4.8
    rear_escape_turn_speed: float = 0.7
    front_blocked_threshold: float = 180.0
    maximum_speed: float = 6.28


@dataclass(frozen=True)
class ProximityDecision:
    command: ControlCommand
    active: bool
    peak_front_value: float
    turn_direction: int
    reason: str
    hazard_region: str = "clear"


class ProximitySafetyLayer:
    """Add short-range collision avoidance without replacing camera navigation."""

    def __init__(self, config: ProximityConfig | None = None) -> None:
        self.config = config or ProximityConfig()
        self.active = False
        self.turn_direction = 1
        self.clear_count = 0
        self.side_active = False
        self.side_turn_direction = 1
        self.side_clear_count = 0
        self.rear_active = False
        self.rear_turn_direction = 1
        self.rear_clear_count = 0

    def _bounded(self, value: float) -> float:
        maximum = self.config.maximum_speed
        return max(-maximum, min(maximum, value))

    @staticmethod
    def _validated(values) -> tuple[float, ...]:
        if len(values) != 8:
            raise ValueError("eight e-puck proximity values are required")
        return tuple(max(0.0, float(value)) for value in values)

    @staticmethod
    def _front_energy(values: tuple[float, ...]) -> tuple[float, float, float]:
        # Cyberbotics e-puck layout: ps0/1 front-right, ps6/7 front-left,
        # ps2 right-side and ps5 left-side.
        right = values[0] + 0.75 * values[1] + 0.25 * values[2]
        left = values[7] + 0.75 * values[6] + 0.25 * values[5]
        peak = max(values[0], values[1], values[6], values[7])
        return left, right, peak

    def _select_turn(self, left_energy: float, right_energy: float) -> None:
        difference = left_energy - right_energy
        if abs(difference) < 1e-6:
            return
        # Positive means the obstacle is stronger on the left, so turn right.
        self.turn_direction = 1 if difference > 0.0 else -1

    def _update_side_and_rear_latches(self, readings: tuple[float, ...]) -> None:
        side_peak = max(readings[2], readings[5])
        if side_peak >= self.config.side_activation_threshold:
            if not self.side_active:
                # ps2 is right-side and ps5 is left-side: turn away.
                self.side_turn_direction = -1 if readings[2] > readings[5] else 1
            self.side_active = True
            self.side_clear_count = 0
        elif self.side_active and side_peak <= self.config.clear_threshold:
            self.side_clear_count += 1
            if self.side_clear_count >= self.config.clear_frames:
                self.side_active = False
                self.side_clear_count = 0
        elif self.side_active:
            self.side_clear_count = 0

        rear_peak = max(readings[3], readings[4])
        if rear_peak >= self.config.rear_activation_threshold:
            if not self.rear_active:
                # ps3 is rear-right and ps4 rear-left: steer the nose away.
                self.rear_turn_direction = -1 if readings[3] > readings[4] else 1
            self.rear_active = True
            self.rear_clear_count = 0
        elif self.rear_active and rear_peak <= self.config.clear_threshold:
            self.rear_clear_count += 1
            if self.rear_clear_count >= self.config.clear_frames:
                self.rear_active = False
                self.rear_clear_count = 0
        elif self.rear_active:
            self.rear_clear_count = 0

    def apply(self, base: ControlCommand, values) -> ProximityDecision:
        readings = self._validated(values)
        left_energy, right_energy, peak = self._front_energy(readings)
        self._update_side_and_rear_latches(readings)

        if peak >= self.config.activation_threshold:
            if not self.active:
                self._select_turn(left_energy, right_energy)
            self.active = True
            self.clear_count = 0
        elif self.active and peak <= self.config.clear_threshold:
            self.clear_count += 1
            if self.clear_count >= self.config.clear_frames:
                self.active = False
                self.clear_count = 0
        elif self.active:
            self.clear_count = 0

        any_active = self.active or self.side_active or self.rear_active
        terminal = base.state in (
            ControllerState.FINISHED,
            ControllerState.FAILSAFE,
        )
        camera_stopped = abs(base.left_speed) < 1e-9 and abs(base.right_speed) < 1e-9
        emergency = peak >= self.config.emergency_threshold
        if terminal or (camera_stopped and not any_active):
            return ProximityDecision(
                command=base,
                active=any_active,
                peak_front_value=peak,
                turn_direction=self.turn_direction,
                reason="camera safety stop retained",
                hazard_region="terminal" if terminal else "clear",
            )

        # A moving crossing object can pass out of the camera view and then
        # approach the robot from behind. Rear protection therefore has highest
        # priority and moves forward into free space instead of waiting to be
        # pushed. This closes the rear-impact gap visible in the supplied video.
        if self.rear_active:
            direction = float(self.rear_turn_direction)
            if peak < self.config.front_blocked_threshold:
                forward = self.config.rear_escape_forward_speed
                turn = self.config.rear_escape_turn_speed * direction
                left_speed = forward + turn
                right_speed = forward - turn
                reason = "rear proximity escape from approaching object"
            else:
                turn = self.config.emergency_turn_speed * direction
                left_speed = turn
                right_speed = -turn
                reason = "rear proximity detected; front blocked, rotating away"
            command = ControlCommand(
                left_speed=self._bounded(left_speed),
                right_speed=self._bounded(right_speed),
                state=base.state,
                reason=reason,
            )
            return ProximityDecision(
                command=command,
                active=True,
                peak_front_value=peak,
                turn_direction=self.rear_turn_direction,
                reason=reason,
                hazard_region="rear",
            )

        # Side sensors keep clearance after a frontal turn, and protect against
        # a crossing object that reaches the robot flank before the front pair.
        if self.side_active and base.state != ControllerState.AVOID:
            direction = float(self.side_turn_direction)
            side_peak = max(readings[2], readings[5])
            scale = 1.35 if side_peak >= self.config.emergency_threshold else 1.0
            forward = self.config.side_escape_forward_speed
            turn = self.config.side_escape_turn_speed * scale * direction
            command = ControlCommand(
                left_speed=self._bounded(forward + turn),
                right_speed=self._bounded(forward - turn),
                state=base.state,
                reason="side proximity clearance manoeuvre",
            )
            return ProximityDecision(
                command=command,
                active=True,
                peak_front_value=peak,
                turn_direction=self.side_turn_direction,
                reason="side proximity clearance manoeuvre",
                hazard_region="side",
            )

        if camera_stopped and self.active and not emergency:
            # A frontal reading must not override the camera's STOP_WAIT.
            # Earlier reverse and forward-arc overrides each moved the robot
            # into one of the two crossing paths. Dedicated side/rear latches
            # above still move forward when a true flank/rear threat exists.
            command = base
            reason = "camera stop retained; front proximity monitored"
            return ProximityDecision(
                command=command,
                active=True,
                peak_front_value=peak,
                turn_direction=self.turn_direction,
                reason=reason,
                hazard_region="front",
            )

        if not self.active:
            if self.side_active:
                return ProximityDecision(
                    command=base,
                    active=True,
                    peak_front_value=peak,
                    turn_direction=self.side_turn_direction,
                    reason="camera avoidance retained; side obstacle monitored",
                    hazard_region="side_monitor",
                )
            return ProximityDecision(
                command=base,
                active=False,
                peak_front_value=peak,
                turn_direction=self.turn_direction,
                reason="camera command; proximity clear",
                hazard_region="clear",
            )

        direction = float(self.turn_direction)
        if emergency:
            rear_peak = max(readings[3], readings[4])
            turn = self.config.emergency_turn_speed * direction
            if camera_stopped and rear_peak < self.config.rear_clear_threshold:
                reverse = self.config.emergency_reverse_speed
                left_speed = -reverse + turn
                right_speed = -reverse - turn
                reason = "emergency proximity reverse-turn"
            elif camera_stopped:
                left_speed = turn
                right_speed = -turn
                reason = "emergency proximity turn; rear blocked"
            else:
                forward = 1.5
                sharp_turn = 1.5 * direction
                left_speed = forward + sharp_turn
                right_speed = forward - sharp_turn
                reason = "emergency proximity forward turn"
            command = ControlCommand(
                left_speed=self._bounded(left_speed),
                right_speed=self._bounded(right_speed),
                state=base.state,
                reason=reason,
            )
        else:
            forward = self.config.avoidance_forward_speed
            turn = self.config.avoidance_turn_speed * direction
            command = ControlCommand(
                left_speed=self._bounded(forward + turn),
                right_speed=self._bounded(forward - turn),
                state=base.state,
                reason="proximity-guided collision avoidance",
            )
            reason = "proximity-guided collision avoidance"
        return ProximityDecision(
            command=command,
            active=True,
            peak_front_value=peak,
            turn_direction=self.turn_direction,
            reason=reason,
            hazard_region="front",
        )
