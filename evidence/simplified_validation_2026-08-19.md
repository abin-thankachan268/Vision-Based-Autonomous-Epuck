# Simplified Controller Validation — 2026-08-19

## Configuration under test

- Webots R2025a
- World: `worlds/simplified_navigation.wbt`
- Robot controller: `controllers/e_puck_controller/`
- Pedestrian-only Supervisor: `controllers/scene_supervisor/scene_supervisor.py`
- Inputs to the robot: camera and `ps0`–`ps7` only

The original interactive world and formal experiment assets were not replaced.
The saved initial viewpoint is regression-tested in both the existing and
simplified worlds.

## Automated validation

`python -m pytest -q` completed with **91 passed**. The suite covers fixed-HSV
lane direction/loss, one-strip and transverse-stripe rejection, stationary and
moving centroid classification, PD behavior, every simplified state, proximity
stop/escape, blue endpoint policy, pedestrian ping-pong motion, world obstacle
counts/collision geometry, controller separation, Supervisor isolation, visual
skin/checker presence, and viewpoint preservation.

Python compilation also completed without errors for the simplified robot
controller, pedestrian Supervisor, and world generator.

## Full-course Webots validation

The default simplified world reached `FINISHED` at **115.424 simulated
seconds**. Important transitions were:

- 5.312 s: `FOLLOW_LANE → STOP_WAIT` on the first red-object approach.
- 6.592 s: stationary classification entered `AVOID`.
- 12.832 s: the turn-straight-turn bypass completed and entered `REJOIN`.
- 16.480 s: camera confidence confirmed the lane and returned to `FOLLOW_LANE`.
- 115.424 s: the emissive checkered grid was recognized and motors stopped in `FINISHED`.

Before the finish approach, maximum front proximity was **224.748** and there
were **zero** samples at or above the emergency threshold of 700. The high
readings after 113 seconds coincide with the close checkered finish geometry;
the controller used its emergency reverse-turn and then stopped at the finish.

Evidence:

- `evidence/simplified_runtime_full_course.log`
- `evidence/simplified_telemetry_full_course.csv`
- `evidence/simplified_pedestrian_full_course.log`
- `evidence/simplified_frames_full_course/`

## Targeted moving-pedestrian validation

For this test only, the Supervisor's own environment overrides placed the blue
object on a bottom-road crossing at x = -0.20 m. No robot position or distance
was read by the Supervisor.

- 2.848 s: the robot entered `STOP_WAIT` and commanded `(0.0, 0.0)` motors.
- Blue observations contained 4 `UNKNOWN`, 27 `MOVING`, and 39 endpoint
  `STATIONARY` frames; all 70 remained in `STOP_WAIT`.
- 5.408 s: the crossing cleared and the robot entered `REJOIN`.
- 5.632 s: lane confirmation returned the robot to `FOLLOW_LANE`.
- The movement log records repeated direction reversals between y = -0.70 m and
  y = -0.20 m at the configured 0.15 m/s speed.

The acceptance window for this targeted test ended after the confirmed return
to `FOLLOW_LANE` at 5.632 s. Because Webots was running in fast mode, the same
process continued beyond the crossing and later entered an unrelated lane-loss
failsafe; that later event is retained in the raw files and is not presented as
a successful full-course moving scenario. Full-course completion is established
by the separate default-world run above.

Evidence:

- `evidence/simplified_runtime_moving_validation.log`
- `evidence/simplified_telemetry_moving_validation.csv`
- `evidence/simplified_pedestrian_moving_validation.log`
- `evidence/simplified_frames_moving_validation_final/`

## Interpretation and limitations

The live tests demonstrate the red stationary bypass, camera lane rejoin,
blue moving-object stop/wait release, proximity emergency escape, checkered
finish detection, and a completed course. The other spaced map objects remain
available for repeated runs, but whether each becomes an active interaction
depends on pedestrian timing and the recovered camera trajectory.

The strict simplified Supervisor does not inspect the robot, so this run has no
independent ground-truth collision-distance metric. Completion, perception,
motor commands, and proximity response are evidenced; a claim of zero physical
collisions is deliberately not made from this run. The frozen formal result set
and its evaluation-only metrics remain separate.
