"""Webots entry point for the simplified autonomous e-puck controller."""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from controllers.e_puck_controller.control import (  # noqa: E402
    ControlConfig,
    NavigationState,
    SimpleNavigator,
)
from controllers.e_puck_controller.vision import (  # noqa: E402
    SimpleVision,
    VisionConfig,
    webots_bgra_to_bgr,
)


def _log_event(path: Path, event: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp},{event}\n")


def _fmt(value) -> str:
    return "-" if value is None else f"{float(value):.1f}"


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
    proximity = []
    for index in range(8):
        sensor = robot.getDevice(f"ps{index}")
        if sensor is None:
            raise RuntimeError(f"Required e-puck proximity sensor ps{index} is unavailable")
        sensor.enable(timestep_ms)
        proximity.append(sensor)

    vision_config = VisionConfig(
        white_min_value=int(os.getenv("SIMPLIFIED_WHITE_MIN_VALUE", "90")),
        roi_top_fraction=float(os.getenv("SIMPLIFIED_ROI_TOP", "0.15")),
    )
    control_config = ControlConfig(
        cruise_speed=float(os.getenv("SIMPLIFIED_CRUISE_SPEED", "4.2")),
        cautious_speed=float(os.getenv("SIMPLIFIED_CAUTIOUS_SPEED", "2.2")),
        kp=float(os.getenv("SIMPLIFIED_PD_KP", "7.2")),
        kd=float(os.getenv("SIMPLIFIED_PD_KD", "0.055")),
        avoidance_turn_speed=float(os.getenv("SIMPLIFIED_AVOID_TURN", "0.95")),
        avoidance_first_leg_seconds=float(os.getenv("SIMPLIFIED_AVOID_LEG", "0.75")),
        avoidance_straight_seconds=float(
            os.getenv("SIMPLIFIED_AVOID_STRAIGHT", "0.95")
        ),
        avoidance_commit_seconds=float(os.getenv("SIMPLIFIED_AVOID_COMMIT", "2.45")),
        search_turn_speed=float(os.getenv("SIMPLIFIED_REJOIN_TURN", "0.55")),
        rejoin_forward_speed=float(os.getenv("SIMPLIFIED_REJOIN_FORWARD", "1.60")),
        rejoin_manoeuvre_speed=float(
            os.getenv("SIMPLIFIED_REJOIN_MANOEUVRE_SPEED", "2.5")
        ),
        rejoin_turn_seconds=float(os.getenv("SIMPLIFIED_REJOIN_TURN_TIME", "1.0")),
        rejoin_straight_seconds=float(
            os.getenv("SIMPLIFIED_REJOIN_STRAIGHT_TIME", "1.5")
        ),
        proximity_danger_threshold=float(os.getenv("SIMPLIFIED_PS_DANGER", "180")),
        proximity_clear_threshold=float(os.getenv("SIMPLIFIED_PS_CLEAR", "120")),
        proximity_emergency_threshold=float(os.getenv("SIMPLIFIED_PS_EMERGENCY", "700")),
        proximity_pause_seconds=float(os.getenv("SIMPLIFIED_PS_PAUSE", "0.25")),
        post_avoidance_grace_seconds=float(
            os.getenv("SIMPLIFIED_POST_AVOID_GRACE", "4.0")
        ),
    )
    vision = SimpleVision(vision_config)
    navigator = SimpleNavigator(control_config)
    runtime_log = PROJECT_ROOT / "evidence" / "simplified_runtime.log"
    telemetry_path = Path(__file__).with_name("simplified_telemetry.csv")
    console_interval = max(0.1, float(os.getenv("SIMPLIFIED_CONSOLE_INTERVAL", "0.5")))
    capture_interval = max(
        0.0, float(os.getenv("SIMPLIFIED_CAPTURE_INTERVAL", "0"))
    )
    capture_directory = PROJECT_ROOT / "evidence" / "simplified_frames"
    next_capture_time = 0.0
    if capture_interval > 0.0:
        capture_directory.mkdir(parents=True, exist_ok=True)
    last_console_time = float("-inf")
    last_state = navigator.state
    finish_latched = False

    _log_event(runtime_log, "controller_started architecture=fixed_hsv+pd+single_target+proximity")
    print("SIMPLIFIED VISION + PD + PROXIMITY CONTROLLER", flush=True)
    print(
        "Robot input is limited to its camera and ps0-ps7 sensors; "
        "no Supervisor navigation data is connected.",
        flush=True,
    )

    with telemetry_path.open("w", newline="", encoding="utf-8") as telemetry_file:
        writer = csv.writer(telemetry_file)
        writer.writerow(
            [
                "time_s",
                "state",
                "lane_visible",
                "lane_error",
                "lane_confidence",
                "finish_visible",
                "obstacle_color",
                "obstacle_motion",
                "obstacle_x",
                "obstacle_y",
                "front_proximity",
                "left_speed",
                "right_speed",
                "reason",
            ]
        )
        while robot.step(timestep_ms) != -1:
            image = camera.getImage()
            readings = tuple(sensor.getValue() for sensor in proximity)
            if not image:
                left_motor.setVelocity(0.0)
                right_motor.setVelocity(0.0)
                continue
            frame = webots_bgra_to_bgr(image, camera.getWidth(), camera.getHeight())
            scene = vision.process_frame(frame)
            if capture_interval > 0.0 and robot.getTime() >= next_capture_time:
                import cv2

                cv2.imwrite(
                    str(capture_directory / f"frame_{robot.getTime():07.2f}s.png"),
                    frame,
                )
                next_capture_time = robot.getTime() + capture_interval
            finish_detected = (
                scene.finish_visible
                and robot.getTime() >= control_config.minimum_finish_time_seconds
            )
            command = navigator.step(scene, readings, timestep_s, finish_detected)
            left_motor.setVelocity(command.left_speed)
            right_motor.setVelocity(command.right_speed)

            state_changed = command.state != last_state
            if state_changed:
                _log_event(
                    runtime_log,
                    f"state_change time_s={robot.getTime():.3f} from={last_state.value} "
                    f"to={command.state.value} reason={command.reason}",
                )
                last_state = command.state
            if command.state == NavigationState.FINISHED and not finish_latched:
                finish_latched = True
                _log_event(runtime_log, f"finish_detected time_s={robot.getTime():.3f}")

            centroid = scene.obstacle.centroid or (None, None)
            front_peak = max(readings[0], readings[1], readings[6], readings[7])
            writer.writerow(
                [
                    f"{robot.getTime():.3f}",
                    command.state.value,
                    int(scene.lane.visible),
                    f"{scene.lane.error:.6f}",
                    f"{scene.lane.confidence:.6f}",
                    int(scene.finish_visible),
                    scene.obstacle.color,
                    scene.obstacle.motion.value,
                    "" if centroid[0] is None else f"{centroid[0]:.3f}",
                    "" if centroid[1] is None else f"{centroid[1]:.3f}",
                    f"{front_peak:.3f}",
                    f"{command.left_speed:.6f}",
                    f"{command.right_speed:.6f}",
                    command.reason,
                ]
            )
            if robot.getTime() - last_console_time >= console_interval or state_changed:
                last_console_time = robot.getTime()
                print(
                    f"[VISION t={robot.getTime():7.3f}s] "
                    f"lane={'VISIBLE' if scene.lane.visible else 'LOST'} "
                    f"left={_fmt(scene.lane.left_x)} right={_fmt(scene.lane.right_x)} "
                    f"error={scene.lane.error:+.3f} confidence={scene.lane.confidence:.2f} "
                    f"object={scene.obstacle.color or 'none'}/{scene.obstacle.motion.value.lower()} "
                    f"centroid=({_fmt(centroid[0])},{_fmt(centroid[1])}) "
                    f"finish={'YES' if scene.finish_visible else 'no'}",
                    flush=True,
                )
                print(
                    "[PROXIMITY] "
                    + " ".join(f"ps{i}={value:6.1f}" for i, value in enumerate(readings))
                    + f" front_peak={front_peak:6.1f}",
                    flush=True,
                )
                print(
                    f"[DECISION] state={command.state.value} "
                    f"motors=({command.left_speed:+.2f},{command.right_speed:+.2f}) "
                    f"because=\"{command.reason}\"",
                    flush=True,
                )


if __name__ == "__main__":
    run()
