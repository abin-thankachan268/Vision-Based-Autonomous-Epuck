"""Generate the deterministic Webots R2025a research worlds."""

from __future__ import annotations

import math
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "worlds" / "autonomous_epuck_experiment.wbt"
BASELINE_OUTPUT = PROJECT_ROOT / "worlds" / "ground_sensor_baseline.wbt"


def pose_box(
    x: float,
    y: float,
    z: float,
    length: float,
    width: float,
    height: float,
    angle: float,
    color: tuple[float, float, float],
) -> str:
    return f"""      Pose {{
        translation {x:.6f} {y:.6f} {z:.6f}
        rotation 0 0 1 {angle:.6f}
        children [
          Shape {{
            appearance PBRAppearance {{
              baseColor {color[0]:.6f} {color[1]:.6f} {color[2]:.6f}
              roughness 1
              metalness 0
            }}
            geometry Box {{
              size {length:.6f} {width:.6f} {height:.6f}
            }}
          }}
        ]
      }}"""


def track_geometry() -> str:
    road = (0.14, 0.15, 0.17)
    white = (0.95, 0.95, 0.95)
    parts: list[str] = []

    straight_length = 1.5
    road_width = 0.5
    radius = 0.45
    half_straight = 0.75
    road_z = 0.008
    road_h = 0.016

    for y in (-radius, radius):
        parts.append(pose_box(0, y, road_z, straight_length, road_width, road_h, 0, road))

    segments = 18
    road_segment_length = radius * math.pi / segments * 1.25
    for center_x, start_angle in ((half_straight, -math.pi / 2), (-half_straight, math.pi / 2)):
        for index in range(segments):
            theta = start_angle + (index + 0.5) * math.pi / segments
            x = center_x + radius * math.cos(theta)
            y = radius * math.sin(theta)
            tangent = theta + math.pi / 2
            parts.append(
                pose_box(x, y, road_z, road_segment_length, road_width, road_h, tangent, road)
            )

    # The physical road remains 0.50 m wide.  The vision lane is a narrower
    # 0.10 m corridor so the low-mounted e-puck camera can observe both marks.
    boundary_offset = 0.05
    line_width = 0.03
    line_z = 0.019
    line_h = 0.008
    for y in (-radius, radius):
        for offset in (-boundary_offset, boundary_offset):
            parts.append(
                pose_box(
                    0,
                    y + offset,
                    line_z,
                    straight_length,
                    line_width,
                    line_h,
                    0,
                    white,
                )
            )

    for center_x, start_angle in ((half_straight, -math.pi / 2), (-half_straight, math.pi / 2)):
        for boundary_radius in (radius - boundary_offset, radius + boundary_offset):
            line_segment_length = boundary_radius * math.pi / segments * 1.25
            for index in range(segments):
                theta = start_angle + (index + 0.5) * math.pi / segments
                x = center_x + boundary_radius * math.cos(theta)
                y = boundary_radius * math.sin(theta)
                tangent = theta + math.pi / 2
                parts.append(
                    pose_box(
                        x,
                        y,
                        line_z,
                        line_segment_length,
                        line_width,
                        line_h,
                        tangent,
                        white,
                    )
                )

    centre_line = (0.01, 0.01, 0.01)
    for y in (-radius, radius):
        parts.append(pose_box(0, y, 0.025, straight_length, 0.018, 0.006, 0, centre_line))
    for center_x, start_angle in ((half_straight, -math.pi / 2), (-half_straight, math.pi / 2)):
        line_segment_length = radius * math.pi / segments * 1.25
        for index in range(segments):
            theta = start_angle + (index + 0.5) * math.pi / segments
            x = center_x + radius * math.cos(theta)
            y = radius * math.sin(theta)
            tangent = theta + math.pi / 2
            parts.append(
                pose_box(
                    x,
                    y,
                    0.025,
                    line_segment_length,
                    0.018,
                    0.006,
                    tangent,
                    centre_line,
                )
            )
    return "\n".join(parts)


