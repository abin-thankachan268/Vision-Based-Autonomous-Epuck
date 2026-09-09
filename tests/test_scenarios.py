from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScenarioMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(
            (ROOT / "scenarios" / "scenarios.json").read_text(encoding="utf-8")
        )
        cls.scenarios = payload["scenarios"]

    def test_fifteen_unique_scenarios(self) -> None:
        identifiers = [scenario["id"] for scenario in self.scenarios]
        self.assertEqual(len(identifiers), 15)
        self.assertEqual(len(set(identifiers)), 15)

    def test_required_category_counts(self) -> None:
        counts = {
            category: sum(scenario["category"] == category for scenario in self.scenarios)
            for category in ("lane", "stationary", "moving", "multi")
        }
        self.assertEqual(
            counts,
            {"lane": 6, "stationary": 3, "moving": 3, "multi": 3},
        )

    def test_required_moving_speeds_and_static_positions(self) -> None:
        speeds = sorted(
            scenario["moving_speed"]
            for scenario in self.scenarios
            if scenario["category"] == "moving"
        )
        positions = sorted(
            scenario["static_position"]
            for scenario in self.scenarios
            if scenario["category"] == "stationary"
        )
        self.assertEqual(speeds, [0.10, 0.15, 0.20])
        self.assertEqual(positions, ["center", "left", "right"])

    def test_multi_obstacle_layouts_are_present(self) -> None:
        layouts = {
            scenario.get("obstacle_layout")
            for scenario in self.scenarios
            if scenario["category"] == "multi"
        }
        self.assertEqual(layouts, {"multi_static", "multi_moving", "mixed"})
