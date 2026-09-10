# Interactive Five-Obstacle Validation

Date: 2026-08-04

Scope: retained extended `worlds/autonomous_epuck_interactive.wbt` only. The
finalized primary interactive world is now
`worlds/autonomous_epuck_interactive12.wbt`; it uses the single-blue-mover
layout documented in the root README. The frozen formal world and formal result
set were not modified.

## Final layout

- Static red 1: (0.12, -0.45, 0.04) m.
- Static red 2: (0.48, -0.45, 0.04) m, near static red 1.
- Static red 3: (-0.65, 0.45, 0.04) m, after the upper moving-object area.
- Moving blue 1: x = 0.25 m, y range 0.12 to 0.78 m.
- Moving blue 2: x = 0.78 m, y range -0.78 to -0.12 m, near the two
  bottom-straight red obstacles.
- All five objects use 0.08 m box collision geometry. The moving objects travel
  at 0.15 m/s and reverse continuously at their range limits.

The former second upper-road blue node was removed from the WBT world, the
interactive Supervisor and the world generator. It cannot return on a normal
regeneration.

## Verification

- Automated tests: 68 passed.
- Generator round trip: retained three static and exactly two moving DEF nodes.
- Saved viewpoint SHA-256:
  `1186d83b917c5be490e9c7ffb0a88cae79a1de8322240073116bb4d7fdef8a65`.
- Two consecutive automatic-reset Webots laps completed.
- Recorded contacts: 0 on each lap.
- Webots remained open after both completed-pass reloads.

| Object | Minimum centre distance, lap 1 | Minimum centre distance, lap 2 |
|---|---:|---:|
| Static red 1 | 0.091047 m | 0.091047 m |
| Static red 2 | 0.092793 m | 0.092793 m |
| Static red 3 | 0.111392 m | 0.111392 m |
| Moving blue 1 | 0.138708 m | 0.138708 m |
| Moving blue 2 | 0.114976 m | 0.114976 m |

The project uses a conservative 0.090 m centre-distance near-contact envelope.
Every measured distance remained outside that envelope. The rendered Webots
inspection is `evidence/interactive_five_obstacle_layout_final.png`.

This verifies this deterministic arrangement only. It is not evidence that any
arbitrary obstacle count, phase, spacing or physical-robot layout is safe.
