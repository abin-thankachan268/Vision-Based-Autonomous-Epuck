from __future__ import annotations

import unittest

from controllers.vision_controller.config import TrackerConfig
from controllers.vision_controller.models import ObstacleDetection, ObstacleMotion
from controllers.vision_controller.tracking import CentroidMotionTracker, MultiObjectTracker


class TrackingTests(unittest.TestCase):
    def test_unknown_until_minimum_history(self) -> None:
        tracker = CentroidMotionTracker(TrackerConfig())
        motion, _ = tracker.update((100.0, 100.0), 320, 240)
        self.assertEqual(motion, ObstacleMotion.UNKNOWN)

    def test_stationary_track(self) -> None:
        tracker = CentroidMotionTracker(TrackerConfig())
        motion = ObstacleMotion.UNKNOWN
        for point in ((100, 100), (101, 100), (100, 101), (101, 101)):
            motion, _ = tracker.update(point, 320, 240)
        self.assertEqual(motion, ObstacleMotion.STATIONARY)

    def test_moving_track(self) -> None:
        tracker = CentroidMotionTracker(TrackerConfig())
        motion = ObstacleMotion.UNKNOWN
        for point in ((80, 100), (100, 100), (120, 100), (145, 100)):
            motion, _ = tracker.update(point, 320, 240)
        self.assertEqual(motion, ObstacleMotion.MOVING)

    def test_tracker_resets_after_missed_frames(self) -> None:
        config = TrackerConfig(maximum_missed_frames=2)
        tracker = CentroidMotionTracker(config)
        for point in ((80, 100), (100, 100), (120, 100), (145, 100)):
            tracker.update(point, 320, 240)
        for _ in range(3):
            motion, _ = tracker.update(None, 320, 240)
        self.assertEqual(motion, ObstacleMotion.NONE)
        motion, _ = tracker.update((100, 100), 320, 240)
        self.assertEqual(motion, ObstacleMotion.UNKNOWN)

    def test_multiple_same_colour_tracks_keep_independent_histories(self) -> None:
        tracker = MultiObjectTracker(TrackerConfig())
        first_ids = None
        tracked = ()
        for step in range(4):
            detections = (
                ObstacleDetection(
                    bbox=(60, 130, 30, 40),
                    centroid=(75.0, 150.0),
                    area_fraction=0.02,
                    observed_color="red",
                    confidence=0.8,
                ),
                ObstacleDetection(
                    bbox=(205 + 15 * step, 130, 30, 40),
                    centroid=(220.0 + 15 * step, 150.0),
                    area_fraction=0.02,
                    observed_color="red",
                    confidence=0.8,
                ),
            )
            tracked = tracker.update(detections, 320, 240)
            ids = tuple(item.track_id for item in tracked)
            if first_ids is None:
                first_ids = ids
            self.assertEqual(ids, first_ids)
        self.assertEqual(tracked[0].motion, ObstacleMotion.STATIONARY)
        self.assertEqual(tracked[1].motion, ObstacleMotion.MOVING)
        self.assertNotEqual(tracked[0].track_id, tracked[1].track_id)


if __name__ == "__main__":
    unittest.main()
