"""Generate the proposal-aligned Webots world used for the primary demonstration."""

from __future__ import annotations

import re
from pathlib import Path

from generate_interactive_world import (
    VIEWPOINT_PATTERN,
    add_interactive_visuals,
    replace_initial_viewpoint,
)
from generate_research_world import build_world


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "worlds" / "simplified_navigation.wbt"
PREVIOUS_VIEW = PROJECT_ROOT / "worlds" / "autonomous_epuck_interactive.wbt"


def _saved_viewpoint() -> str:
    for path in (OUTPUT, PREVIOUS_VIEW):
        if path.exists():
            match = VIEWPOINT_PATTERN.search(path.read_text(encoding="utf-8"))
            if match:
                return match.group(0)
    return """DEF TOP_VIEW Viewpoint {
  orientation 0 0 1 0
  position 0 0 3.3
}"""


def simplify_world(world: str) -> str:
    """Space three static objects and retain one moving pedestrian."""

    replacements = {
        "DEF STATIC_OBSTACLE_2 Solid {\n  translation 10 10 0.04":
            "DEF STATIC_OBSTACLE_2 Solid {\n  translation 0.83 0.45 0.04",
        "DEF STATIC_OBSTACLE_3 Solid {\n  translation 10 10 0.04":
            "DEF STATIC_OBSTACLE_3 Solid {\n  translation -0.65 0.45 0.04",
        "DEF MOVING_OBJECT Solid {\n  translation 0 0.78 0.05":
            "DEF MOVING_OBJECT Solid {\n  translation 0.25 0.48 0.05",
        'controller "vision_controller"': 'controller "e_puck_controller"',
        'controller "experiment_supervisor"': 'controller "scene_supervisor"',
        'name "Autonomous e-puck"': 'name "Simplified autonomous e-puck"',
        'name "Experiment evaluation supervisor"': 'name "Pedestrian movement supervisor"',
        'title "Vision-Based Autonomous E-puck Navigation Research"':
            'title "Simplified Vision-Based Autonomous e-puck Navigation"',
    }
    for old, new in replacements.items():
        if old not in world:
            raise ValueError(f"Expected generated world fragment was not found: {old}")
        world = world.replace(old, new, 1)
    spare = re.compile(
        r"DEF MOVING_OBJECT_2 Solid \{.*?\n\}\n(?=DEF EVALUATOR Robot \{)",
        re.DOTALL,
    )
    world, removed = spare.subn("", world, count=1)
    if removed != 1:
        raise ValueError("Spare moving-object node was not found")
    world = world.replace(
        '"Vision-based lane following and obstacle avoidance research world"',
        '"Simplified fixed-HSV, PD and proximity navigation world"',
        1,
    ).replace(
        '"The vision controller receives camera frames only; Supervisor data is evaluation-only."',
        '"The robot receives camera and proximity data only; the Supervisor moves one pedestrian."',
        1,
    )
    checker_white = "baseColor 0.98 0.98 0.98 roughness 0.8"
    checker_emissive = (
        "baseColor 0.98 0.98 0.98 emissiveColor 0.8 0.8 0.8 roughness 0.8"
    )
    if checker_white not in world:
        raise ValueError("Checkered marker white appearance was not found")
    world = world.replace(checker_white, checker_emissive, 1)
    return world


def main() -> None:
    world = build_world("vision")
    world = replace_initial_viewpoint(world, _saved_viewpoint())
    world = add_interactive_visuals(world)
    world = simplify_world(world)
    OUTPUT.write_text(world, encoding="utf-8", newline="\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
