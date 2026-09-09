from __future__ import annotations

import unittest

from controllers.experiment_supervisor.metrics import RunAccumulator, oval_lane_error


class MetricTests(unittest.TestCase):
    def test_lane_error_on_straights_and_curves(self) -> None:
        self.assertAlmostEqual(oval_lane_error(0.0, -0.45), 0.0, places=6)
        self.assertAlmostEqual(oval_lane_error(0.0, 0.45), 0.0, places=6)
        self.assertAlmostEqual(oval_lane_error(1.20, 0.0), 0.0, places=6)
        self.assertAlmostEqual(oval_lane_error(-1.20, 0.0), 0.0, places=6)
        self.assertAlmostEqual(oval_lane_error(0.0, -0.35), 0.10, places=6)

    def test_collision_count_uses_contact_edges(self) -> None:
        accumulator = RunAccumulator()
        accumulator.update(0.01, 0.20, 0.20)
        accumulator.update(0.01, 0.05, 0.20)
        accumulator.update(0.01, 0.04, 0.20)
        accumulator.update(0.01, 0.20, 0.20)
        accumulator.update(0.01, 0.05, 0.20)
        self.assertEqual(accumulator.collision_count, 2)

    def test_lane_summary(self) -> None:
        accumulator = RunAccumulator()
        accumulator.update(0.02, 1.0, 1.0)
        accumulator.update(0.04, 1.0, 1.0)
        accumulator.update(0.30, 1.0, 1.0)
        self.assertAlmostEqual(accumulator.mean_lane_error, 0.12)
        self.assertAlmostEqual(accumulator.maximum_lane_error, 0.30)
        self.assertAlmostEqual(accumulator.within_lane_fraction, 2 / 3)


if __name__ == "__main__":
    unittest.main()
