# Submission Package Validation

Validation date: 2026-09-03

## Technical verification

- Primary world: `worlds/autonomous_epuck_interactive12.wbt`.
- Webots version: R2025a.
- Automated tests: 97 passed.
- Finalized interactive layout: two red stationary `SolidBox` obstacles and one
  blue collidable `DEF MOVING_OBJECT` solid.
- Active finalized-world controller: `vision_proximity_controller`.
- Active finalized-world Supervisor: `interactive_supervisor`.
- Supervisor compatibility: the finalized world has no `FINISH_MARKER`,
  `STATIC_OBSTACLE_*` DEF nodes, or `MOVING_OBJECT_2`, and the Supervisor still
  starts and moves the single blue object.
- Recorded corrective proposal-world validation remains available for
  `worlds/simplified_navigation.wbt`: one completed full lap through all three
  checkpoints in 74.688 simulated seconds.
- Recorded conservative contact events for that retained validation run: zero.
- User-selected `autonomous_epuck_interactive12.wbt` state: finalized by the
  project owner and reported working as expected.
- Camera-plus-proximity console logging and CSV telemetry: enabled.
- Optional two-mover/reset world is retained as
  `worlds/autonomous_epuck_interactive.wbt`, but it is no longer the primary
  finalized world.
- Active controller: validated camera/OpenCV navigation with eight-sensor
  proximity fusion; the reduced PD controller remains included as an
  explainable reference.
- Corrective full-course validation: completed all three checkpoints in 74.688
  simulated seconds with zero events at the conservative 0.090 m contact
  envelope.
- Corrective minimum centre distances: 0.095606 m to static obstacles and
  0.112544 m to the moving object.
- Targeted pedestrian validation: 70/70 blue-object observations held zero
  motor commands in `STOP_WAIT`, followed by `REJOIN` and `FOLLOW_LANE`.
- Proposal Supervisor isolation: no robot-position, emitter, receiver,
  navigation, world-reload, or simulation-close API is used.
- Corrective evidence: full-lap telemetry, result record and eight visually
  inspected top-view frames are included under `evidence/controller_recovery_*`.
- Submission video: H.264, 1280 × 720, 76.672 seconds; visually inspected using
  a six-frame contact sheet and final-frame export.

## Artifact verification

- Results workbook: five sheets; no formula-error tokens detected.
- Dissertation working draft: valid DOCX and 10-page searchable PDF.
- Participant evaluation pack: valid DOCX and 5-page searchable PDF.
- Project-plan presentation: valid nine-slide PPTX; all slides rendered and
  visually inspected. The intentional full-bleed title-slide bands touch the
  slide boundary; no content is clipped.
- Office documents were opened structurally and generated document layouts
  were visually checked after PDF export.

## Clean-copy and integrity checks

- No Git repository or remote publication is included.
- No dependency cache, `node_modules`, Python bytecode, temporary Office file
  or Webots GUI project-state file is included.
- Project-owned code, worlds, resources, results, evidence and supporting
  materials are contained in this folder.
- The simplification proposal, its implementation, automated tests, Webots
  world, telemetry, event logs and captured validation frames are included.
- Standard Webots R2025a PROTO/runtime dependencies remain external as stated
  in `SUBMISSION_GUIDE.md`.
- `SUBMISSION_MANIFEST.json` provides per-file SHA-256 digests and sizes.

## Research status boundary

The technical simulation and recorded formal experiments are complete for the
defined scope. Ethics approval, participant recruitment and data collection,
verified academic references, supervisor sign-off and the final dissertation
remain pending. The included dissertation and participant documents are
therefore explicitly labelled as working drafts and must not be represented as
approved final research outputs.
