from __future__ import annotations

import unittest
from pathlib import Path

import cv2
import numpy as np

from controllers.vision_controller.models import LaneEstimate, ObstacleDetection, ObstacleMotion
from controllers.vision_controller.perception import VisionPerception
from controllers.vision_proximity_controller.finish_marker import (
    detect_checkered_finish,
)
from tests.fixtures.generate_fixtures import write_fixtures


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class PerceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        write_fixtures(FIXTURES)

    def read(self, name: str):
        frame = cv2.imread(str(FIXTURES / name))
        self.assertIsNotNone(frame)
        return frame

    def test_centered_lane(self) -> None:
        result = VisionPerception().process_frame(self.read("lane_centered.png"))
        self.assertTrue(result.lane.visible)
        self.assertGreater(result.lane.confidence, 0.6)
        self.assertAlmostEqual(result.lane.normalized_error, 0.0, delta=0.08)

    def test_lane_error_direction(self) -> None:
        perception = VisionPerception()
        left = perception.process_frame(self.read("lane_left.png"))
        right = perception.process_frame(self.read("lane_right.png"))
        self.assertLess(left.lane.normalized_error, -0.05)
        self.assertGreater(right.lane.normalized_error, 0.05)

    def test_missing_lane(self) -> None:
        result = VisionPerception().process_frame(self.read("lane_missing.png"))
        self.assertFalse(result.lane.visible)
        self.assertEqual(result.lane.confidence, 0.0)

    def test_green_finish_marker(self) -> None:
        result = VisionPerception().process_frame(self.read("finish_visible.png"))
        self.assertTrue(result.finish_visible)

    def test_checkered_racing_finish_marker(self) -> None:
        frame = np.full((240, 320, 3), (42, 42, 42), dtype=np.uint8)
        cell_width, cell_height = 32, 20
        start_x, start_y = 64, 150
        for row in range(3):
            for column in range(6):
                color = (245, 245, 245) if (row + column) % 2 == 0 else (5, 5, 5)
                x0 = start_x + column * cell_width
                y0 = start_y + row * cell_height
                cv2.rectangle(
                    frame,
                    (x0, y0),
                    (x0 + cell_width - 1, y0 + cell_height - 1),
                    color,
                    -1,
                )
        self.assertTrue(detect_checkered_finish(frame))

    def test_lane_boundaries_are_not_a_checkered_finish(self) -> None:
        self.assertFalse(detect_checkered_finish(self.read("lane_centered.png")))

    def test_stationary_classification_uses_history(self) -> None:
        perception = VisionPerception()
        result = None
        for index in range(5):
            result = perception.process_frame(self.read("stationary_red.png"), timestamp=index * 0.1)
        self.assertIsNotNone(result)
        self.assertTrue(result.obstacle.present)
        self.assertEqual(result.obstacle.observed_color, "red")
        self.assertEqual(result.obstacle.motion, ObstacleMotion.STATIONARY)

    def test_moving_classification_uses_centroid_displacement(self) -> None:
        perception = VisionPerception()
        result = None
        for index in range(1, 5):
            result = perception.process_frame(
                self.read(f"moving_blue_{index}.png"),
                timestamp=index * 0.1,
            )
        self.assertIsNotNone(result)
        self.assertTrue(result.obstacle.present)
        self.assertEqual(result.obstacle.observed_color, "blue")
        self.assertEqual(result.obstacle.motion, ObstacleMotion.MOVING)

    def test_multiple_obstacles_are_returned_with_stable_track_ids(self) -> None:
        perception = VisionPerception()
        first_ids = None
        result = None
        for step in range(4):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.line(frame, (105, 30), (105, 239), (255, 255, 255), 5)
            cv2.line(frame, (215, 30), (215, 239), (255, 255, 255), 5)
            cv2.rectangle(frame, (120, 150), (155, 205), (0, 0, 255), -1)
            cv2.rectangle(
                frame,
                (175 + 12 * step, 135),
                (207 + 12 * step, 185),
                (255, 0, 0),
                -1,
            )
            result = perception.process_frame(frame, timestamp=step * 0.1)
            self.assertEqual(len(result.obstacles), 2)
            ids = {item.observed_color: item.track_id for item in result.obstacles}
            if first_ids is None:
                first_ids = ids
            self.assertEqual(ids, first_ids)
        self.assertIsNotNone(result)
        motions = {item.observed_color: item.motion for item in result.obstacles}
        self.assertEqual(motions["red"], ObstacleMotion.STATIONARY)
        self.assertEqual(motions["blue"], ObstacleMotion.MOVING)

    def test_path_blocked_requires_combined_corridor_coverage(self) -> None:
        perception = VisionPerception()
        lane = LaneEstimate(
            center_x=160.0,
            confidence=0.9,
            left_boundary_x=110.0,
            right_boundary_x=210.0,
        )
        obstacles = (
            ObstacleDetection(bbox=(95, 150, 65, 50), centroid=(127.5, 175.0)),
            ObstacleDetection(bbox=(160, 150, 65, 50), centroid=(192.5, 175.0)),
        )
        self.assertTrue(perception._path_blocked(obstacles, lane, 320, 240))


if __name__ == "__main__":
    unittest.main()
