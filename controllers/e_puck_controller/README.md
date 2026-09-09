# Simplified e-puck Controller Architecture

This controller is the proposal-aligned demonstration path for Webots R2025a.
It is deliberately separate from the frozen formal controller and preserved
ground-sensor baseline.

## Principal files

- `e_puck_controller.py` connects Webots devices, prints live explanations, and writes telemetry.
- `vision.py` performs fixed-HSV lane/object perception and single-target centroid tracking.
- `control.py` contains PD steering, proximity fusion, and the six-state navigation policy.
- `../scene_supervisor/scene_supervisor.py` moves one blue pedestrian and does not provide robot navigation data.

## Perception

The camera buffer is converted from Webots BGRA to OpenCV BGR. A fixed HSV mask
finds the controlled-world white boundaries. Morphology removes small noise,
connected components keep left and right boundary observations separate, and
coverage/transverse-stripe checks reject a single white strip as a false lane.
The output is lane centre, normalized lateral error, and confidence.

Red and blue contours are ranked by lane relevance, vertical proximity, and
area. Only the highest-relevance object is tracked. Multi-frame centroid
displacement produces `UNKNOWN`, `MOVING`, or `STATIONARY`. In the controlled
world, blue is always treated as the pedestrian safety class, even when it
briefly has zero image displacement at a crossing endpoint.

## Control

`FOLLOW_LANE` uses proportional-derivative steering; it has no integral term.
A red stationary object enters a turn-straight-turn `AVOID` manoeuvre. A finite
turn-straight-counter-turn recovery crosses back toward the lane, and camera
confidence must confirm two usable boundaries before returning to
`FOLLOW_LANE`. A blue object remains in `STOP_WAIT` until it clears.

The eight proximity sensors are a local safety input. A close unseen object
first causes a stop, then a turn-away escape. Extreme front proximity uses a
bounded reverse-turn when the rear is clear. Proximity never supplies global
position or route data.

## Outputs and configuration

The Webots console reports `[VISION]`, `[PROXIMITY]`, and `[DECISION]` records.
CSV telemetry is written beside the controller. Runtime state changes and
finish events are written to `evidence/simplified_runtime.log`. Set
`SIMPLIFIED_CAPTURE_INTERVAL` to a positive number of seconds to save camera
frames for validation; it defaults to disabled.

All thresholds, PD gains, manoeuvre timings, speeds, proximity limits, and the
pedestrian crossing path have `SIMPLIFIED_*` environment overrides in the two
Webots entry points. Defaults are the validated demonstration configuration.

## Scope

The implementation is validated in the supplied controlled Webots world with
white boundaries, red static blocks, and a blue pedestrian. It is not evidence
of safe physical-robot deployment, arbitrary-colour detection, dense traffic,
or occlusion robustness.
