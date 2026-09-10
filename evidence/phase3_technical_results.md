# Phase 3 Technical Results

**Execution date:** 2026-08-04  
**Formal configuration ID:** `82999888659be0c7`  
**Status:** Expanded technical experiment programme complete; ethics approval and participant evaluation pending.

## Formal trial coverage

- Vision controller: 15 scenarios x 10 repetitions = 150 trials.
- Ground-sensor baseline: 6 lane scenarios x 10 repetitions = 60 trials.
- Total formal trials: 210.
- The 15 vision scenarios comprise six lane, three stationary-obstacle, three
  moving-object, and three multi-obstacle scenarios.
- Pilot results are stored separately from formal results.
- The previous 180-run single-target dataset is retained in
  `results/formal_single_target_b2ecfa3a65604f8d` and excluded from the current summaries.

## Verified technical results

- Vision completion: 150/150 (100%).
- Ground-sensor baseline completion: 30/60 (50%).
- Baseline straight-route completion: 30/30.
- Baseline curve-dominant completion: 0/30.
- Vision collisions: 0 across all 150 runs.
- Overall vision mean lane error: 0.033434 m.
- Highest scenario mean lane error: 0.058470 m in `multi_static_sequential`.
- Expected obstacle detections: 90/90.
- False-positive detections in lane-only vision trials: 0.
- Minimum stationary-obstacle centre clearance: 0.080705 m.
- Minimum moving-object centre clearance: 0.127681 m.
- All formal result rows contain configuration ID `82999888659be0c7`.

All 30 multi-obstacle runs completed without a recorded collision:

- `multi_static_sequential`: 10/10 completed.
- `multi_moving_crossings`: 10/10 completed.
- `multi_mixed_obstacles`: 10/10 completed.

The planned overall completion, collision, overall mean lane-error,
obstacle-success and moving-object clearance criteria were met in the controlled
Webots simulation. The sequential-static scenario exceeded the 0.05 m
lane-error target when considered individually, so it remains a documented
stress-case limitation. Centre clearance is an evaluation metric, not surface
clearance, and these values do not establish physical or safety-critical readiness.

## Reproducibility and integrity evidence

- All 40 automated offline tests pass.
- All 29 project Python sources pass compilation checks.
- The formal matrix contains exactly 210 unique run IDs.
- Raw data, telemetry and logs are retained for each formal run.
- The vision entry point reads the camera and wheel motors only; it has no
  ground-sensor, receiver, Supervisor-distance or coordinate dependency.
- The Supervisor configures scenarios and records evaluation-only ground truth;
  it does not transmit navigation data to the robot.

## Result locations

- Formal summaries: `results/formal/run_summary.csv` and
  `results/formal/enriched_summary.csv`.
- Raw evaluation data: `results/formal/raw/`.
- Controller telemetry: `results/formal/telemetry/`.
- Run logs: `results/formal/logs/`.
- Frozen manifest: `config/frozen_experiment_configuration.json` (configuration `82999888659be0c7`).
- Workbook: `results/Research_Results.xlsx`.

## Ethics boundary

No participant data has been collected. The participant materials are local
drafts and must not be used for recruitment until the UREC2 route, researcher
and supervisor contacts, retention period, and required approvals/signatures
have been confirmed.
