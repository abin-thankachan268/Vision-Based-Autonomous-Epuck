"""Interactive Webots behavior: looping obstacles and automatic lap reset."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# crossing_x, start_y, direction, lower_y, upper_y
MOVING_STARTS = (
    (0.25, 0.48, -1, 0.12, 0.78),
    (0.78, -0.78, 1, -0.78, -0.12),
)
CHECKPOINT_NODE_NAMES = ("CP1", "CP2", "CP3")
STATIC_NODE_NAMES = ("STATIC_OBSTACLE", "STATIC_OBSTACLE_2", "STATIC_OBSTACLE_3")
MOVING_NODE_NAMES = ("MOVING_OBJECT", "MOVING_OBJECT_2")


def advance_ping_pong(
    value: float,
    direction: int,
    speed: float,
    dt: float,
    lower: float,
    upper: float,
) -> tuple[float, int]:
    """Advance at constant speed and reflect cleanly at either boundary."""

    if lower >= upper:
        raise ValueError("lower must be less than upper")
    next_direction = -1 if direction < 0 else 1
    next_value = value + next_direction * max(0.0, speed) * max(0.0, dt)
    while next_value < lower or next_value > upper:
        if next_value < lower:
            next_value = lower + (lower - next_value)
            next_direction = 1
        elif next_value > upper:
            next_value = upper - (next_value - upper)
            next_direction = -1
    return next_value, next_direction


class InteractiveSupervisor:
    """Keep the desktop simulation open and reload after each complete lap."""

    def __init__(self) -> None:
        from controller import Supervisor

        self.supervisor = Supervisor()
        self.timestep = int(self.supervisor.getBasicTimeStep())
        self.dt = self.timestep / 1000.0
        self.speed = max(0.01, float(os.getenv("EPUCK_MOVING_SPEED", "0.15")))
        self.reset_delay = max(0.0, float(os.getenv("EPUCK_RESET_DELAY", "1.0")))
        self.time_limit = max(30.0, float(os.getenv("EPUCK_INTERACTIVE_TIME_LIMIT", "180.0")))

        self.robot = self._required_node("EPUCK")
        self.robot_translation = self.robot.getField("translation")
        self.checkpoints = [
            node
            for name in CHECKPOINT_NODE_NAMES
            if (node := self._optional_node(name)) is not None
        ]
        self.finish = self._optional_node("FINISH_MARKER")
        self.checkpoint_positions = [
            tuple(node.getField("translation").getSFVec3f()[:2])
            for node in self.checkpoints
        ]
        self.finish_position = (
            tuple(self.finish.getField("translation").getSFVec3f()[:2])
            if self.finish is not None
            else None
        )
        self.completion_enabled = (
            len(self.checkpoint_positions) == len(CHECKPOINT_NODE_NAMES)
            and self.finish_position is not None
        )
        self.checkpoint_count = 0
        self.completed_at: float | None = None
        self.runtime_log = PROJECT_ROOT / "evidence" / "interactive_runtime.log"
        export_image = os.getenv("EPUCK_EXPORT_IMAGE", "").strip()
        self.export_image = Path(export_image).resolve() if export_image else None
        final_export_image = os.getenv("EPUCK_EXPORT_FINAL_IMAGE", "").strip()
        self.final_export_image = (
            Path(final_export_image).resolve() if final_export_image else None
        )
        self.image_exported = False
        self.static_translations = [
            node.getField("translation")
            for name in STATIC_NODE_NAMES
            if (node := self._optional_node(name)) is not None
        ]
        self.minimum_static_clearance = 99.0
        self.minimum_moving_clearance = 99.0
        self.minimum_static_by_object = [99.0] * len(self.static_translations)
        self.collision_count = 0
        self.static_contact = False
        self.moving_contact = False

        moving_specs = [
            (node, start)
            for name, start in zip(MOVING_NODE_NAMES, MOVING_STARTS)
            if (node := self._optional_node(name)) is not None
        ]
        if not moving_specs:
            raise RuntimeError("Required moving DEF node not found: MOVING_OBJECT")
        self.moving = []
        # Newer demo worlds have one object on each straight; older saved
        # worlds may contain only MOVING_OBJECT, which is still valid.
        for node, (crossing_x, start_y, direction, lower_y, upper_y) in moving_specs:
            translation = node.getField("translation")
            translation.setSFVec3f([crossing_x, start_y, 0.05])
            self.moving.append(
                [translation, crossing_x, direction, lower_y, upper_y]
            )
        self.minimum_moving_by_object = [99.0] * len(self.moving)

        self._log_event("controller_started")
        reset_message = (
            "the world reloads after each completed pass."
            if self.completion_enabled
            else "completion markers are unavailable, so the world reloads on the time limit."
        )
        print(
            f"Interactive demonstration mode: {len(self.moving)} moving obstacle(s) "
            f"loop continuously; {reset_message}"
        )

    def _required_node(self, def_name: str):
        node = self.supervisor.getFromDef(def_name)
        if node is None:
            raise RuntimeError(f"Required DEF node not found: {def_name}")
        return node

    def _optional_node(self, def_name: str):
        return self.supervisor.getFromDef(def_name)

    def _log_event(self, event: str) -> None:
        self.runtime_log.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with self.runtime_log.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp},{event}\n")

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    def _move_obstacles(self) -> None:
        for moving in self.moving:
            translation, crossing_x, direction, lower_y, upper_y = moving
            current_y = translation.getSFVec3f()[1]
            next_y, next_direction = advance_ping_pong(
                current_y,
                direction,
                self.speed,
                self.dt,
                lower_y,
                upper_y,
            )
            moving[2] = next_direction
            translation.setSFVec3f([crossing_x, next_y, 0.05])

    def _update_safety_metrics(self, robot_xy: tuple[float, float]) -> None:
        static_clearances = [
            self._distance(
                robot_xy,
                tuple(translation.getSFVec3f()[:2]),
            )
            for translation in self.static_translations
        ]
        static_clearance = min(static_clearances) if static_clearances else 99.0
        moving_clearances = [
            self._distance(
                robot_xy,
                tuple(moving[0].getSFVec3f()[:2]),
            )
            for moving in self.moving
        ]
        moving_clearance = min(moving_clearances)
        self.minimum_static_by_object = [
            min(previous, current)
            for previous, current in zip(
                self.minimum_static_by_object,
                static_clearances,
            )
        ]
        self.minimum_moving_by_object = [
            min(previous, current)
            for previous, current in zip(
                self.minimum_moving_by_object,
                moving_clearances,
            )
        ]
        self.minimum_static_clearance = min(
            self.minimum_static_clearance,
            static_clearance,
        )
        self.minimum_moving_clearance = min(
            self.minimum_moving_clearance,
            moving_clearance,
        )
        # Use a conservative 0.09 m centre-distance envelope. The earlier
        # 0.078 m axis-aligned contact approximation missed the visible corner
        # and rear grazes identified in the supplied simulation recording.
        static_contact = static_clearance <= 0.09
        moving_contact = moving_clearance <= 0.09
        if static_contact and not self.static_contact:
            self.collision_count += 1
            self._log_event(
                "contact_static "
                f"time_s={self.supervisor.getTime():.3f} "
                f"object={static_clearances.index(static_clearance) + 1} "
                f"distance={static_clearance:.6f} "
                f"robot_x={robot_xy[0]:.6f} robot_y={robot_xy[1]:.6f}"
            )
        if moving_contact and not self.moving_contact:
            self.collision_count += 1
            self._log_event(
                "contact_moving "
                f"time_s={self.supervisor.getTime():.3f} "
                f"object={moving_clearances.index(moving_clearance) + 1} "
                f"distance={moving_clearance:.6f} "
                f"robot_x={robot_xy[0]:.6f} robot_y={robot_xy[1]:.6f}"
            )
        self.static_contact = static_contact
        self.moving_contact = moving_contact

    def _update_completion(self, time_s: float) -> None:
        robot_position = self.robot_translation.getSFVec3f()
        robot_xy = (robot_position[0], robot_position[1])
        self._update_safety_metrics(robot_xy)
        if not self.completion_enabled:
            return
        if self.checkpoint_count < len(self.checkpoint_positions):
            target = self.checkpoint_positions[self.checkpoint_count]
            if self._distance(robot_xy, target) <= 0.28:
                self.checkpoint_count += 1
        if (
            self.completed_at is None
            and self.checkpoint_count == len(self.checkpoint_positions)
            and self.finish_position is not None
            and self._distance(robot_xy, self.finish_position) <= 0.18
        ):
            self.completed_at = time_s
            self._log_event(
                "pass_completed "
                f"collisions={self.collision_count} "
                f"min_static={self.minimum_static_clearance:.6f} "
                f"min_moving={self.minimum_moving_clearance:.6f} "
                "static_each="
                + "|".join(f"{value:.6f}" for value in self.minimum_static_by_object)
                + " moving_each="
                + "|".join(f"{value:.6f}" for value in self.minimum_moving_by_object)
            )
            print("Interactive demonstration pass completed; resetting the world.")

    def run(self) -> None:
        while self.supervisor.step(self.timestep) != -1:
            time_s = self.supervisor.getTime()
            self._move_obstacles()
            if self.export_image is not None and not self.image_exported:
                self.export_image.parent.mkdir(parents=True, exist_ok=True)
                self.supervisor.exportImage(str(self.export_image), 100)
                self.image_exported = True
                print(f"Interactive layout image saved: {self.export_image}")
            self._update_completion(time_s)
            completed_delay_elapsed = (
                self.completed_at is not None
                and time_s - self.completed_at >= self.reset_delay
            )
            if completed_delay_elapsed or time_s >= self.time_limit:
                if self.completed_at is None:
                    robot_position = self.robot_translation.getSFVec3f()
                    self._log_event(
                        "time_limit_reset "
                        f"checkpoint_count={self.checkpoint_count} "
                        f"robot_x={robot_position[0]:.6f} "
                        f"robot_y={robot_position[1]:.6f} "
                        f"collisions={self.collision_count} "
                        f"min_static={self.minimum_static_clearance:.6f} "
                        f"min_moving={self.minimum_moving_clearance:.6f} "
                        "static_each="
                        + "|".join(
                            f"{value:.6f}"
                            for value in self.minimum_static_by_object
                        )
                        + " moving_each="
                        + "|".join(
                            f"{value:.6f}"
                            for value in self.minimum_moving_by_object
                        )
                    )
                    if self.final_export_image is not None:
                        self.final_export_image.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        self.supervisor.exportImage(
                            str(self.final_export_image),
                            100,
                        )
                    print("Interactive demonstration time limit reached; resetting for another pass.")
                else:
                    self._log_event("completed_pass_reset")
                self.supervisor.worldReload()
                return


if __name__ == "__main__":
    InteractiveSupervisor().run()
