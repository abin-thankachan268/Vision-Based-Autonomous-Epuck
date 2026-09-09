"""Supervisor used only to move one blue pedestrian across the road."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path


PEDESTRIAN_START = (0.25, 0.48, -1, 0.12, 0.78)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _log_event(path: Path, event: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(timezone.utc).isoformat()},{event}\n")


def advance_ping_pong(
    value: float,
    direction: int,
    speed: float,
    dt: float,
    lower: float,
    upper: float,
) -> tuple[float, int]:
    """Advance at constant speed and reflect at the configured limits."""

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


def run() -> None:
    from controller import Supervisor

    supervisor = Supervisor()
    timestep = int(supervisor.getBasicTimeStep())
    dt = timestep / 1000.0
    speed = max(0.01, float(os.getenv("SIMPLIFIED_PEDESTRIAN_SPEED", "0.15")))
    default_x, default_y, default_direction, default_lower, default_upper = PEDESTRIAN_START
    crossing_x = float(os.getenv("SIMPLIFIED_PEDESTRIAN_X", str(default_x)))
    start_y = float(os.getenv("SIMPLIFIED_PEDESTRIAN_START_Y", str(default_y)))
    direction = -1 if int(os.getenv("SIMPLIFIED_PEDESTRIAN_DIRECTION", str(default_direction))) < 0 else 1
    lower_y = float(os.getenv("SIMPLIFIED_PEDESTRIAN_LOWER_Y", str(default_lower)))
    upper_y = float(os.getenv("SIMPLIFIED_PEDESTRIAN_UPPER_Y", str(default_upper)))
    movement_log = PROJECT_ROOT / "evidence" / "simplified_pedestrian.log"
    pedestrian = supervisor.getFromDef("MOVING_OBJECT")
    if pedestrian is None:
        raise RuntimeError("Required pedestrian DEF MOVING_OBJECT was not found")
    translation = pedestrian.getField("translation")
    translation.setSFVec3f([crossing_x, start_y, 0.05])
    _log_event(
        movement_log,
        f"started x={crossing_x:.3f} y={start_y:.3f} speed={speed:.3f} "
        f"bounds=({lower_y:.3f},{upper_y:.3f}) direction={direction}",
    )
    print(
        "Scene Supervisor: moving MOVING_OBJECT continuously; "
        "no robot position, distance, emitter or navigation data is used.",
        flush=True,
    )
    while supervisor.step(timestep) != -1:
        current_y = translation.getSFVec3f()[1]
        previous_direction = direction
        next_y, direction = advance_ping_pong(
            current_y,
            direction,
            speed,
            dt,
            lower_y,
            upper_y,
        )
        translation.setSFVec3f([crossing_x, next_y, 0.05])
        if direction != previous_direction:
            _log_event(
                movement_log,
                f"reversed x={crossing_x:.3f} y={next_y:.3f} direction={direction}",
            )
            print(
                f"Scene Supervisor: pedestrian reversed at y={next_y:.3f}",
                flush=True,
            )


if __name__ == "__main__":
    run()