def build_world(controller_mode: str = "vision") -> str:
    geometry = track_geometry()
    baseline = controller_mode == "baseline"
    ground_sensor_proto = (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/'
        'projects/robots/gctronic/e-puck/protos/E-puckGroundSensors.proto"'
        if baseline
        else ""
    )
    controller_name = "baseline_ground" if baseline else "vision_controller"
    camera_configuration = "" if baseline else """  camera_fieldOfView 1.50
  camera_width 320
  camera_height 240
  camera_antiAliasing TRUE
  camera_rotation 0 1 0 0.47
"""
    ground_sensor_slot = (
        """  groundSensorsSlot [
    E-puckGroundSensors {
    }
    DistanceSensor {
      translation 0 0.02 0
      name "ir1"
    }
    DistanceSensor {
      translation 0 -0.01 0
      name "ir0"
      type "infra-red"
    }
  ]
"""
        if baseline
        else ""
    )
    return f"""#VRML_SIM R2025a utf8

EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/backgrounds/protos/TexturedBackground.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/floors/protos/RectangleArena.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/robots/gctronic/e-puck/protos/E-puck.proto"
{ground_sensor_proto}

WorldInfo {{
  basicTimeStep 32
  info [
    "Vision-based lane following and obstacle avoidance research world"
    "The vision controller receives camera frames only; Supervisor data is evaluation-only."
  ]
  title "Vision-Based Autonomous E-puck Navigation Research"
}}
Viewpoint {{
  orientation 0.333333 -0.244017 -0.910684 1.7225
  position 2.35 -2.55 2.25
}}
TexturedBackground {{
}}
DEF SUN DirectionalLight {{
  ambientIntensity 0.7
  intensity 1
  direction -0.4 -0.3 -1
}}
RectangleArena {{
  floorSize 3 2
  wallHeight 0.001
  wallAppearance PBRAppearance {{
    baseColor 0.08 0.12 0.07
    roughness 1
    metalness 0
  }}
  floorAppearance PBRAppearance {{
    baseColor 0.16 0.32 0.12
    roughness 1
    metalness 0
  }}
}}
DEF RESEARCH_TRACK Group {{
  children [
{geometry}
    DEF FINISH_MARKER Pose {{
      translation -0.60 -0.45 0.025
      children [
        Shape {{
          appearance PBRAppearance {{
            baseColor 0.05 0.80 0.12
            roughness 1
            metalness 0
          }}
          geometry Box {{
            size 0.045 0.06 0.012
          }}
        }}
      ]
    }}
  ]
}}
DEF START Transform {{
  translation -0.46 -0.45 0
}}
DEF CP1 Transform {{
  translation 1.18 0 0
}}
DEF CP2 Transform {{
  translation 0 0.45 0
}}
DEF CP3 Transform {{
  translation -1.18 0 0
}}
DEF EPUCK E-puck {{
  translation -0.46 -0.45 0
  rotation 0 0 1 0
  controller "{controller_name}"
  name "Autonomous e-puck"
{camera_configuration}{ground_sensor_slot}}}
DEF STATIC_OBSTACLE Solid {{
  translation 0.12 -0.45 0.04
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor 0.90 0.03 0.03
        roughness 0.8
        metalness 0
      }}
      geometry DEF STATIC_BOX Box {{
        size 0.08 0.08 0.08
      }}
    }}
  ]
  name "red stationary obstacle"
  boundingObject USE STATIC_BOX
  locked TRUE
}}
DEF STATIC_OBSTACLE_2 Solid {{
  translation 10 10 0.04
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor 0.90 0.03 0.03
        roughness 0.8
        metalness 0
      }}
      geometry DEF STATIC_BOX_2 Box {{
        size 0.08 0.08 0.08
      }}
    }}
  ]
  name "red stationary obstacle 2"
  boundingObject USE STATIC_BOX_2
  locked TRUE
}}
DEF STATIC_OBSTACLE_3 Solid {{
  translation 10 10 0.04
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor 0.90 0.03 0.03
        roughness 0.8
        metalness 0
      }}
      geometry DEF STATIC_BOX_3 Box {{
        size 0.08 0.08 0.08
      }}
    }}
  ]
  name "red stationary obstacle 3"
  boundingObject USE STATIC_BOX_3
  locked TRUE
}}
DEF MOVING_OBJECT Solid {{
  translation 0 0.78 0.05
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor 0.03 0.16 0.95
        roughness 0.8
        metalness 0
      }}
      geometry DEF MOVING_BOX Box {{
        size 0.08 0.08 0.10
      }}
    }}
  ]
  name "blue moving crossing object"
  boundingObject USE MOVING_BOX
  locked TRUE
}}
DEF MOVING_OBJECT_2 Solid {{
  translation 10 10 0.05
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor 0.03 0.16 0.95
        roughness 0.8
        metalness 0
      }}
      geometry DEF MOVING_BOX_2 Box {{
        size 0.08 0.08 0.10
      }}
    }}
  ]
  name "blue moving crossing object 2"
  boundingObject USE MOVING_BOX_2
  locked TRUE
}}
DEF EVALUATOR Robot {{
  supervisor TRUE
  controller "experiment_supervisor"
  name "Experiment evaluation supervisor"
}}
"""


def main() -> None:
    OUTPUT.write_text(build_world("vision"), encoding="utf-8", newline="\n")
    BASELINE_OUTPUT.write_text(build_world("baseline"), encoding="utf-8", newline="\n")
    print(OUTPUT)
    print(BASELINE_OUTPUT)


if __name__ == "__main__":
    main()
