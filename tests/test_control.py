from __future__ import annotations

import unittest

from controllers.vision_controller.config import ControlConfig, ControllerConfig
from controllers.vision_controller.control import VisionControllerCore
from controllers.vision_controller.models import (
    ControllerState,
    LaneEstimate,
    ObstacleDetection,
    ObstacleMotion,
    PerceptionResult,
)


def perception(
    lane_confidence: float = 0.9,
    lane_error: float = 0.0,
    motion: ObstacleMotion = ObstacleMotion.NONE,
    obstacle_present: bool = False,
    obstacles: tuple[ObstacleDetection, ...] = (),
    path_blocked: bool = False,
) -> PerceptionResult:
    obstacle = (
        ObstacleDetection(
            bbox=(140, 120, 40, 50),
            centroid=(160.0, 145.0),
            area_fraction=0.03,
            observed_color="blue" if motion == ObstacleMotion.MOVING else "red",
            motion=motion,
            confidence=0.9,
        )
        if obstacle_present
        else ObstacleDetection()
    )
    selected = obstacles[0] if obstacles else obstacle
    return PerceptionResult(
        lane=LaneEstimate(
            center_x=160.0 if lane_confidence else None,
            normalized_error=lane_error,
            confidence=lane_confidence,
            left_boundary_x=70.0 if lane_confidence else None,
            right_boundary_x=250.0 if lane_confidence else None,
        ),
        obstacle=selected,
        obstacles=obstacles,
        frame_width=320,
        frame_height=240,
        path_blocked=path_blocked,
    )


