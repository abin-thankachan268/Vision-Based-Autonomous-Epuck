"""Pure geometry and run aggregation helpers used by the Supervisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot


STRAIGHT_HALF_LENGTH = 0.75
TRACK_RADIUS = 0.45
LANE_LIMIT = 0.20


def distance_2d(first: tuple[float, float], second: tuple[float, float]) -> float:
    return hypot(first[0] - second[0], first[1] - second[1])


def oval_lane_error(x: float, y: float) -> float:
    """Return absolute lateral error from the generated oval centre line."""

    if -STRAIGHT_HALF_LENGTH <= x <= STRAIGHT_HALF_LENGTH:
        return min(abs(y - TRACK_RADIUS), abs(y + TRACK_RADIUS))
    center_x = STRAIGHT_HALF_LENGTH if x > STRAIGHT_HALF_LENGTH else -STRAIGHT_HALF_LENGTH
    return abs(hypot(x - center_x, y) - TRACK_RADIUS)


@dataclass
class RunAccumulator:
    lane_errors: list[float] = field(default_factory=list)
    collision_count: int = 0
    minimum_static_clearance: float = float("inf")
    minimum_moving_clearance: float = float("inf")
    _static_contact: bool = False
    _moving_contact: bool = False

    def update(
        self,
        lane_error: float,
        static_clearance: float,
        moving_clearance: float,
        collision_threshold: float = 0.078,
    ) -> None:
        self.lane_errors.append(lane_error)
        self.minimum_static_clearance = min(self.minimum_static_clearance, static_clearance)
        self.minimum_moving_clearance = min(self.minimum_moving_clearance, moving_clearance)

        static_contact = static_clearance <= collision_threshold
        moving_contact = moving_clearance <= collision_threshold
        if static_contact and not self._static_contact:
            self.collision_count += 1
        if moving_contact and not self._moving_contact:
            self.collision_count += 1
        self._static_contact = static_contact
        self._moving_contact = moving_contact

    @property
    def mean_lane_error(self) -> float:
        return sum(self.lane_errors) / len(self.lane_errors) if self.lane_errors else 0.0

    @property
    def maximum_lane_error(self) -> float:
        return max(self.lane_errors, default=0.0)

    @property
    def within_lane_fraction(self) -> float:
        if not self.lane_errors:
            return 0.0
        return sum(error <= LANE_LIMIT for error in self.lane_errors) / len(self.lane_errors)
