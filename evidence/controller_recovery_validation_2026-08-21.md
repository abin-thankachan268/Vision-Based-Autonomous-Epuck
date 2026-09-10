# Controller Recovery and Visual Validation — 2026-08-21

## Reason for the correction

A fixed 30-second Webots recording reproduced the reported failure in
`simplified_navigation.wbt`. The proposal-specific `e_puck_controller` passed
offline tests but its open-loop stationary bypass drove for four seconds without
lane evidence. After leaving the road, thin bright horizon strips were accepted
as lane boundaries. The robot therefore continued on grass instead of returning
to the circuit.

## Implemented recovery

- Retained the simplified controller and its tests as an explainable reference.
- Selected the previously stable `vision_proximity_controller` in the main
  proposal-aligned world.
- Increased camera-controller stationary avoidance steering from 1.1 to 1.5.
- Reduced front, side and rear proximity activation from 120 to 105, with an
  85 clear threshold and the existing 300 emergency threshold.
- Retained the camera's stop for non-emergency frontal proximity instead of
  reversing or advancing into a crossing. Dedicated side/rear latches remain
  responsible for confirmed flank and rear threats.
- Kept the Supervisor evaluation/scenario-only: it moves the blue object but
  sends no position, distance or navigation input to the robot.

## Automated verification

Command:

```powershell
python -m pytest -q -p no:cacheprovider
```

Result: **95 passed**.

The added regression coverage rejects thin horizon strips as lane boundaries,
bounds PD steering so a recovery command cannot reverse one wheel, preserves
the new rejoin proximity grace period, and verifies retained frontal stopping.

## Webots full-lap result

The active controller was run in Webots R2025a against the unchanged
`simplified_navigation.wbt` geometry and continuously moving blue object. A
temporary evaluation-only Supervisor observed the run; none of its measurements
were sent to the robot controller.

- Completed: **yes**
- Completion time: **74.688 simulated seconds**
- Checkpoints: **3 of 3**
- Contact events at or below the conservative 0.090 m envelope: **0**
- Minimum static-obstacle centre distance: **0.095606 m**
- Minimum moving-object centre distance: **0.112544 m**
- Final result: `completed=1`, `contacts=0`, `events=none`

Top-view frames at 10, 20, 30, 40, 50, 60 and 70 seconds were visually
inspected. The robot used the paved shoulders during avoidance where needed,
rejoined the marked lane, negotiated both curves, waited/escaped safely at the
moving crossing and returned through the finish area without entering the grass.

## Submission video

`Autonomous_Epuck_Proposal_World_Demonstration.mp4` records the complete
verified proposal-world run from start through the finish, followed by a
two-second finish hold. The Webots main view uses the saved top viewpoint and
includes the live robot-camera inset.

- Codec: H.264
- Resolution: 1280 × 720
- Duration: 76.672 seconds
- Recorded completion time: 74.688 simulated seconds
- Recorded checkpoints: 3 of 3
- Recorded contact events: 0

`submission_video_contact_sheet.jpg`, `submission_video_final.jpg` and
`submission_video_result.txt` provide quick visual and machine-readable checks
of the recording.

## Scope

This is deterministic simulation evidence for the supplied world and obstacle
layout. It is not evidence of physical-robot or public-road safety.
