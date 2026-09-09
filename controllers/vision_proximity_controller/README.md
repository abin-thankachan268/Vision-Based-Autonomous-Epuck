# Camera and Proximity Controller

This controller extends the existing camera/OpenCV navigation system with the
e-puck's eight local infrared proximity sensors. It is used by
`worlds/autonomous_epuck_interactive12.wbt`, the finalized interactive world.
The frozen formal experiment continues to use the camera-only controller so the
existing research results remain reproducible.

## Responsibility split

- The camera pipeline detects lane boundaries, red/blue objects and the finish.
- The camera state machine selects `FOLLOW_LANE`, `STOP_WAIT`, `AVOID`,
  `REJOIN`, `FINISHED` or `FAILSAFE` and generates the base wheel command.
- `ProximitySafetyLayer` reads `ps0` through `ps7` and modifies that command only
  when a nearby object creates a short-range collision risk.
- `ps0`, `ps1`, `ps6` and `ps7` trigger frontal avoidance; the side sensors
  contribute to left/right turn selection; `ps3` and `ps4` guard reverse escape.
- `ps2` and `ps5` detect flank hazards, while `ps3` and `ps4` can trigger a
  forward escape when a moving object approaches from behind.
- `FINISHED` and `FAILSAFE` stops are never overridden.

Default thresholds are 105 for front/side/rear activation, 85 for clearing and
300 for an emergency response. Three clear frames are required to release
avoidance. They can be overridden for controlled tuning with
`AUTONOMOUS_EPUCK_PS_ACTIVATION`, `AUTONOMOUS_EPUCK_PS_SIDE_ACTIVATION`,
`AUTONOMOUS_EPUCK_PS_REAR_ACTIVATION`, `AUTONOMOUS_EPUCK_PS_CLEAR` and
`AUTONOMOUS_EPUCK_PS_EMERGENCY`.

When the camera is already stopped for a crossing object, a non-emergency
front-sensor trigger retains that stop. Dedicated side and rear sensor latches
still move the robot forward when a true flank/rear threat is measured.
Emergency readings retain the bounded reverse-turn response.

Fusion telemetry is written locally to `fusion_telemetry.csv`. It contains the
eight raw readings, front peak, activation flag, chosen turn direction, camera
state, final wheel speeds and decision reason.

## Webots console explanation

The controller also prints a live, rate-limited explanation every 0.5 simulated
seconds and immediately when an important state or sensor-fusion decision
changes:

- `PERCEPTION` reports lane visibility, centre, error, confidence, boundaries,
  each tracked object's colour/motion/centroid/threat, blocked-path status and
  finish visibility.
- `PROXIMITY` reports the raw `ps0`-`ps7` values, front peak, activation state
  and selected turn-away direction.
- `DECISION` reports the camera state and reason, camera motor request, whether
  proximity overrode it, final motor speeds and the fusion reason.

Set `AUTONOMOUS_EPUCK_CONSOLE_LOG_INTERVAL` to another number of simulated seconds if a
faster or slower periodic display is needed. Decision changes are still printed
immediately.

The interactive controller requires 24 visually clear frames before leaving an
obstacle wait/avoidance decision. This gives continuously moving objects extra
time to leave the robot's side and rear clearance envelope. It can be increased
for controlled tests with `AUTONOMOUS_EPUCK_CLEAR_OBSTACLE_FRAMES`; values below 24 are not
accepted by the default helper.

The controller has no Supervisor receiver, robot-position input or obstacle
ground truth. It does not read the three downward ground sensors.

The finalized interactive12 demonstration contains two red stationary `SolidBox`
obstacles and one blue collidable `DEF MOVING_OBJECT` solid. The companion
`interactive_supervisor` moves that blue object continuously and now supports
this single-mover world shape without requiring optional five-obstacle demo
nodes such as `MOVING_OBJECT_2` or `FINISH_MARKER`.

The older `worlds/autonomous_epuck_interactive.wbt` five-obstacle arrangement
is retained as an extended demonstration with three static and two moving
obstacles. It does not imply support for arbitrary dense or differently
coloured layouts.

## Interactive appearance

`worlds/autonomous_epuck_interactive12.wbt` uses the saved e-puck/world
appearance from that finalized WBT file. The retained extended world still
mounts a visual car shell in the e-puck `turretSlot`; that shell has no
collision geometry and therefore does not alter controller or sensor behavior.
The fused controller includes an interactive checker-pattern detector for worlds
that use the racing grid, while the frozen formal camera controller and its
green-marker result set remain unchanged.
