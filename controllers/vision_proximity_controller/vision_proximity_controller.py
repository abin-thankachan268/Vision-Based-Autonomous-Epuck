"""Webots entry point for camera navigation with proximity safety fusion."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path


if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from controllers.vision_controller.config import ControllerConfig
from controllers.vision_controller.control import VisionControllerCore
from controllers.vision_controller.perception import VisionPerception
from controllers.vision_proximity_controller.console_logging import (
    DecisionConsoleLogger,
)
from controllers.vision_proximity_controller.finish_marker import (
    detect_checkered_finish,
)
from controllers.vision_proximity_controller.proximity import (
    ProximityConfig,
    ProximitySafetyLayer,
)
from controllers.vision_proximity_controller.telemetry import FusionTelemetryWriter


def _proximity_config() -> ProximityConfig:
    return ProximityConfig(
        activation_threshold=float(os.getenv("AUTONOMOUS_EPUCK_PS_ACTIVATION", "105")),
        clear_threshold=float(os.getenv("AUTONOMOUS_EPUCK_PS_CLEAR", "85")),
        emergency_threshold=float(os.getenv("AUTONOMOUS_EPUCK_PS_EMERGENCY", "300")),
        side_activation_threshold=float(os.getenv("AUTONOMOUS_EPUCK_PS_SIDE_ACTIVATION", "105")),
        rear_activation_threshold=float(os.getenv("AUTONOMOUS_EPUCK_PS_REAR_ACTIVATION", "105")),
    )


def _camera_config() -> ControllerConfig:
    """Interactive camera config with extra moving-object clearance time."""

    config = ControllerConfig()
    clear_frames = max(
        config.control.clear_obstacle_frames,
        24,
        int(os.getenv("AUTONOMOUS_EPUCK_CLEAR_OBSTACLE_FRAMES", "24")),
    )
    return replace(
        config,
        control=replace(config.control, clear_obstacle_frames=clear_frames),
    )


def run() -> None:
    from controller import Robot

    robot = Robot()
    timestep_ms = int(robot.getBasicTimeStep())
    timestep_s = timestep_ms / 1000.0

    left_motor = robot.getDevice("left wheel motor")
    right_motor = robot.getDevice("right wheel motor")
    left_motor.setPosition(float("inf"))
    right_motor.setPosition(float("inf"))
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)

    camera = robot.getDevice("camera")
    camera.enable(timestep_ms)
    proximity_sensors = []
    for index in range(8):
        sensor = robot.getDevice(f"ps{index}")
        if sensor is None:
            raise RuntimeError(f"e-puck proximity sensor ps{index} is unavailable")
        sensor.enable(timestep_ms)
        proximity_sensors.append(sensor)

    camera_config = _camera_config()
    perception = VisionPerception(camera_config)
    camera_controller = VisionControllerCore(camera_config)
    proximity = ProximitySafetyLayer(_proximity_config())
    console = DecisionConsoleLogger(
        float(os.getenv("AUTONOMOUS_EPUCK_CONSOLE_LOG_INTERVAL", "0.5"))
    )
    telemetry_path = Path(__file__).with_name("fusion_telemetry.csv")

    print("VISION + PROXIMITY AUTONOMOUS CONTROLLER", flush=True)
    print(
        "Navigation uses the camera and local ps0-ps7 readings only; "
        "Supervisor ground truth is not connected.",
        flush=True,
    )
    print(
        "Console trace: PERCEPTION shows what the camera sees, PROXIMITY "
        "shows all eight local sensors, and DECISION explains the selected "
        "state and final wheel command.",
        flush=True,
    )

    with FusionTelemetryWriter(telemetry_path) as telemetry:
        while robot.step(timestep_ms) != -1:
            image = camera.getImage()
            readings = tuple(sensor.getValue() for sensor in proximity_sensors)
            if not image:
                left_motor.setVelocity(0.0)
                right_motor.setVelocity(0.0)
                continue

            result = perception.process_webots_image(
                image,
                camera.getWidth(),
                camera.getHeight(),
                robot.getTime(),
            )
            frame = perception.webots_frame_to_bgr(
                image,
                camera.getWidth(),
                camera.getHeight(),
            )
            checker_visible = detect_checkered_finish(frame)
            if checker_visible and not result.finish_visible:
                result = replace(result, finish_visible=True)
            finish_detected = (
                result.finish_visible
                and robot.getTime()
                >= camera_config.control.minimum_finish_time_seconds
            )
            camera_command = camera_controller.step(
                result,
                timestep_s,
                finish_detected=finish_detected,
            )
            decision = proximity.apply(camera_command, readings)
            left_motor.setVelocity(decision.command.left_speed)
            right_motor.setVelocity(decision.command.right_speed)
            console.log(
                robot.getTime(),
                result,
                readings,
                camera_command,
                decision,
            )
            telemetry.write(robot.getTime(), readings, decision)


if __name__ == "__main__":
    run()
