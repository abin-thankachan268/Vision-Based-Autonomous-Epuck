# Final Technical Validation - 2026-08-04

Note: this dated validation record describes the formal result set and the
retained `worlds/autonomous_epuck_interactive.wbt` demo as they stood on
2026-08-04. As of 2026-09-03, the primary finalized interactive world is
`worlds/autonomous_epuck_interactive12.wbt`; see `README.md` and
`SUBMISSION_GUIDE.md` for the current entry point.

## Configuration and result integrity

- Frozen configuration ID: `82999888659be0c7`.
- The aggregate SHA-256 value recomputed from every manifest input and matched
  the frozen configuration ID.
- Formal summary rows: 210.
- Unique formal run IDs: 210.
- Configuration IDs present in the formal summary: one
  (`82999888659be0c7`).
- The formal dry run found all 150 expected vision runs already present and no
  missing vision run to execute.

## Automated validation

- Unit/integration tests: 68 passed, 0 failed.
- Python compilation audit: 40 files passed.
- Vision entry point devices: camera and wheel motors only.
- World communication devices: no `Emitter` or `Receiver` node.
- Research world obstacle nodes: three static and two moving, all generated with
  collision geometry.

## Interactive Webots outcome

- Human-facing world: `worlds/autonomous_epuck_interactive.wbt`.
- Both interactive blue obstacles loop continuously at constant configured
  speed; one crosses the upper road and one crosses the lower road.
- The controller uses `worldReload()` after a completed pass and contains no
  `simulationQuit` call.
- A default-duration headless run recorded four consecutive `pass_completed`
  and `completed_pass_reset` events.
- The Webots process remained alive after 30 seconds and was stopped manually by
  the validation command.
- The frozen experiment world was regenerated after Webots had saved a previous
  end-state; all 17 frozen input hashes now match configuration
  `82999888659be0c7` again.
- The interactive e-puck uses the camera-plus-proximity controller with local
  `ps0`-`ps7` collision avoidance; the frozen formal controller remains unchanged.
- The tuned default thresholds (activation 120, clear 90, emergency 300)
  completed with zero collisions (minimum static/moving centre distances:
  0.082436 m / 0.078260 m). Retained telemetry recorded 46 proximity-active
  samples, and Webots remained alive after completion.
- A separate normal-reset run completed twice consecutively with zero collisions
  and automatically reloaded after each pass.
- The interactive world preserves the user's saved initial map view, and the
  controller prints rate-limited `PERCEPTION`, `PROXIMITY` and `DECISION`
  explanations. A post-change live pass completed with zero collisions while
  Webots remained open.
- Recording-led correction added stronger frontal clearance, side/rear hazard
  handling, aligned constant-motion crossings and 24 clear confirmation frames.
  Two consecutive normal-reset passes recorded zero contacts inside a
  conservative 0.090 m envelope (static 0.090483 m; moving 0.091130 m).
- The interactive e-puck now carries a visual-only car shell, and an 18-tile
  black-and-white racing grid replaces the green start/finish block. A live
  zero-collision pass confirmed that the turret attachment did not block the
  camera or proximity system. The user's saved viewpoint was not changed.
- The interactive layout now uses all three red static obstacles and two blue
  moving obstacles. A rendered Webots inspection confirmed the intended
  placement and collision geometry. Two consecutive automatic-reset laps
  completed with zero contacts; per-object minimum centre distances were
  0.091047/0.092793/0.111392 m for the red objects and
  0.138708/0.114976 m for the blue objects. The formal research world
  and its frozen three-static/two-moving result set were not changed.

## Formal Webots outcome

- Vision completion: 150/150 (100%).
- Vision collisions: 0.
- Multi-obstacle completion: 30/30 (100%).
- Multi-obstacle collisions: 0.
- Overall vision mean lane error: 0.033434 m.
- Minimum stationary centre clearance: 0.080705 m.
- Minimum moving centre clearance: 0.127681 m.
- Expected obstacle detections: 90/90.
- Lane-only false-positive detections: 0.
- Baseline completion: 30/60 (50%).

The sequential-static multi-obstacle scenario averaged 0.058470 m lane error,
which exceeds the 0.05 m target when the scenario is considered individually.
It still completed 10/10 runs with no recorded collision. This is retained as a
stress-case limitation rather than reported as a pass on every per-scenario
quality measure.

## Artifact QA

- The results workbook was rebuilt from `results/formal/enriched_summary.csv`.
- Workbook formula-error scan: no matches for `#REF!`, `#DIV/0!`, `#VALUE!`,
  `#NAME?` or `#N/A`.
- Dashboard, scenario summary, baseline comparison, protocol and raw-data sample
  were rendered and visually inspected.
- The dissertation working draft was rebuilt and all 10 rendered pages were
  visually inspected.
- The participant evaluation draft was rebuilt and all 5 rendered pages were
  visually inspected.
- The canonical LibreOffice document renderer was unavailable; Microsoft Word's
  fixed-format exporter and Poppler rasterization were used for visual QA.

## Research boundary

The technical implementation and formal simulation programme are complete for
the defined scope. Phase 3 remains incomplete until UREC2 materials, contacts,
signatures and approval are finalized. Phase 4 remains incomplete until approved
participant work, verified references, supervisor feedback and final dissertation
work are completed. No participant data has been collected.
