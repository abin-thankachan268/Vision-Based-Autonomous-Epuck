# Vision-Based Autonomous E-puck Navigation Research Project

This local Webots R2025a project contains a camera/OpenCV navigation controller,
the camera-plus-proximity interactive controller, the preserved ground-sensor
baseline, Supervisor controllers, automated scenario execution, formal results,
and working research documents.

## Current status

- Final human-facing world: `worlds/autonomous_epuck_interactive12.wbt`.
- Active final robot controller: `controllers/vision_proximity_controller/`.
- Active final Supervisor: `controllers/interactive_supervisor/interactive_supervisor.py`.
- The finalized interactive world contains two red stationary `SolidBox`
  obstacles and one blue `DEF MOVING_OBJECT` solid.
- The Supervisor moves the blue solid continuously and sends no robot position,
  distance, emitter, receiver, or navigation data to the e-puck controller.
- Vision formal trials: 150/150 completed, with zero recorded collisions.
- Multi-obstacle formal trials: 30/30 completed across sequential-static,
  sequential-moving and mixed layouts, with zero recorded collisions.
- Ground-sensor baseline: 30/60 completed; all curve-dominant trials failed.
- Ethics approval, participant data collection, verified academic references and
  final dissertation submission: not complete.

The four-phase progress remains 50% because Phases 3 and 4 include approvals and
human-participant work that must not be fabricated or started before approval.
See `PROJECT_COMPLETION_PLAN.md` for the checked completion record.

## Run the offline validation

From this folder:

```powershell
python -m unittest discover -s tests -v
```

Expected result: 97 tests pass.

## Final interactive demonstration

Open **`worlds/autonomous_epuck_interactive12.wbt`** in Webots R2025a. This is
the finalized working world. The e-puck uses `vision_proximity_controller`,
which combines camera/OpenCV lane and object perception with the eight local
e-puck proximity sensors (`ps0`-`ps7`) for short-range collision safety.

The world uses the saved track, CP1/CP2/CP3 route markers, two red stationary
blocks, and one blue collidable moving solid. The active Supervisor is
`interactive_supervisor`. In this finalized single-mover layout it requires
only `EPUCK` and `MOVING_OBJECT` to start; optional nodes from the older
five-obstacle demo, such as `MOVING_OBJECT_2`, `STATIC_OBSTACLE_*`, and
`FINISH_MARKER`, are not required.

When the world starts, the Supervisor positions the blue solid at the configured
upper-road crossing and updates its `translation` every timestep using a
constant-speed ping-pong motion. The expected Webots console startup line is:

```text
Interactive demonstration mode: 1 moving obstacle(s) loop continuously; completion markers are unavailable, so the world reloads on the time limit.
```

Because `autonomous_epuck_interactive12.wbt` does not define `FINISH_MARKER`,
completed-pass reset is disabled for this file. The blue object continues to
move, and Webots remains open until the configured interactive time-limit reload.

## Retained worlds and evidence

`worlds/simplified_navigation.wbt` is retained as the earlier proposal-aligned
validation world. It uses `vision_proximity_controller` with the
pedestrian-only `scene_supervisor.py`, includes the checkered finish marker, and
is the source of the recorded 74.688-second corrective full-lap evidence in
`evidence/controller_recovery_validation_2026-08-21.md`.

`worlds/autonomous_epuck_interactive.wbt` is retained as the older extended
five-obstacle demonstration. It has three red static obstacles, two blue moving
objects, a visual car shell, a checkered racing grid, and completed-pass
`worldReload()` behavior. It is useful as an extended demo, but it is no longer
the primary finalized world.

`worlds/autonomous_epuck_experiment.wbt` is retained as the frozen automated
formal-experiment world. Its Supervisor exits Webots at the end of a batch run
so the scenario runner can continue. Do not use that batch world for the normal
interactive demonstration.

The baseline comparison world is `worlds/ground_sensor_baseline.wbt`, and
`worlds/legacy_ground_sensor_demo.wbt` is retained for original-project
provenance only.

## Scenario and result locations

- Scenario definitions: `scenarios/scenarios.json`
- Frozen configuration: `config/frozen_experiment_configuration.json`
- Primary finalized world: `worlds/autonomous_epuck_interactive12.wbt`
- Earlier proposal validation world: `worlds/simplified_navigation.wbt`
- Optional extended world: `worlds/autonomous_epuck_interactive.wbt`
- Active interactive controller: `controllers/vision_proximity_controller/`
- Active interactive Supervisor: `controllers/interactive_supervisor/interactive_supervisor.py`
- Retained pedestrian-only Supervisor: `controllers/scene_supervisor/scene_supervisor.py`
- Retained explainable reference controller: `controllers/e_puck_controller/`
- Formal summary: `results/formal/enriched_summary.csv`
- Per-run evaluator data: `results/formal/raw/`
- Camera-controller telemetry: `results/formal/telemetry/`
- Interactive fusion telemetry: `controllers/vision_proximity_controller/fusion_telemetry.csv`
- Results workbook: `results/Research_Results.xlsx`
- Verification evidence: `evidence/`
- Earlier full-lap proposal video: `evidence/Autonomous_Epuck_Proposal_World_Demonstration.mp4`

## Scope boundary

The controller supports the tested red/blue objects and configured layouts.
Arbitrary colours, shapes, dense occlusion, physical robots and safety-critical
deployment are outside the verified scope. Add new layouts to the scenario
matrix and test them before treating them as supported.

This project is retained locally. No Git commit or remote publication is needed
to reproduce the supplied formal result set.

## Submission package

Start with `SUBMISSION_GUIDE.md` for the package structure, prerequisites,
validation commands and the distinction between the completed technical work
and the participant/ethics work that remains pending. All paths in this package
are relative; no local-machine project path is required.
