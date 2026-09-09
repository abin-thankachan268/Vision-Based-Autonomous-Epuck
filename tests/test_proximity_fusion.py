from __future__ import annotations

import unittest

from controllers.vision_controller.models import (
    LaneEstimate,
    ObstacleDetection,
    ObstacleMotion,
    PerceptionResult,
)
from controllers.vision_controller.models import ControlCommand, ControllerState
from controllers.vision_proximity_controller.console_logging import (
    DecisionConsoleLogger,
    decision_log_line,
    perception_log_line,
    sensor_log_line,
)
from controllers.vision_proximity_controller.proximity import (
    ProximityConfig,
    ProximitySafetyLayer,
)


def command(
    left: float = 3.0,
    right: float = 3.0,
    state: ControllerState = ControllerState.FOLLOW_LANE,
) -> ControlCommand:
    return ControlCommand(left, right, state, "camera")


class ProximityFusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layer = ProximitySafetyLayer()

    def test_clear_readings_preserve_camera_command(self) -> None:
        base = command(3.1, 2.9)
        decision = self.layer.apply(base, [0] * 8)
        self.assertEqual(decision.command, base)
        self.assertFalse(decision.active)

    def test_right_obstacle_turns_left(self) -> None:
        readings = [400, 250, 100, 0, 0, 0, 0, 0]
        decision = self.layer.apply(command(), readings)
        self.assertTrue(decision.active)
        self.assertLess(decision.command.left_speed, decision.command.right_speed)

    def test_left_obstacle_turns_right(self) -> None:
        readings = [0, 0, 0, 0, 0, 100, 250, 400]
        decision = self.layer.apply(command(), readings)
        self.assertTrue(decision.active)
        self.assertGreater(decision.command.left_speed, decision.command.right_speed)

    def test_side_sensor_biases_turn_after_forward_activation(self) -> None:
        decision = self.layer.apply(command(), [190, 0, 0, 0, 0, 1000, 0, 0])
        self.assertTrue(decision.active)
        self.assertGreater(decision.command.left_speed, decision.command.right_speed)

    def test_right_side_hazard_triggers_left_clearance(self) -> None:
        decision = self.layer.apply(command(), [0, 0, 500, 0, 0, 0, 0, 0])
        self.assertEqual(decision.hazard_region, "side")
        self.assertLess(decision.command.left_speed, decision.command.right_speed)

    def test_side_sensor_does_not_cancel_camera_static_avoidance(self) -> None:
        base = command(1.7, 3.9, ControllerState.AVOID)
        decision = self.layer.apply(base, [0, 0, 500, 0, 0, 0, 0, 0])
        self.assertEqual(decision.command, base)
        self.assertEqual(decision.hazard_region, "side_monitor")

    def test_rear_hazard_moves_forward_away_from_approaching_object(self) -> None:
        stopped = command(0.0, 0.0, ControllerState.STOP_WAIT)
        decision = self.layer.apply(stopped, [0, 0, 0, 500, 0, 0, 0, 0])
        self.assertEqual(decision.hazard_region, "rear")
        self.assertGreater(decision.command.left_speed, 0.0)
        self.assertGreater(decision.command.right_speed, 0.0)
        self.assertLess(decision.command.left_speed, decision.command.right_speed)

    def test_terminal_stop_is_not_overridden_by_rear_sensor(self) -> None:
        finished = command(0.0, 0.0, ControllerState.FINISHED)
        decision = self.layer.apply(finished, [0, 0, 0, 500, 0, 0, 0, 0])
        self.assertEqual(decision.command, finished)

    def test_emergency_reading_sharpens_turn_during_camera_motion(self) -> None:
        decision = self.layer.apply(command(), [1200, 0, 0, 0, 0, 0, 0, 0])
        self.assertLess(decision.command.left_speed, decision.command.right_speed)
        self.assertGreaterEqual(decision.command.left_speed, 0.0)

    def test_camera_stop_is_retained_for_non_emergency_front_proximity(self) -> None:
        base = command(0.0, 0.0, ControllerState.STOP_WAIT)
        decision = self.layer.apply(base, [200, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(decision.command, base)
        self.assertIn("stop retained", decision.reason)

    def test_emergency_can_escape_from_camera_stop(self) -> None:
        base = command(0.0, 0.0, ControllerState.STOP_WAIT)
        decision = self.layer.apply(base, [1200, 0, 0, 0, 0, 0, 0, 0])
        self.assertLess(decision.command.left_speed, 0.0)
        self.assertLess(decision.command.right_speed, 0.0)

    def test_hysteresis_requires_consecutive_clear_frames(self) -> None:
        config = ProximityConfig(clear_frames=3)
        layer = ProximitySafetyLayer(config)
        layer.apply(command(), [200, 0, 0, 0, 0, 0, 0, 0])
        self.assertTrue(layer.apply(command(), [0] * 8).active)
        self.assertTrue(layer.apply(command(), [0] * 8).active)
        self.assertFalse(layer.apply(command(), [0] * 8).active)

    def test_eight_readings_are_required(self) -> None:
        with self.assertRaises(ValueError):
            self.layer.apply(command(), [0, 0])

    def test_console_lines_explain_perception_sensors_and_fused_decision(self) -> None:
        result = PerceptionResult(
            lane=LaneEstimate(center_x=31.5, normalized_error=-0.1, confidence=0.9),
            obstacles=(
                ObstacleDetection(
                    track_id=4,
                    bbox=(1, 2, 3, 4),
                    centroid=(20.0, 30.0),
                    observed_color="red",
                    motion=ObstacleMotion.STATIONARY,
                    confidence=0.8,
                ),
            ),
            path_blocked=True,
        )
        base = command()
        decision = self.layer.apply(base, [400, 200, 0, 0, 0, 0, 0, 0])
        self.assertIn("lane=VISIBLE", perception_log_line(1.0, result))
        self.assertIn("red/stationary", perception_log_line(1.0, result))
        self.assertIn("path=BLOCKED", perception_log_line(1.0, result))
        self.assertIn("ps0= 400.0", sensor_log_line([400, 200, 0, 0, 0, 0, 0, 0], decision))
        self.assertIn("fusion=OVERRIDE", decision_log_line(base, decision))

    def test_console_logger_is_periodic_and_reacts_to_decision_changes(self) -> None:
        logger = DecisionConsoleLogger(0.5)
        result = PerceptionResult(lane=LaneEstimate(center_x=32.0, confidence=1.0))
        base = command()
        clear = self.layer.apply(base, [0] * 8)
        self.assertTrue(logger.should_log(0.0, result, base, clear))
        self.assertFalse(logger.should_log(0.1, result, base, clear))
        self.assertTrue(logger.should_log(0.5, result, base, clear))
        active = self.layer.apply(base, [400, 0, 0, 0, 0, 0, 0, 0])
        self.assertTrue(logger.should_log(0.6, result, base, active))


if __name__ == "__main__":
    unittest.main()
