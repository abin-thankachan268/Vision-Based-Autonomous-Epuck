"""Generate the retained extended looping world without changing formal files.

The primary finalized interactive world is
worlds/autonomous_epuck_interactive12.wbt. This generator still maintains the
older five-obstacle/two-mover demonstration at
worlds/autonomous_epuck_interactive.wbt.
"""

from __future__ import annotations

import re
from pathlib import Path

from generate_research_world import build_world


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "worlds" / "autonomous_epuck_interactive.wbt"
VIEWPOINT_PATTERN = re.compile(
    r"(?:DEF\s+\w+\s+)?Viewpoint\s*\{[^}]*\}",
    re.MULTILINE,
)

GREEN_FINISH_MARKER = """    DEF FINISH_MARKER Pose {
      translation -0.60 -0.45 0.025
      children [
        Shape {
          appearance PBRAppearance {
            baseColor 0.05 0.80 0.12
            roughness 1
            metalness 0
          }
          geometry Box {
            size 0.045 0.06 0.012
          }
        }
      ]
    }"""

CHECKERED_FINISH_MARKER = """    DEF FINISH_MARKER Pose {
      translation -0.60 -0.45 0.025
      children [
        Pose { translation -0.02 -0.125 0.004 children [ Shape { appearance DEF CHECKER_WHITE PBRAppearance { baseColor 0.98 0.98 0.98 roughness 0.8 metalness 0 } geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation -0.02 -0.075 0.004 children [ Shape { appearance DEF CHECKER_BLACK PBRAppearance { baseColor 0.01 0.01 0.01 roughness 0.9 metalness 0 } geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation -0.02 -0.025 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation -0.02 0.025 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation -0.02 0.075 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation -0.02 0.125 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0 -0.125 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0 -0.075 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0 -0.025 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0 0.025 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0 0.075 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0 0.125 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0.02 -0.125 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0.02 -0.075 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0.02 -0.025 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0.02 0.025 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0.02 0.075 0.004 children [ Shape { appearance USE CHECKER_WHITE geometry Box { size 0.02 0.05 0.008 } } ] }
        Pose { translation 0.02 0.125 0.004 children [ Shape { appearance USE CHECKER_BLACK geometry Box { size 0.02 0.05 0.008 } } ] }
      ]
    }"""

CAR_SKIN_SLOT = """  turretSlot [
    DEF CAR_SKIN Pose {
      translation 0 0 0.012
      children [
        Pose {
          translation 0 0 0.010
          children [
            Shape {
              appearance DEF CAR_PAINT PBRAppearance { baseColor 0.06 0.28 0.85 roughness 0.22 metalness 0.35 }
              geometry Box { size 0.095 0.068 0.020 }
            }
          ]
        }
        Pose {
          translation 0.027 0 0.024
          children [ Shape { appearance USE CAR_PAINT geometry Box { size 0.038 0.064 0.010 } } ]
        }
        Pose {
          translation -0.012 0 0.030
          children [
            Shape {
              appearance DEF CAR_GLASS PBRAppearance { baseColor 0.025 0.055 0.085 roughness 0.12 metalness 0.15 }
              geometry Box { size 0.042 0.054 0.022 }
            }
          ]
        }
        Pose {
          translation -0.012 0 0.043
          children [ Shape { appearance USE CAR_PAINT geometry Box { size 0.030 0.057 0.005 } } ]
        }
        Pose { translation 0.048 0 0.010 children [ Shape { appearance PBRAppearance { baseColor 0.04 0.04 0.05 roughness 0.65 metalness 0 } geometry Box { size 0.004 0.071 0.012 } } ] }
        Pose { translation -0.048 0 0.010 children [ Shape { appearance PBRAppearance { baseColor 0.04 0.04 0.05 roughness 0.65 metalness 0 } geometry Box { size 0.004 0.071 0.012 } } ] }
        Pose { translation 0.050 -0.021 0.018 children [ Shape { appearance DEF HEADLIGHT PBRAppearance { baseColor 1 0.86 0.25 emissiveColor 0.35 0.25 0.03 roughness 0.35 metalness 0 } geometry Box { size 0.004 0.012 0.008 } } ] }
        Pose { translation 0.050 0.021 0.018 children [ Shape { appearance USE HEADLIGHT geometry Box { size 0.004 0.012 0.008 } } ] }
        Pose { translation -0.050 -0.021 0.018 children [ Shape { appearance DEF TAILLIGHT PBRAppearance { baseColor 0.85 0.02 0.015 emissiveColor 0.22 0 0 roughness 0.4 metalness 0 } geometry Box { size 0.004 0.012 0.008 } } ] }
        Pose { translation -0.050 0.021 0.018 children [ Shape { appearance USE TAILLIGHT geometry Box { size 0.004 0.012 0.008 } } ] }
      ]
    }
  ]
"""

