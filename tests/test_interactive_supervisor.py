from __future__ import annotations

import sys
import types
import unittest
from unittest import mock
from pathlib import Path

from controllers.interactive_supervisor.interactive_supervisor import (
    InteractiveSupervisor,
    MOVING_STARTS,
    advance_ping_pong,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_INTERACTIVE_WORLD = PROJECT_ROOT / "worlds" / "autonomous_epuck_interactive12.wbt"
EXTENDED_INTERACTIVE_WORLD = PROJECT_ROOT / "worlds" / "autonomous_epuck_interactive.wbt"


class FakeField:
    def __init__(self, value: list[float]) -> None:
        self.value = value

    def getSFVec3f(self) -> list[float]:
        return list(self.value)

    def setSFVec3f(self, value: list[float]) -> None:
        self.value = list(value)


class FakeNode:
    def __init__(self, translation: list[float]) -> None:
        self.translation = FakeField(translation)

    def getField(self, name: str) -> FakeField:
        if name != "translation":
            raise KeyError(name)
        return self.translation


class FakeSupervisor:
    def __init__(self, nodes: dict[str, FakeNode]) -> None:
        self.nodes = nodes

    def getBasicTimeStep(self) -> int:
        return 32

    def getFromDef(self, def_name: str) -> FakeNode | None:
        return self.nodes.get(def_name)

    def getTime(self) -> float:
        return 0.0


class InteractiveSupervisorTests(unittest.TestCase):
    def test_ping_pong_moves_at_constant_speed_between_frames(self) -> None:
        value, direction = advance_ping_pong(0.70, -1, 0.15, 0.20, 0.12, 0.78)
        self.assertAlmostEqual(value, 0.67)
        self.assertEqual(direction, -1)

    def test_ping_pong_reflects_at_lower_boundary(self) -> None:
        value, direction = advance_ping_pong(0.13, -1, 0.15, 0.20, 0.12, 0.78)
        self.assertAlmostEqual(value, 0.14)
        self.assertEqual(direction, 1)

    def test_one_moving_object_crosses_each_road_straight(self) -> None:
        self.assertEqual(len(MOVING_STARTS), 2)
        self.assertGreater(MOVING_STARTS[0][3], 0.0)
        crossing_x, start_y, direction, lower_y, upper_y = MOVING_STARTS[1]
        self.assertEqual(crossing_x, 0.78)
        self.assertEqual(start_y, -0.78)
        self.assertEqual(direction, 1)
        self.assertLess(lower_y, -0.45)
        self.assertGreater(upper_y, -0.45)

    def test_interactive_controller_reloads_and_never_quits_application(self) -> None:
        source = (
            PROJECT_ROOT
            / "controllers"
            / "interactive_supervisor"
            / "interactive_supervisor.py"
        ).read_text(encoding="utf-8")
        self.assertIn("worldReload()", source)
        self.assertNotIn("simulationQuit", source)

    def test_supervisor_moves_single_blue_object_in_legacy_world_shape(self) -> None:
        moving = FakeNode([-0.307713, 0.442052, 0.047])
        fake_supervisor = FakeSupervisor(
            {
                "EPUCK": FakeNode([-0.590567, -0.449332, 0.0]),
                "CP1": FakeNode([1.18, 0.0, 0.0]),
                "CP2": FakeNode([0.0, 0.45, 0.0]),
                "CP3": FakeNode([-1.18, 0.0, 0.0]),
                "MOVING_OBJECT": moving,
            }
        )
        controller_module = types.SimpleNamespace(
            Supervisor=lambda: fake_supervisor,
        )

        with mock.patch.dict(sys.modules, {"controller": controller_module}):
            with mock.patch.object(InteractiveSupervisor, "_log_event"):
                supervisor = InteractiveSupervisor()

        self.assertEqual(len(supervisor.moving), 1)
        self.assertEqual(supervisor.static_translations, [])
        self.assertFalse(supervisor.completion_enabled)
        self.assertEqual(moving.getField("translation").getSFVec3f(), [0.25, 0.48, 0.05])

        supervisor._move_obstacles()

        moved_position = moving.getField("translation").getSFVec3f()
        self.assertEqual(moved_position[0], 0.25)
        self.assertAlmostEqual(moved_position[1], 0.4752)
        self.assertEqual(moved_position[2], 0.05)

    def test_interactive_world_uses_interactive_supervisor(self) -> None:
        world = FINAL_INTERACTIVE_WORLD.read_text(encoding="utf-8")
        self.assertIn('controller "interactive_supervisor"', world)
        self.assertIn('controller "vision_proximity_controller"', world)

    def test_final_interactive12_world_uses_single_blue_mover_layout(self) -> None:
        world = FINAL_INTERACTIVE_WORLD.read_text(encoding="utf-8")
        self.assertEqual(world.count("SolidBox {"), 2)
        self.assertIn("DEF MOVING_OBJECT Solid", world)
        self.assertNotIn("DEF MOVING_OBJECT_2 Solid", world)
        self.assertNotIn("DEF FINISH_MARKER", world)

    def test_interactive_world_has_visual_car_skin_and_checkered_grid(self) -> None:
        world = EXTENDED_INTERACTIVE_WORLD.read_text(encoding="utf-8")
        self.assertIn("DEF CAR_SKIN Pose", world)
        self.assertIn("turretSlot [", world)
        self.assertEqual(world.count("size 0.02 0.05 0.008"), 18)
        self.assertIn("DEF CHECKER_WHITE", world)
        self.assertIn("DEF CHECKER_BLACK", world)
        car_block = world[
            world.index("DEF CAR_SKIN") : world.index("DEF STATIC_OBSTACLE")
        ]
        self.assertNotIn("boundingObject", car_block)

    def test_interactive_world_has_three_static_and_two_moving_obstacles(self) -> None:
        world = EXTENDED_INTERACTIVE_WORLD.read_text(encoding="utf-8")
        self.assertEqual(world.count("DEF STATIC_OBSTACLE"), 3)
        self.assertEqual(world.count("DEF MOVING_OBJECT"), 2)
        self.assertEqual(world.count("boundingObject USE STATIC_BOX"), 3)
        self.assertEqual(world.count("boundingObject USE MOVING_BOX"), 2)
        self.assertIn("translation 0.48 -0.45 0.04", world)
        self.assertIn("translation -0.65 0.45 0.04", world)
        self.assertIn("translation 0.25 0.48 0.05", world)
        self.assertIn("DEF MOVING_OBJECT_2 Solid", world)
        self.assertIn("translation 0.78 -0.78 0.05", world)

    def test_removed_upper_moving_object_is_not_supervised(self) -> None:
        source = (
            PROJECT_ROOT
            / "controllers"
            / "interactive_supervisor"
            / "interactive_supervisor.py"
        ).read_text(encoding="utf-8")
        self.assertIn('MOVING_NODE_NAMES = ("MOVING_OBJECT", "MOVING_OBJECT_2")', source)
        self.assertIn("if (node := self._optional_node(name)) is not None", source)
        self.assertNotIn('self._required_node("MOVING_OBJECT_3")', source)

    def test_interactive_world_preserves_user_selected_initial_view(self) -> None:
        world = EXTENDED_INTERACTIVE_WORLD.read_text(encoding="utf-8")
        self.assertIn("DEF TOP_VIEW Viewpoint", world)
        self.assertIn(
            "orientation 0.005854450603763857 0.9997072490744533 "
            "-0.02347640424164307 0.4884365123749093",
            world,
        )
        self.assertIn(
            "position -4.126994364919009 -0.13541521545641197 "
            "2.1667398773398214",
            world,
        )


if __name__ == "__main__":
    unittest.main()
