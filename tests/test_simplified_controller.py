from __future__ import annotations

import unittest
from pathlib import Path

import cv2
import numpy as np

from controllers.e_puck_controller.control import (
    ControlConfig,
    NavigationState,
    PDController,
    SimpleNavigator,
)
from controllers.e_puck_controller.vision import (
    LaneObservation,
    MotionClass,
    ObstacleObservation,
    SceneObservation,
    SimpleVision,
)
from controllers.scene_supervisor.scene_supervisor import advance_ping_pong


FIXTURES = Path(__file__).parent / "fixtures"


def scene(
    *,
    lane_visible: bool = True,
    obstacle: MotionClass = MotionClass.NONE,
    obstacle_x: float = 150.0,
) -> SceneObservation:
    lane = (
        LaneObservation(160.0, 0.0, 0.9, 120.0, 200.0)
        if lane_visible
        else LaneObservation()
    )
    detected = (
        ObstacleObservation()
        if obstacle == MotionClass.NONE
        else ObstacleObservation(
            color="blue" if obstacle == MotionClass.MOVING else "red",
            bbox=(int(obstacle_x - 20), 150, 40, 40),
            centroid=(obstacle_x, 170.0),
            area_fraction=0.02,
            motion=obstacle,
            motion_confidence=1.0,
        )
    )
    return SceneObservation(lane, detected, False, 320, 240)


class SimplifiedVisionTests(unittest.TestCase):
    def read(self, name: str):
        image = cv2.imread(str(FIXTURES / name))
        self.assertIsNotNone(image)
        return image

    def test_fixed_hsv_lane_detection_reports_direction_and_loss(self) -> None:
        centered = SimpleVision().process_frame(self.read("lane_centered.png"))
        left = SimpleVision().process_frame(self.read("lane_left.png"))
        right = SimpleVision().process_frame(self.read("lane_right.png"))
        missing = SimpleVision().process_frame(self.read("lane_missing.png"))
        self.assertAlmostEqual(centered.lane.error, 0.0, delta=0.02)
        self.assertLess(left.lane.error, 0.0)
        self.assertGreater(right.lane.error, 0.0)
        self.assertFalse(missing.lane.visible)

    def test_relevant_object_tracker_classifies_stationary_target(self) -> None:
        vision = SimpleVision()
        result = None
        frame = self.read("stationary_red.png")
        for _ in range(4):
            result = vision.process_frame(frame)
        self.assertIsNotNone(result)
        self.assertEqual(result.obstacle.color, "red")
        self.assertEqual(result.obstacle.motion, MotionClass.STATIONARY)

    def test_relevant_object_tracker_classifies_moving_target(self) -> None:
        vision = SimpleVision()
        result = None
        for index in range(1, 5):
            result = vision.process_frame(self.read(f"moving_blue_{index}.png"))
        self.assertIsNotNone(result)
        self.assertEqual(result.obstacle.color, "blue")
        self.assertEqual(result.obstacle.motion, MotionClass.MOVING)

    def test_single_white_strip_filling_frame_is_not_two_boundaries(self) -> None:
        frame = np.full((240, 320, 3), 255, dtype=np.uint8)
        result = SimpleVision().process_frame(frame)
        self.assertFalse(result.lane.visible)

    def test_transverse_white_stripe_is_not_lane_boundaries(self) -> None:
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(frame, (0, 90), (319, 110), (255, 255, 255), -1)
        result = SimpleVision().process_frame(frame)
        self.assertFalse(result.lane.visible)

    def test_thin_horizon_strips_are_not_lane_boundaries(self) -> None:
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(frame, (0, 36), (70, 44), (255, 255, 255), -1)
        cv2.rectangle(frame, (240, 36), (319, 48), (255, 255, 255), -1)
        result = SimpleVision().process_frame(frame)
        self.assertFalse(result.lane.visible)


