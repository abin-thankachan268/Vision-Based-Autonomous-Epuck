"""Combined camera/proximity telemetry for the interactive controller."""

from __future__ import annotations

import csv
from pathlib import Path


class FusionTelemetryWriter:
    def __init__(self, path: Path) -> None:
        self.handle = path.open("w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.handle)
        self.writer.writerow(
            [
                "time_s",
                "ps0",
                "ps1",
                "ps2",
                "ps3",
                "ps4",
                "ps5",
                "ps6",
                "ps7",
                "peak_front",
                "proximity_active",
                "hazard_region",
                "turn_direction",
                "camera_state",
                "left_speed",
                "right_speed",
                "reason",
            ]
        )

    def write(self, time_s, readings, decision) -> None:
        command = decision.command
        self.writer.writerow(
            [
                f"{time_s:.3f}",
                *(f"{value:.3f}" for value in readings),
                f"{decision.peak_front_value:.3f}",
                int(decision.active),
                decision.hazard_region,
                decision.turn_direction,
                command.state.value,
                f"{command.left_speed:.6f}",
                f"{command.right_speed:.6f}",
                decision.reason,
            ]
        )

    def close(self) -> None:
        self.handle.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
