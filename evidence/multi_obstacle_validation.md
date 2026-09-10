# Multi-Obstacle Validation

The main Webots world now contains three configurable red static obstacles and
two configurable blue moving objects. Formal configuration
`82999888659be0c7` was tested in three additional scenarios, each repeated ten
times.

| Scenario | Layout | Completed | Collisions | Mean lane error |
|---|---|---:|---:|---:|
| `multi_static_sequential` | Two red obstacles encountered sequentially | 10/10 | 0 | 0.058470 m |
| `multi_moving_crossings` | Two blue crossings | 10/10 | 0 | 0.036728 m |
| `multi_mixed_obstacles` | Red static plus blue moving object | 10/10 | 0 | 0.050727 m |

The camera controller now detects multiple contours, merges fragments that
belong to one physical object, associates detections with stable track IDs,
ranks threats, and stops when the visible corridor is blocked. The controller
does not receive obstacle positions or distances from the Supervisor.

This verifies the configured layouts only. It does not imply that arbitrary
numbers, shapes, colours, placements or fully simultaneous occluded obstacles
will always be handled. New layouts should be added as scenarios and tested
before being treated as supported.
