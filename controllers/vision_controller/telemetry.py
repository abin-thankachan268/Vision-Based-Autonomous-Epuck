"""Structured CSV telemetry for reproducible controller runs."""

from __future__ import annotations

import csv
from pathlib import Path

from .models import ControlCommand, PerceptionResult


class TelemetryWriter:
    FIELDS = (
        "time_s",
        "state",
        "reason",
        "lane_center_x",
        "lane_error_normalized",
        "lane_confidence",
        "obstacle_count",
        "path_blocked",
        "obstacle_present",
        "primary_track_id",
        "obstacle_color",
        "obstacle_motion",
        "obstacle_confidence",
        "obstacle_threat_score",
        "left_speed",
        "right_speed",
    )

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._handle = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._handle, fieldnames=self.FIELDS)
        self._writer.writeheader()

    def write(self, result: PerceptionResult, command: ControlCommand) -> None:
        obstacle = result.obstacle
        self._writer.writerow(
            {
                "time_s": f"{result.timestamp:.3f}",
                "state": command.state.value,
                "reason": command.reason,
                "lane_center_x": "" if result.lane.center_x is None else f"{result.lane.center_x:.3f}",
                "lane_error_normalized": f"{result.lane.normalized_error:.6f}",
                "lane_confidence": f"{result.lane.confidence:.6f}",
                "obstacle_count": len(result.obstacles) or int(obstacle.present),
                "path_blocked": int(result.path_blocked),
                "obstacle_present": int(obstacle.present),
                "primary_track_id": obstacle.track_id if obstacle.present else "",
                "obstacle_color": obstacle.observed_color,
                "obstacle_motion": obstacle.motion.value,
                "obstacle_confidence": f"{obstacle.confidence:.6f}",
                "obstacle_threat_score": f"{obstacle.threat_score:.6f}",
                "left_speed": f"{command.left_speed:.6f}",
                "right_speed": f"{command.right_speed:.6f}",
            }
        )
        self._handle.flush()

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.close()

    def __enter__(self) -> "TelemetryWriter":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
