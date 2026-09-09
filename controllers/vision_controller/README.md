# Vision Controller Architecture

The vision controller is deliberately separated from the original ground-sensor
prototype. The final navigation path is:

1. `vision_controller.py` reads only the e-puck camera and applies motor speeds.
2. `perception.py` converts the Webots BGRA buffer to OpenCV BGR, detects white
   lane boundaries, estimates lane-centre error, detects red/blue obstacles,
   merges same-object contour fragments, ranks threats and detects when the
   visible driving corridor is blocked.
3. `tracking.py` maintains independent multi-frame tracks with stable IDs and
   classifies each object's motion from centroid history. Colour is retained for
   association and evidence but is not used as the moving/static label.
4. `control.py` uses PID steering and the documented navigation state machine.
   It binds an avoidance manoeuvre to the active track/colour, stops for moving
   or unknown objects, and conservatively stops when multiple obstacles block
   the available corridor.
5. `telemetry.py` records the obstacle count, primary track, threat score,
   blocked-path flag, perception values and control outputs in a reproducible CSV.

The Supervisor must never send position or distance data to this controller.
Ground sensors are intentionally absent. They remain available only in the
separate `baseline_ground` controller for experimental comparison.

## State behavior

- `FOLLOW_LANE`: steer from camera-derived lane-centre error.
- `STOP_WAIT`: stop while an unknown or moving obstacle remains visible.
- `AVOID`: steer away from a stationary obstacle using its image centroid.
- `REJOIN`: search for and confirm the lane before returning to normal control.
- `FINISHED`: stop after the finish condition is detected.
- `FAILSAFE`: stop after a recovery, wait or avoidance timeout.

## Offline validation

Run from the project root:

```powershell
python -m unittest discover -s tests -v
```

The tests generate deterministic fixtures and do not require Webots.
