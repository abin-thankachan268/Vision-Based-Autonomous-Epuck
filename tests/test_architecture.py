from __future__ import annotations

import hashlib
import os
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_baseline_is_exact_local_copy(self) -> None:
        original = ROOT / "controllers" / "e_puck" / "e_puck.py"
        baseline = ROOT / "controllers" / "baseline_ground" / "baseline_ground.py"
        self.assertEqual(
            hashlib.sha256(original.read_bytes()).digest(),
            hashlib.sha256(baseline.read_bytes()).digest(),
        )

    def test_vision_entrypoint_has_no_ground_sensor_or_receiver_devices(self) -> None:
        source = (
            ROOT
            / "controllers"
            / "vision_controller"
            / "vision_controller.py"
        ).read_text(encoding="utf-8")
        forbidden = ("gs0", "gs1", "gs2", "receiver", "dist_robot", "sup_ped_distance")
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_fused_entrypoint_uses_all_proximity_sensors_without_ground_truth(self) -> None:
        source = (
            ROOT
            / "controllers"
            / "vision_proximity_controller"
            / "vision_proximity_controller.py"
        ).read_text(encoding="utf-8")
        self.assertIn("range(8)", source)
        self.assertIn('robot.getDevice(f"ps{index}")', source)
        forbidden = (
            "gs0",
            "gs1",
            "gs2",
            "receiver",
            "dist_robot",
            "sup_ped_distance",
            "getFromDef",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_interactive_fusion_waits_for_additional_obstacle_clear_frames(self) -> None:
        from controllers.vision_proximity_controller.vision_proximity_controller import (
            _camera_config,
        )

        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(_camera_config().control.clear_obstacle_frames, 24)


if __name__ == "__main__":
    unittest.main()