MOVING_OBJECT_2 = """DEF MOVING_OBJECT_2 Solid {
  translation 0.78 -0.78 0.05
  children [
    Shape {
      appearance PBRAppearance {
        baseColor 0.03 0.16 0.95
        roughness 0.8
        metalness 0
      }
      geometry DEF MOVING_BOX_2 Box {
        size 0.08 0.08 0.1
      }
    }
  ]
  name "blue moving crossing object 2"
  boundingObject USE MOVING_BOX_2
  locked TRUE
}
"""


def replace_initial_viewpoint(world: str, viewpoint: str) -> str:
    """Replace only the generated viewpoint while retaining the user's POV."""

    return VIEWPOINT_PATTERN.sub(lambda match: viewpoint, world, count=1)


def add_interactive_visuals(world: str) -> str:
    """Add a visual-only car shell and racing start/finish grid."""

    if GREEN_FINISH_MARKER not in world:
        raise ValueError("generated green finish marker was not found")
    world = world.replace(
        GREEN_FINISH_MARKER,
        CHECKERED_FINISH_MARKER,
        1,
    )
    camera_tail = "  camera_rotation 0 1 0 0.47\n}"
    if camera_tail not in world:
        raise ValueError("generated interactive e-puck camera block was not found")
    return world.replace(
        camera_tail,
        f"  camera_rotation 0 1 0 0.47\n{CAR_SKIN_SLOT}}}",
        1,
    )


def add_interactive_obstacles(world: str) -> str:
    """Activate two spare red obstacles and add the lower-road crossing."""

    placements = {
        "DEF STATIC_OBSTACLE_2 Solid {\n  translation 10 10 0.04":
            "DEF STATIC_OBSTACLE_2 Solid {\n  translation 0.48 -0.45 0.04",
        "DEF STATIC_OBSTACLE_3 Solid {\n  translation 10 10 0.04":
            "DEF STATIC_OBSTACLE_3 Solid {\n  translation -0.65 0.45 0.04",
        "DEF MOVING_OBJECT Solid {\n  translation 0 0.78 0.05":
            "DEF MOVING_OBJECT Solid {\n  translation 0.25 0.48 0.05",
    }
    for hidden, visible in placements.items():
        if hidden not in world:
            raise ValueError(f"generated spare obstacle was not found: {hidden}")
        world = world.replace(hidden, visible, 1)
    spare_moving = re.compile(
        r"DEF MOVING_OBJECT_2 Solid \{.*?\n\}\n(?=DEF EVALUATOR Robot \{)",
        re.DOTALL,
    )
    world, removed = spare_moving.subn("", world, count=1)
    if removed != 1:
        raise ValueError("generated second upper-road moving object was not found")
    evaluator = "DEF EVALUATOR Robot {"
    if evaluator not in world:
        raise ValueError("generated evaluator was not found")
    return world.replace(evaluator, f"{MOVING_OBJECT_2}{evaluator}", 1)


def main() -> None:
    saved_viewpoint = None
    if OUTPUT.exists():
        match = VIEWPOINT_PATTERN.search(OUTPUT.read_text(encoding="utf-8"))
        if match:
            saved_viewpoint = match.group(0)
    world = build_world("vision")
    default_top_view = """DEF TOP_VIEW Viewpoint {
  orientation 0 0 1 0
  position 0 0 3.3
}"""
    world = replace_initial_viewpoint(
        world,
        saved_viewpoint or default_top_view,
    )
    world = add_interactive_visuals(world)
    world = add_interactive_obstacles(world)
    world = world.replace(
        'controller "vision_controller"',
        'controller "vision_proximity_controller"',
        1,
    ).replace(
        'controller "experiment_supervisor"',
        'controller "interactive_supervisor"',
        1,
    ).replace(
        'name "Experiment evaluation supervisor"',
        'name "Interactive demonstration supervisor"',
        1,
    )
    OUTPUT.write_text(world, encoding="utf-8", newline="\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