class ControlTests(unittest.TestCase):
    def setUp(self) -> None:
        control = ControlConfig(
            lost_lane_frames=2,
            clear_obstacle_frames=2,
            stationary_confirm_frames=1,
            rejoin_confirm_frames=2,
            rejoin_timeout_seconds=0.5,
            stop_wait_timeout_seconds=0.5,
            avoidance_timeout_seconds=0.5,
            avoidance_leg_seconds=0.0,
            avoidance_commit_seconds=0.0,
        )
        self.core = VisionControllerCore(ControllerConfig(control=control))

    def test_follow_lane_generates_camera_based_motor_command(self) -> None:
        command = self.core.step(perception(lane_error=0.2), 0.1)
        self.assertEqual(command.state, ControllerState.FOLLOW_LANE)
        self.assertGreater(command.left_speed, command.right_speed)

    def test_follow_to_stop_wait_for_moving_obstacle(self) -> None:
        command = self.core.step(
            perception(motion=ObstacleMotion.MOVING, obstacle_present=True),
            0.1,
        )
        self.assertEqual(command.state, ControllerState.STOP_WAIT)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_follow_to_avoid_for_stationary_obstacle(self) -> None:
        command = self.core.step(
            perception(motion=ObstacleMotion.STATIONARY, obstacle_present=True),
            0.1,
        )
        self.assertEqual(command.state, ControllerState.AVOID)
        self.assertNotEqual(command.left_speed, command.right_speed)

    def test_unknown_obstacle_stops_while_classifying(self) -> None:
        command = self.core.step(
            perception(motion=ObstacleMotion.UNKNOWN, obstacle_present=True),
            0.1,
        )
        self.assertEqual(command.state, ControllerState.STOP_WAIT)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_stop_wait_to_avoid_when_object_becomes_stationary(self) -> None:
        self.core.step(perception(motion=ObstacleMotion.UNKNOWN, obstacle_present=True), 0.1)
        command = self.core.step(
            perception(motion=ObstacleMotion.STATIONARY, obstacle_present=True),
            0.1,
        )
        self.assertEqual(command.state, ControllerState.AVOID)

    def test_stop_wait_to_rejoin_when_object_clears(self) -> None:
        self.core.step(perception(motion=ObstacleMotion.MOVING, obstacle_present=True), 0.1)
        self.core.step(perception(), 0.1)
        command = self.core.step(perception(), 0.1)
        self.assertEqual(command.state, ControllerState.REJOIN)

    def test_avoid_to_rejoin_when_object_clears(self) -> None:
        self.core.step(perception(motion=ObstacleMotion.STATIONARY, obstacle_present=True), 0.1)
        self.core.step(perception(), 0.1)
        command = self.core.step(perception(), 0.1)
        self.assertEqual(command.state, ControllerState.REJOIN)

    def test_lane_loss_to_rejoin(self) -> None:
        self.core.step(perception(lane_confidence=0.0), 0.1)
        command = self.core.step(perception(lane_confidence=0.0), 0.1)
        self.assertEqual(command.state, ControllerState.REJOIN)

    def test_rejoin_to_follow_after_confirmed_lane(self) -> None:
        self.core.step(perception(lane_confidence=0.0), 0.1)
        self.core.step(perception(lane_confidence=0.0), 0.1)
        self.core.step(perception(), 0.1)
        command = self.core.step(perception(), 0.1)
        self.assertEqual(command.state, ControllerState.FOLLOW_LANE)

    def test_rejoin_timeout_enters_failsafe(self) -> None:
        self.core.step(perception(lane_confidence=0.0), 0.1)
        self.core.step(perception(lane_confidence=0.0), 0.1)
        command = self.core.step(perception(lane_confidence=0.0), 0.6)
        self.assertEqual(command.state, ControllerState.FAILSAFE)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_stop_wait_timeout_enters_failsafe(self) -> None:
        moving = perception(motion=ObstacleMotion.MOVING, obstacle_present=True)
        self.core.step(moving, 0.1)
        command = self.core.step(moving, 0.6)
        self.assertEqual(command.state, ControllerState.FAILSAFE)

    def test_avoidance_timeout_enters_failsafe(self) -> None:
        stationary = perception(motion=ObstacleMotion.STATIONARY, obstacle_present=True)
        self.core.step(stationary, 0.1)
        command = self.core.step(stationary, 0.6)
        self.assertEqual(command.state, ControllerState.FAILSAFE)

    def test_obstacle_interrupts_rejoin(self) -> None:
        self.core.step(perception(lane_confidence=0.0), 0.1)
        self.core.step(perception(lane_confidence=0.0), 0.1)
        command = self.core.step(
            perception(motion=ObstacleMotion.MOVING, obstacle_present=True),
            0.1,
        )
        self.assertEqual(command.state, ControllerState.STOP_WAIT)

    def test_finish_transition(self) -> None:
        command = self.core.step(perception(), 0.1, finish_detected=True)
        self.assertEqual(command.state, ControllerState.FINISHED)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_terminal_states_remain_stopped(self) -> None:
        self.core.step(perception(), 0.1, finish_detected=True)
        command = self.core.step(perception(), 0.1)
        self.assertEqual(command.state, ControllerState.FINISHED)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_blocked_multi_obstacle_corridor_stops_safely(self) -> None:
        stationary = ObstacleDetection(
            track_id=1,
            bbox=(110, 130, 50, 60),
            centroid=(135.0, 160.0),
            area_fraction=0.03,
            observed_color="red",
            motion=ObstacleMotion.STATIONARY,
            confidence=0.9,
        )
        second = ObstacleDetection(
            track_id=2,
            bbox=(160, 130, 50, 60),
            centroid=(185.0, 160.0),
            area_fraction=0.03,
            observed_color="red",
            motion=ObstacleMotion.STATIONARY,
            confidence=0.9,
        )
        command = self.core.step(
            perception(obstacles=(stationary, second), path_blocked=True),
            0.1,
        )
        self.assertEqual(command.state, ControllerState.STOP_WAIT)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))

    def test_moving_obstacle_interrupts_stationary_avoidance(self) -> None:
        stationary = ObstacleDetection(
            track_id=1,
            bbox=(120, 130, 40, 50),
            centroid=(140.0, 155.0),
            area_fraction=0.03,
            observed_color="red",
            motion=ObstacleMotion.STATIONARY,
            confidence=0.9,
        )
        moving = ObstacleDetection(
            track_id=2,
            bbox=(175, 125, 35, 50),
            centroid=(192.5, 150.0),
            area_fraction=0.025,
            observed_color="blue",
            motion=ObstacleMotion.MOVING,
            confidence=0.9,
        )
        self.core.step(perception(obstacles=(stationary,)), 0.1)
        command = self.core.step(perception(obstacles=(moving, stationary)), 0.1)
        self.assertEqual(command.state, ControllerState.STOP_WAIT)
        self.assertEqual((command.left_speed, command.right_speed), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
