from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from controllers.vision_controller.models import ControlCommand, ControllerState
from controllers.vision_controller.telemetry import TelemetryWriter
from tests.test_control import perception


class TelemetryTests(unittest.TestCase):
    def test_structured_row_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.csv"
            result = perception(lane_error=0.2)
            command = ControlCommand(3.0, 2.0, ControllerState.FOLLOW_LANE, "test")
            with TelemetryWriter(path) as writer:
                writer.write(result, command)
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["state"], "FOLLOW_LANE")
            self.assertEqual(rows[0]["reason"], "test")
            self.assertEqual(rows[0]["obstacle_present"], "0")
            self.assertEqual(rows[0]["obstacle_count"], "0")
            self.assertEqual(rows[0]["path_blocked"], "0")


if __name__ == "__main__":
    unittest.main()
