"""Typed results passed between the perception and control subsystems."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class ControllerState(str, Enum):
    FOLLOW_LANE = "FOLLOW_LANE"
    STOP_WAIT = "STOP_WAIT"
    AVOID = "AVOID"
    REJOIN = "REJOIN"
    FINISHED = "FINISHED"
    FAILSAFE = "FAILSAFE"


class ObstacleMotion(str, Enum):
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    MOVING = "MOVING"
    STATIONARY = "STATIONARY"


@dataclass(frozen=True)
class LaneEstimate:
    center_x: Optional[float] = None
    normalized_error: float = 0.0
    confidence: float = 0.0
    left_boundary_x: Optional[float] = None
    right_boundary_x: Optional[float] = None

    @property
    def visible(self) -> bool:
        return self.center_x is not None and self.confidence > 0.0


@dataclass(frozen=True)
class ObstacleDetection:
    track_id: int = -1
    bbox: Optional[Tuple[int, int, int, int]] = None
    centroid: Optional[Tuple[float, float]] = None
    area_fraction: float = 0.0
    observed_color: str = ""
    motion: ObstacleMotion = ObstacleMotion.NONE
    confidence: float = 0.0
    threat_score: float = 0.0

    @property
    def present(self) -> bool:
        return self.bbox is not None and self.centroid is not None


@dataclass(frozen=True)
class PerceptionResult:
    lane: LaneEstimate = LaneEstimate()
    obstacle: ObstacleDetection = ObstacleDetection()
    obstacles: Tuple[ObstacleDetection, ...] = ()
    frame_width: int = 0
    frame_height: int = 0
    timestamp: float = 0.0
    finish_visible: bool = False
    path_blocked: bool = False


@dataclass(frozen=True)
class ControlCommand:
    left_speed: float
    right_speed: float
    state: ControllerState
    reason: str
