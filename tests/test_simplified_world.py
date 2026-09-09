from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SimplifiedWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = (PROJECT_ROOT / "worlds" / "simplified_navigation.wbt").read_text(
            encoding="utf-8"
        )

    def test_world_uses_validated_fused_controller(self) -> None:
        self.assertIn('controller "vision_proximity_controller"', self.world)
        self.assertIn('controller "scene_supervisor"', self.world)
        self.assertNotIn('controller "experiment_supervisor"', self.world)

    def test_world_spaces_three_static_and_one_moving_obstacle(self) -> None:
        self.assertEqual(self.world.count("DEF STATIC_OBSTACLE"), 3)
        self.assertEqual(self.world.count("DEF MOVING_OBJECT"), 1)
        self.assertEqual(self.world.count("boundingObject USE STATIC_BOX"), 3)
        self.assertEqual(self.world.count("boundingObject USE MOVING_BOX"), 1)
        self.assertIn("translation 0.12 -0.45 0.04", self.world)
        self.assertIn("translation 0.83 0.45 0.04", self.world)
        self.assertIn("translation -0.65 0.45 0.04", self.world)
        self.assertIn("translation 0.25 0.48 0.05", self.world)

    def test_world_retains_visual_skin_checkered_grid_and_saved_view(self) -> None:
        self.assertIn("DEF CAR_SKIN Pose", self.world)
        self.assertEqual(self.world.count("size 0.02 0.05 0.008"), 18)
        self.assertIn("emissiveColor 0.8 0.8 0.8", self.world)
        self.assertIn(
            "orientation 0.02581514733456244 0.9983024599949671 "
            "-0.05220896988154142 0.9196497379597873",
            self.world,
        )
        self.assertIn(
            "position -2.8434065516690286 -0.03415818987371683 "
            "3.7161556402774734",
            self.world,
        )

    def test_supervisor_source_has_no_robot_navigation_channel(self) -> None:
        source = (
            PROJECT_ROOT / "controllers" / "scene_supervisor" / "scene_supervisor.py"
        ).read_text(encoding="utf-8")
        self.assertIn('getFromDef("MOVING_OBJECT")', source)
        for forbidden in (
            "getEmitter",
            "getReceiver",
            "getDevice",
            'getFromDef("EPUCK")',
            "getPosition",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("worldReload", source)
        self.assertNotIn("simulationQuit", source)
        self.assertIn("SIMPLIFIED_PEDESTRIAN_X", source)
        self.assertIn("simplified_pedestrian.log", source)

    def test_explainable_simplified_controller_is_retained_as_reference(self) -> None:
        controller = PROJECT_ROOT / "controllers" / "e_puck_controller"
        for name in ("e_puck_controller.py", "vision.py", "control.py"):
            self.assertTrue((controller / name).is_file())
        entrypoint = (controller / "e_puck_controller.py").read_text(encoding="utf-8")
        self.assertNotIn("vision_controller", entrypoint)
        self.assertNotIn("ground sensor", entrypoint.lower())
        self.assertIn("SIMPLIFIED_CAPTURE_INTERVAL", entrypoint)


if __name__ == "__main__":
    unittest.main()
