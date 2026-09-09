"""Readable, rate-limited Webots console reporting for sensor fusion."""

from __future__ import annotations


def _number(value, digits: int = 3) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"


def _visible_obstacles(result) -> tuple:
    if result.obstacles:
        return tuple(item for item in result.obstacles if item.present)
    return (result.obstacle,) if result.obstacle.present else ()


def perception_log_line(time_s: float, result) -> str:
    lane = result.lane
    lane_status = "VISIBLE" if lane.visible else "LOST"
    obstacles = _visible_obstacles(result)
    if obstacles:
        object_text = "; ".join(
            f"#{item.track_id}:{item.observed_color or 'unknown'}"
            f"/{item.motion.value.lower()}"
            f" center=({_number(item.centroid[0], 1)},{_number(item.centroid[1], 1)})"
            f" area={item.area_fraction:.3f} threat={item.threat_score:.2f}"
            for item in obstacles
        )
    else:
        object_text = "none"
    return (
        f"[PERCEPTION t={time_s:7.3f}s] lane={lane_status} "
        f"center={_number(lane.center_x, 1)} error={lane.normalized_error:+.3f} "
        f"confidence={lane.confidence:.2f} boundaries="
        f"({_number(lane.left_boundary_x, 1)},{_number(lane.right_boundary_x, 1)}) "
        f"objects={len(obstacles)} [{object_text}] "
        f"path={'BLOCKED' if result.path_blocked else 'OPEN'} "
        f"finish={'YES' if result.finish_visible else 'no'}"
    )


def sensor_log_line(readings, decision) -> str:
    values = tuple(float(value) for value in readings)
    sensor_text = " ".join(
        f"ps{index}={value:6.1f}" for index, value in enumerate(values)
    )
    turn = "RIGHT" if decision.turn_direction > 0 else "LEFT"
    return (
        f"[PROXIMITY] {sensor_text} | front_peak={decision.peak_front_value:6.1f} "
        f"status={'ACTIVE' if decision.active else 'clear'} "
        f"region={decision.hazard_region.upper()} turn_away={turn}"
    )


def decision_log_line(camera_command, decision) -> str:
    final = decision.command
    overridden = (
        abs(final.left_speed - camera_command.left_speed) > 1e-9
        or abs(final.right_speed - camera_command.right_speed) > 1e-9
    )
    return (
        f"[DECISION] state={final.state.value} "
        f"camera_motor=({camera_command.left_speed:+.2f},{camera_command.right_speed:+.2f}) "
        f"camera_reason=\"{camera_command.reason}\" | "
        f"fusion={'OVERRIDE' if overridden else 'camera command retained'} "
        f"final_motor=({final.left_speed:+.2f},{final.right_speed:+.2f}) "
        f"because=\"{decision.reason}\""
    )


class DecisionConsoleLogger:
    """Print periodically and immediately when an important decision changes."""

    def __init__(self, interval_seconds: float = 0.5) -> None:
        self.interval_seconds = max(0.05, float(interval_seconds))
        self.last_time = float("-inf")
        self.last_signature = None

    @staticmethod
    def _signature(result, camera_command, decision) -> tuple:
        obstacles = _visible_obstacles(result)
        return (
            camera_command.state,
            camera_command.reason,
            decision.active,
            decision.reason,
            result.lane.visible,
            result.path_blocked,
            result.finish_visible,
            tuple(
                (item.track_id, item.observed_color, item.motion)
                for item in obstacles
            ),
        )

    def should_log(self, time_s: float, result, camera_command, decision) -> bool:
        signature = self._signature(result, camera_command, decision)
        changed = signature != self.last_signature
        periodic = time_s - self.last_time >= self.interval_seconds
        if changed or periodic:
            self.last_signature = signature
            self.last_time = time_s
            return True
        return False

    def log(self, time_s, result, readings, camera_command, decision) -> None:
        if not self.should_log(time_s, result, camera_command, decision):
            return
        print(perception_log_line(time_s, result), flush=True)
        print(sensor_log_line(readings, decision), flush=True)
        print(decision_log_line(camera_command, decision), flush=True)
