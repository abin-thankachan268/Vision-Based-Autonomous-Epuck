"""Scenario control and ground-truth evaluation without robot data transmission."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path


if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from controllers.experiment_supervisor.metrics import RunAccumulator, distance_2d, oval_lane_error


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class ExperimentSupervisor:
    def __init__(self):
        from controller import Supervisor

        self.supervisor = Supervisor()
        self.timestep = int(self.supervisor.getBasicTimeStep())
        self.scenario_id = os.getenv("EPUCK_SCENARIO_ID", "phase2_nominal")
        self.repetition = env_int("EPUCK_REPETITION", 1)
        self.seed = env_int("EPUCK_SEED", 1)
        self.lighting = os.getenv("EPUCK_LIGHTING", "nominal").lower()
        self.route = os.getenv("EPUCK_ROUTE", "full").lower()
        self.controller_mode = os.getenv("EPUCK_CONTROLLER_MODE", "vision").lower()
        self.configuration_id = os.getenv("EPUCK_CONFIGURATION_ID", "unfrozen")
        results_set = os.getenv("EPUCK_RESULTS_SET", "").strip()
        if results_set and not all(character.isalnum() or character in "-_." for character in results_set):
            raise ValueError("EPUCK_RESULTS_SET may contain only letters, digits, dash, underscore and dot")
        self.results_root = PROJECT_ROOT / "results"
        if results_set:
            self.results_root /= results_set
        self.raw_root = self.results_root / "raw"
        self.static_position = os.getenv("EPUCK_STATIC_POSITION", "center").lower()
        self.obstacle_layout = os.getenv("EPUCK_OBSTACLE_LAYOUT", "single").lower()
        self.moving_speed = env_float("EPUCK_MOVING_SPEED", 0.15)
        self.enable_static = os.getenv("EPUCK_ENABLE_STATIC", "1") != "0"
        self.enable_moving = os.getenv("EPUCK_ENABLE_MOVING", "1") != "0"
        self.time_limit = env_float("EPUCK_TIME_LIMIT", 120.0)
        self.run_id = (
            f"{self.scenario_id}_r{self.repetition:02d}_s{self.seed:04d}"
        )

        self.robot = self._required_node("EPUCK")
        self.static_nodes = [
            self._required_node("STATIC_OBSTACLE"),
            self._required_node("STATIC_OBSTACLE_2"),
            self._required_node("STATIC_OBSTACLE_3"),
        ]
        self.moving_nodes = [
            self._required_node("MOVING_OBJECT"),
            self._required_node("MOVING_OBJECT_2"),
        ]
        self.sun = self._required_node("SUN")
        self.checkpoints = [
            self._required_node("CP1"),
            self._required_node("CP2"),
            self._required_node("CP3"),
        ]
        self.finish = self._required_node("FINISH_MARKER")

        self.robot_translation = self.robot.getField("translation")
        self.static_translations = [
            node.getField("translation") for node in self.static_nodes
        ]
        self.moving_translations = [
            node.getField("translation") for node in self.moving_nodes
        ]
        self.finish_translation = self.finish.getField("translation")
        self.checkpoint_count = 0
        self.active_static_translations = []
        self.active_moving_translations: list[tuple[object, float]] = []
        self.moving_started_flags: list[bool] = []
        self.moving_cleared_flags: list[bool] = []
        self.accumulator = RunAccumulator()
        self.finished = False
        self.failure_reason = ""

        self._configure_world()
        self.checkpoint_positions = [
            tuple(node.getField("translation").getSFVec3f()[:2])
            for node in self.checkpoints[: self.required_checkpoints]
        ]
        self.finish_position = tuple(self.finish_translation.getSFVec3f()[:2])
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.raw_root / f"{self.run_id}.csv"
        self.raw_handle = self.raw_path.open("w", newline="", encoding="utf-8")
        self.raw_writer = csv.writer(self.raw_handle)
        self.raw_writer.writerow(
            [
                "run_id",
                "time_s",
                "robot_x",
                "robot_y",
                "lane_error_m",
                "checkpoint_count",
                "static_clearance_m",
                "moving_clearance_m",
                "collision_count",
                "moving_started",
                "moving_cleared",
                "finished",
                "obstacle_layout",
                "static_obstacle_count",
                "moving_obstacle_count",
            ]
        )
        print(f"Experiment evaluator started: {self.run_id}")
        print(
            "No Emitter or Receiver is used; evaluator ground truth is not sent "
            f"to the {self.controller_mode} controller."
        )

    def _required_node(self, def_name: str):
        node = self.supervisor.getFromDef(def_name)
        if node is None:
            raise RuntimeError(f"Required DEF node not found: {def_name}")
        return node

    def _configure_world(self) -> None:
        lighting_values = {
            "dim": (0.25, 0.35),
            "nominal": (0.70, 1.00),
            "bright": (1.00, 1.80),
        }
        ambient, intensity = lighting_values.get(self.lighting, lighting_values["nominal"])
        self.sun.getField("ambientIntensity").setSFFloat(ambient)
        self.sun.getField("intensity").setSFFloat(intensity)

        if self.route == "straight":
            self.required_checkpoints = 1
            self.checkpoints[0].getField("translation").setSFVec3f([0.0, -0.45, 0.0])
            self.finish_translation.setSFVec3f([0.60, -0.45, 0.025])
        else:
            self.required_checkpoints = 3
            self.finish_translation.setSFVec3f([-0.60, -0.45, 0.025])

        static_y = {
            "left": -0.41,
            "center": -0.45,
            "right": -0.49,
        }.get(self.static_position, -0.45)
        for translation in self.static_translations:
            translation.setSFVec3f([10.0, 10.0, 0.04])
        for translation in self.moving_translations:
            translation.setSFVec3f([10.0, 10.0, 0.05])

        static_positions: list[list[float]] = []
        if self.enable_static:
            if self.obstacle_layout == "multi_static":
                static_positions = [
                    [-0.02, -0.41, 0.04],
                    [0.55, -0.49, 0.04],
                ]
            elif self.obstacle_layout == "mixed":
                static_positions = [[0.12, -0.41, 0.04]]
            elif self.obstacle_layout == "blocked":
                static_positions = [
                    [0.12, -0.40, 0.04],
                    [0.12, -0.50, 0.04],
                ]
            else:
                static_positions = [[0.12, static_y, 0.04]]
        for translation, position in zip(self.static_translations, static_positions):
            translation.setSFVec3f(position)
        self.active_static_translations = self.static_translations[: len(static_positions)]

        moving_crossings: list[float] = []
        if self.enable_moving:
            moving_crossings = (
                [0.25, -0.25]
                if self.obstacle_layout == "multi_moving"
                else [0.0]
            )
        for translation, crossing_x in zip(self.moving_translations, moving_crossings):
            translation.setSFVec3f([crossing_x, 0.78, 0.05])
        self.active_moving_translations = list(
            zip(self.moving_translations[: len(moving_crossings)], moving_crossings)
        )
        self.moving_started_flags = [False] * len(self.active_moving_translations)
        self.moving_cleared_flags = [False] * len(self.active_moving_translations)

    def _update_moving_objects(self, time_s: float, robot_xy: tuple[float, float]) -> None:
        crossing_trigger = min(
            0.50,
            max(0.30, 0.18 + 0.092 * 0.33 / max(self.moving_speed, 0.01)),
        )
        for index, (translation, crossing_x) in enumerate(
            self.active_moving_translations
        ):
            if self.moving_cleared_flags[index]:
                continue
            crossing = (crossing_x, 0.45)
            if not self.moving_started_flags[index]:
                fallback_time = 45.0 + index * 5.0
                if (
                    distance_2d(robot_xy, crossing) <= crossing_trigger
                    or time_s >= fallback_time
                ):
                    self.moving_started_flags[index] = True
            if not self.moving_started_flags[index]:
                continue
            current = translation.getSFVec3f()
            next_y = max(
                0.12,
                current[1] - self.moving_speed * self.timestep / 1000.0,
            )
            translation.setSFVec3f([crossing_x, next_y, 0.05])
            if next_y <= 0.12:
                self.moving_cleared_flags[index] = True
                translation.setSFVec3f([10.0, 10.0, 0.05])

    def _update_checkpoints(self, robot_xy: tuple[float, float]) -> None:
        if self.checkpoint_count < len(self.checkpoint_positions):
            target = self.checkpoint_positions[self.checkpoint_count]
            if distance_2d(robot_xy, target) <= 0.28:
                self.checkpoint_count += 1

    def _write_summary(self, duration: float) -> None:
        self.results_root.mkdir(parents=True, exist_ok=True)
        summary_path = self.results_root / "run_summary.csv"
        header = [
            "run_id",
            "scenario_id",
            "repetition",
            "seed",
            "controller_mode",
            "configuration_id",
            "route",
            "lighting",
            "static_position",
            "moving_speed_mps",
            "duration_s",
            "completed",
            "lane_following_success",
            "within_lane_fraction",
            "mean_lane_error_m",
            "max_lane_error_m",
            "collision_count",
            "min_static_clearance_m",
            "min_moving_clearance_m",
            "checkpoints_passed",
            "failure_reason",
            "obstacle_layout",
            "static_obstacle_count",
            "moving_obstacle_count",
        ]
        previous: list[dict[str, str]] = []
        if summary_path.exists():
            with summary_path.open(newline="", encoding="utf-8") as handle:
                previous = [
                    row for row in csv.DictReader(handle) if row["run_id"] != self.run_id
                ]
        row = dict(
            zip(
                header,
                [
                    self.run_id,
                    self.scenario_id,
                    self.repetition,
                    self.seed,
                    self.controller_mode,
                    self.configuration_id,
                    self.route,
                    self.lighting,
                    self.static_position,
                    f"{self.moving_speed:.3f}",
                    f"{duration:.3f}",
                    int(self.finished),
                    int(self.finished and self.accumulator.within_lane_fraction >= 0.95),
                    f"{self.accumulator.within_lane_fraction:.6f}",
                    f"{self.accumulator.mean_lane_error:.6f}",
                    f"{self.accumulator.maximum_lane_error:.6f}",
                    self.accumulator.collision_count,
                    f"{self.accumulator.minimum_static_clearance:.6f}",
                    f"{self.accumulator.minimum_moving_clearance:.6f}",
                    self.checkpoint_count,
                    self.failure_reason,
                    self.obstacle_layout,
                    len(self.active_static_translations),
                    len(self.active_moving_translations),
                ],
            )
        )
        with summary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(previous)
            writer.writerow(row)

    def run(self) -> None:
        try:
            while self.supervisor.step(self.timestep) != -1:
                time_s = self.supervisor.getTime()
                robot_position = self.robot_translation.getSFVec3f()
                robot_xy = (robot_position[0], robot_position[1])
                self._update_moving_objects(time_s, robot_xy)
                self._update_checkpoints(robot_xy)

                static_clearance = min(
                    (
                        distance_2d(
                            robot_xy,
                            tuple(translation.getSFVec3f()[:2]),
                        )
                        for translation in self.active_static_translations
                    ),
                    default=99.0,
                )
                moving_clearance = min(
                    (
                        distance_2d(
                            robot_xy,
                            tuple(translation.getSFVec3f()[:2]),
                        )
                        for translation, _crossing_x in self.active_moving_translations
                    ),
                    default=99.0,
                )
                lane_error = oval_lane_error(*robot_xy)
                self.accumulator.update(lane_error, static_clearance, moving_clearance)

                finish_distance = distance_2d(robot_xy, self.finish_position)
                self.finished = (
                    self.checkpoint_count == self.required_checkpoints
                    and finish_distance <= 0.18
                )
                self.raw_writer.writerow(
                    [
                        self.run_id,
                        f"{time_s:.3f}",
                        f"{robot_xy[0]:.6f}",
                        f"{robot_xy[1]:.6f}",
                        f"{lane_error:.6f}",
                        self.checkpoint_count,
                        f"{static_clearance:.6f}",
                        f"{moving_clearance:.6f}",
                        self.accumulator.collision_count,
                        int(any(self.moving_started_flags)),
                        int(
                            bool(self.moving_cleared_flags)
                            and all(self.moving_cleared_flags)
                        ),
                        int(self.finished),
                        self.obstacle_layout,
                        len(self.active_static_translations),
                        len(self.active_moving_translations),
                    ]
                )

                if self.finished:
                    break
                if time_s >= self.time_limit:
                    self.failure_reason = "time_limit"
                    break
        finally:
            duration = self.supervisor.getTime()
            self.raw_handle.close()
            self._write_summary(duration)
            print(
                f"Experiment evaluator finished: completed={self.finished} "
                f"checkpoints={self.checkpoint_count} collisions={self.accumulator.collision_count}"
            )
            self.supervisor.simulationQuit(0)


if __name__ == "__main__":
    ExperimentSupervisor().run()