class SimplifiedControlTests(unittest.TestCase):
    def config(self) -> ControlConfig:
        return ControlConfig(
            clear_frames=2,
            rejoin_confirm_frames=2,
            avoidance_commit_seconds=0.2,
            avoidance_first_leg_seconds=0.1,
            lost_lane_frames=2,
        )

    def test_pd_has_no_integral_accumulation(self) -> None:
        pd = PDController(kp=2.0, kd=0.5)
        first = pd.update(0.25, 0.1)
        second = pd.update(0.25, 0.1)
        third = pd.update(0.25, 0.1)
        self.assertAlmostEqual(first, 0.5)
        self.assertAlmostEqual(second, 0.5)
        self.assertAlmostEqual(third, 0.5)

    def test_large_rejoin_error_never_reverses_a_wheel(self) -> None:
        navigator = SimpleNavigator(self.config())
        navigator.state = NavigationState.REJOIN
        partial = SceneObservation(
            LaneObservation(260.0, 0.75, 0.61, None, 295.0),
            ObstacleObservation(),
            False,
            320,
            240,
        )
        command = navigator.step(partial, [0] * 8, 0.1)
        self.assertGreaterEqual(command.left_speed, 0.0)
        self.assertGreaterEqual(command.right_speed, 0.0)

    def test_moving_object_stops_then_rejoins_lane(self) -> None:
        navigator = SimpleNavigator(self.config())
        stopped = navigator.step(scene(obstacle=MotionClass.MOVING), [0] * 8, 0.1)
        self.assertEqual(stopped.state, NavigationState.STOP_WAIT)
        self.assertEqual((stopped.left_speed, stopped.right_speed), (0.0, 0.0))
        navigator.step(scene(), [0] * 8, 0.1)
        rejoin = navigator.step(scene(), [0] * 8, 0.1)
        self.assertEqual(rejoin.state, NavigationState.REJOIN)
        navigator.step(scene(), [0] * 8, 0.1)
        following = navigator.step(scene(), [0] * 8, 0.1)
        self.assertEqual(following.state, NavigationState.FOLLOW_LANE)

    def test_blue_object_waits_even_at_stationary_crossing_endpoint(self) -> None:
        navigator = SimpleNavigator(self.config())
        blue = SceneObservation(
            LaneObservation(160.0, 0.0, 0.9, 120.0, 200.0),
            ObstacleObservation(
                color="blue",
                bbox=(130, 150, 40, 40),
                centroid=(150.0, 170.0),
                area_fraction=0.02,
                motion=MotionClass.STATIONARY,
                motion_confidence=1.0,
            ),
            False,
            320,
            240,
        )
        command = navigator.step(blue, [0] * 8, 0.1)
        self.assertEqual(command.state, NavigationState.STOP_WAIT)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_stationary_object_enters_avoidance_and_uses_proximity(self) -> None:
        navigator = SimpleNavigator(self.config())
        avoiding = navigator.step(
            scene(obstacle=MotionClass.STATIONARY, obstacle_x=130.0), [0] * 8, 0.1
        )
        self.assertEqual(avoiding.state, NavigationState.AVOID)
        close = navigator.step(
            scene(obstacle=MotionClass.STATIONARY),
            [0, 0, 0, 0, 0, 0, 500, 600],
            0.1,
        )
        self.assertEqual(close.state, NavigationState.AVOID)
        self.assertNotEqual(close.left_speed, close.right_speed)
        self.assertIn("proximity-guided", close.reason)

    def test_centered_obstacle_prefers_inside_left_shoulder(self) -> None:
        navigator = SimpleNavigator(self.config())
        command = navigator.step(
            scene(obstacle=MotionClass.STATIONARY, obstacle_x=160.0), [0] * 8, 0.05
        )
        self.assertEqual(command.state, NavigationState.AVOID)
        self.assertLess(command.left_speed, command.right_speed)

    def test_nominal_avoidance_contains_straight_passing_stage(self) -> None:
        config = ControlConfig(
            avoidance_first_leg_seconds=0.1,
            avoidance_straight_seconds=0.2,
            avoidance_commit_seconds=0.5,
        )
        navigator = SimpleNavigator(config)
        navigator.step(scene(obstacle=MotionClass.STATIONARY), [0] * 8, 0.05)
        command = navigator.step(scene(), [0] * 8, 0.15)
        self.assertEqual(command.state, NavigationState.AVOID)
        self.assertAlmostEqual(command.left_speed, command.right_speed)

    def test_proximity_danger_causes_stop_without_camera_object(self) -> None:
        navigator = SimpleNavigator(self.config())
        command = navigator.step(scene(), [500, 0, 0, 0, 0, 0, 0, 0], 0.1)
        self.assertEqual(command.state, NavigationState.STOP_WAIT)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_persistent_proximity_danger_stops_then_escapes(self) -> None:
        navigator = SimpleNavigator(self.config())
        values = [500, 0, 0, 0, 0, 0, 0, 0]
        navigator.step(scene(), values, 0.1)
        navigator.step(scene(), values, 0.1)
        navigator.step(scene(), values, 0.1)
        command = navigator.step(scene(), values, 0.1)
        self.assertEqual(command.state, NavigationState.AVOID)
        self.assertNotEqual(command.left_speed, command.right_speed)
        self.assertIn("proximity-guided", command.reason)

    def test_emergency_proximity_reverses_instead_of_deadlocking(self) -> None:
        navigator = SimpleNavigator(self.config())
        navigator.state = NavigationState.AVOID
        command = navigator.step(
            scene(obstacle=MotionClass.STATIONARY),
            [900, 800, 0, 0, 0, 0, 200, 300],
            0.1,
        )
        self.assertEqual(command.state, NavigationState.AVOID)
        self.assertLess(command.left_speed, 0.0)
        self.assertLess(command.right_speed, 0.0)
        self.assertIn("reverse-turn", command.reason)

    def test_handled_red_obstacle_is_not_immediately_retriggered(self) -> None:
        navigator = SimpleNavigator(self.config())
        navigator.step(scene(obstacle=MotionClass.STATIONARY), [0] * 8, 0.1)
        navigator.step(scene(), [0] * 8, 0.2)
        navigator.step(scene(), [0] * 8, 0.2)
        self.assertEqual(navigator.state, NavigationState.REJOIN)
        command = navigator.step(
            scene(obstacle=MotionClass.STATIONARY), [150] + [0] * 7, 0.1
        )
        self.assertIn(
            command.state, (NavigationState.REJOIN, NavigationState.FOLLOW_LANE)
        )
        self.assertGreater(command.left_speed, 0.0)
        self.assertGreater(command.right_speed, 0.0)
        self.assertIn("lane", command.reason)

    def test_side_proximity_does_not_cancel_new_rejoin_grace_period(self) -> None:
        config = ControlConfig(
            clear_frames=1,
            avoidance_commit_seconds=0.1,
            rejoin_confirm_frames=2,
        )
        navigator = SimpleNavigator(config)
        navigator.state = NavigationState.AVOID
        navigator.state_elapsed = 0.1
        command = navigator.step(scene(), [0, 0, 800, 0, 0, 0, 0, 0], 0.1)
        self.assertEqual(command.state, NavigationState.REJOIN)
        self.assertGreater(command.left_speed, 0.0)
        self.assertGreater(command.right_speed, 0.0)

    def test_lane_loss_recovers_or_fails_safe(self) -> None:
        navigator = SimpleNavigator(self.config())
        navigator.step(scene(lane_visible=False), [0] * 8, 0.1)
        recovery = navigator.step(scene(lane_visible=False), [0] * 8, 0.1)
        self.assertEqual(recovery.state, NavigationState.REJOIN)
        self.assertGreater(recovery.left_speed, 0.0)
        self.assertGreater(recovery.right_speed, 0.0)

    def test_partial_boundary_guides_post_avoidance_rejoin(self) -> None:
        navigator = SimpleNavigator(self.config())
        navigator.state = NavigationState.REJOIN
        navigator.rejoining_after_avoidance = True
        navigator.state_elapsed = 4.0
        partial = SceneObservation(
            LaneObservation(80.0, -0.5, 0.45, 45.0, None),
            ObstacleObservation(),
            False,
            320,
            240,
        )
        command = navigator.step(partial, [0] * 8, 0.1)
        self.assertEqual(command.state, NavigationState.REJOIN)
        self.assertNotEqual(command.left_speed, command.right_speed)
        self.assertIn("single-boundary", command.reason)

    def test_finish_stops_motors(self) -> None:
        navigator = SimpleNavigator(self.config())
        command = navigator.step(scene(), [0] * 8, 0.1, finish_detected=True)
        self.assertEqual(command.state, NavigationState.FINISHED)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))


class SimplifiedSupervisorTests(unittest.TestCase):
    def test_pedestrian_moves_at_constant_speed_and_reflects(self) -> None:
        value, direction = advance_ping_pong(0.48, -1, 0.15, 0.2, 0.12, 0.78)
        self.assertAlmostEqual(value, 0.45)
        self.assertEqual(direction, -1)
        value, direction = advance_ping_pong(0.13, -1, 0.15, 0.2, 0.12, 0.78)
        self.assertAlmostEqual(value, 0.14)
        self.assertEqual(direction, 1)


if __name__ == "__main__":
    unittest.main()
