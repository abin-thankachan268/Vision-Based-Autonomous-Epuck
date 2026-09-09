"""Webots entry point for the vision-based autonomous e-puck controller."""

from __future__ import annotations

import sys
import os
from pathlib import Path

import cv2


if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from controllers.vision_controller.config import ControllerConfig
from controllers.vision_controller.control import VisionControllerCore
from controllers.vision_controller.perception import VisionPerception
from controllers.vision_controller.telemetry import TelemetryWriter


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

    config = ControllerConfig()
    perception = VisionPerception(config)
    controller = VisionControllerCore(config)
    telemetry_path = Path(__file__).with_name(config.telemetry_filename)

    print("VISION CONTROLLER")
    print("Navigation input: camera only; Supervisor ground truth is not connected.")
    capture_frames = os.getenv("EPUCK_CAPTURE_FRAMES", "0") == "1"
    capture_at_seconds = float(os.getenv("EPUCK_CAPTURE_AT_SECONDS", "0"))
    captured_frame = False

    with TelemetryWriter(telemetry_path) as telemetry:
        while robot.step(timestep_ms) != -1:
            image = camera.getImage()
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
            if (
                capture_frames
                and not captured_frame
                and robot.getTime() >= capture_at_seconds
            ):
                debug_directory = Path(__file__).resolve().parents[2] / "evidence"
                debug_directory.mkdir(parents=True, exist_ok=True)
                debug_frame = perception.webots_frame_to_bgr(
                    image,
                    camera.getWidth(),
                    camera.getHeight(),
                )
                cv2.imwrite(str(debug_directory / "phase2_camera_frame.png"), debug_frame)
                captured_frame = True
            finish_detected = (
                result.finish_visible
                and robot.getTime() >= config.control.minimum_finish_time_seconds
            )
            command = controller.step(result, timestep_s, finish_detected=finish_detected)
            left_motor.setVelocity(command.left_speed)
            right_motor.setVelocity(command.right_speed)
            telemetry.write(result, command)


if __name__ == "__main__":
    run()
