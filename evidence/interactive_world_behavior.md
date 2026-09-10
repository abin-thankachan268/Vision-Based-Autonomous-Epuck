# Interactive Webots Behavior

The human-facing main world is `worlds/autonomous_epuck_interactive12.wbt`.

## Finalized interactive12 behavior

The e-puck in this world runs `vision_proximity_controller`. Camera perception
supplies lane position, obstacle class and controller state. The local
`ps0`-`ps7` devices add a short-range safety overlay to the camera command. No
Supervisor position or distance is sent to the robot, and ground sensors are not
used.

The finalized WBT contains two red stationary `SolidBox` obstacles and one blue
collidable `DEF MOVING_OBJECT` solid. The active `interactive_supervisor` moves
that blue object continuously by updating its `translation` field every
timestep. This world has CP1, CP2 and CP3 markers but no `FINISH_MARKER`, so
completed-pass reset is disabled and the world reloads only at the configured
interactive time limit.

The Supervisor supports this finalized single-mover layout without requiring
the optional nodes used by the retained extended demo, including
`STATIC_OBSTACLE_*`, `MOVING_OBJECT_2`, and `FINISH_MARKER`.

## Retained extended-world behavior

The earlier `worlds/autonomous_epuck_interactive.wbt` remains in the package as
an extended five-obstacle demonstration. Its behavior is:

- One blue moving obstacle travels continuously between y = 0.12 m and
  y = 0.78 m across the upper road. A second travels between y = -0.78 m and
  y = -0.12 m across the lower road near the original red obstacle. Both use
  0.15 m/s by default.
- Each moving obstacle reverses direction at the end of its travel, so it remains in
  motion instead of being removed after one crossing.
- The Supervisor records CP1, CP2 and CP3 in order before accepting the finish.
- One second after a completed pass, `worldReload()` restarts the world and all
  controllers.
- If a pass cannot finish within 180 seconds, the interactive world reloads for
  another attempt rather than closing Webots.
- The interactive controller contains no `simulationQuit` call.
- Runtime start, completion and reset events are appended to
  `evidence/interactive_runtime.log` for local verification. Completed-pass
  events include evaluation-only collision and minimum-clearance values.

The frozen experiment world remains `worlds/autonomous_epuck_experiment.wbt`. It intentionally
retains batch termination so `tools/run_scenarios.py` can launch the next trial.
Keeping these worlds separate preserves the existing formal configuration and
results while giving the desktop demonstration the requested continuous behavior.

## Camera-plus-proximity validation

The dated validation records in this section apply to the retained extended
`worlds/autonomous_epuck_interactive.wbt` world unless a different WBT file is
named explicitly.

On 2026-08-04, a default-threshold headless pass completed with zero recorded
collisions. Evaluation-only minimum centre distances were 0.082436 m to a
static obstacle and 0.078260 m to a moving obstacle. The retained controller
telemetry contains 2,191 samples, including 46 proximity-active samples, 25
normal avoidance commands and 21 emergency forward-turn commands. Webots was
still running after the completed pass and was stopped manually by the test.

A normal-reset test recorded two consecutive zero-collision passes
and two automatic world reloads. These are simulation results for this map and
do not establish safety for arbitrary obstacles or a physical robot.

The live controller console now explains all three stages of every sampled
decision: camera perception, the eight proximity readings, and the selected
camera/fusion/final motor command. The output is rate-limited to 0.5 simulated
seconds by default and also appears immediately on meaningful decision changes.
After adding these diagnostics and the overhead start view, a Webots validation
pass still completed with zero collisions and the process remained open.

## Recording-led contact correction

The supplied `supporting_materials/Interactive_Simulation_Recording.mp4` recording is 61.184 seconds
at 640 x 480 and 31.25 frames/s. Frame inspection confirmed that the red object
filled the camera before the robot made its final diversion at approximately
5.5-6.0 seconds. Baseline telemetry showed why: the original proximity override
reduced the camera avoidance wheel-speed difference from 2.2 to 1.6, weakening
the turn exactly when more clearance was needed.

The second blue-object contact had a different cause. The old controller ignored
side/rear sensors for activation even when `ps3` rose to 2367. The two blue
objects also crossed together from opposite directions, briefly placing the
robot between simultaneous front and rear hazards. The corrections are:

- a stronger, slower frontal proximity turn that never weakens the camera's
  static-obstacle S-curve;
- explicit side and rear hazard states and decision logging;
- aligned continuous ping-pong travel for both blue objects, so they cross and
  clear together without an opposing-motion sandwich;
- 24 camera-clear confirmation frames before the robot proceeds; and
- a conservative 0.090 m evaluation envelope instead of the former 0.078 m
  axis-aligned contact approximation.

Two consecutive normal-reset passes completed with `collisions=0`, minimum
static centre clearance 0.090483 m and minimum moving centre clearance
0.091130 m. Webots remained open, both moving objects continued looping, and
the saved viewpoint/world file was unchanged.

## Car appearance and racing grid

The retained extended interactive e-puck has a compact blue car-style shell
with a dark-glass cabin, roof, front/rear bumpers, headlights and taillights.
The shell is a `turretSlot` visual attachment with no `boundingObject`, so the
camera, proximity devices, wheel control and original e-puck collision
footprint are unchanged.

The former green block beside the initial robot position was replaced by three
rows and six columns of alternating black/white tiles. The same marker is the
loop's racing-style start/finish line. The interactive generator recreates both
visual features while preserving the user's saved viewpoint. A post-change
headless Webots pass completed with zero collisions (static 0.090483 m, moving
0.091140 m), confirming that the shell did not obstruct perception or control.

## Five-obstacle interactive layout

This section describes the retained extended
`worlds/autonomous_epuck_interactive.wbt` layout, not the finalized
`worlds/autonomous_epuck_interactive12.wbt` world.

The two formerly parked red nodes are active at (0.48, -0.45) m and
(-0.65, 0.45) m, supplementing the original red obstacle at
(0.12, -0.45) m. One blue node crosses the upper road at x = 0.25 m and a
second crosses the lower road at x = 0.78 m. The former closely spaced upper
duplicate was removed at the user's request and is no longer generated or
supervised.

The final arrangement completed two
consecutive automatically reset laps with zero recorded contacts. Both passes
reported the same minimum per-object centre distances: red objects
0.091047/0.092793/0.111392 m and blue objects 0.138708/0.114976 m. Webots
remained open after the second reset. The rendered layout is saved as
`evidence/interactive_five_obstacle_layout_final.png`.
