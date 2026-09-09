"""Centroid tracking for independent obstacle motion classification."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from math import hypot
from typing import Deque, Optional, Sequence, Tuple

from .config import TrackerConfig
from .models import ObstacleDetection, ObstacleMotion


def _classify_history(
    history: Sequence[Tuple[float, float]],
    config: TrackerConfig,
    frame_width: int,
    frame_height: int,
) -> tuple[ObstacleMotion, float]:
    if len(history) < config.minimum_samples:
        return ObstacleMotion.UNKNOWN, len(history) / config.minimum_samples

    diagonal = max(hypot(frame_width, frame_height), 1.0)
    first = history[0]
    last = history[-1]
    net_displacement = hypot(last[0] - first[0], last[1] - first[1]) / diagonal
    spread = max(
        hypot(point[0] - first[0], point[1] - first[1]) / diagonal
        for point in history
    )

    if net_displacement >= config.moving_displacement_fraction:
        confidence = min(1.0, net_displacement / config.moving_displacement_fraction)
        return ObstacleMotion.MOVING, confidence
    if spread <= config.stationary_displacement_fraction:
        confidence = 1.0 - min(1.0, spread / config.stationary_displacement_fraction)
        return ObstacleMotion.STATIONARY, max(0.5, confidence)
    return ObstacleMotion.UNKNOWN, 0.4


class CentroidMotionTracker:
    """Classify one visible obstacle without using color as motion ground truth."""

    def __init__(self, config: TrackerConfig):
        self.config = config
        self._history: Deque[Tuple[float, float]] = deque(maxlen=config.history_size)
        self._missed_frames = 0

    def reset(self) -> None:
        self._history.clear()
        self._missed_frames = 0

    def update(
        self,
        centroid: Optional[Tuple[float, float]],
        frame_width: int,
        frame_height: int,
    ) -> tuple[ObstacleMotion, float]:
        if centroid is None:
            self._missed_frames += 1
            if self._missed_frames > self.config.maximum_missed_frames:
                self.reset()
            return ObstacleMotion.NONE, 0.0

        self._missed_frames = 0
        self._history.append(centroid)
        return _classify_history(
            tuple(self._history), self.config, frame_width, frame_height
        )


@dataclass
class _Track:
    track_id: int
    color: str
    history_size: int
    history: Deque[Tuple[float, float]] = field(init=False)
    missed_frames: int = 0

    def __post_init__(self) -> None:
        self.history = deque(maxlen=self.history_size)


class MultiObjectTracker:
    """Maintain independent centroid histories using deterministic greedy matching."""

    def __init__(self, config: TrackerConfig):
        self.config = config
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1

    def reset(self) -> None:
        self._tracks.clear()
        self._next_track_id = 1

    def update(
        self,
        detections: Sequence[ObstacleDetection],
        frame_width: int,
        frame_height: int,
    ) -> tuple[ObstacleDetection, ...]:
        diagonal = max(hypot(frame_width, frame_height), 1.0)
        maximum_distance = self.config.association_distance_fraction * diagonal
        unmatched_tracks = set(self._tracks)
        assignments: dict[int, int] = {}

        detection_order = sorted(
            range(len(detections)),
            key=lambda index: detections[index].area_fraction,
            reverse=True,
        )
        for detection_index in detection_order:
            detection = detections[detection_index]
            if detection.centroid is None:
                continue
            compatible: list[tuple[float, int]] = []
            for track_id in unmatched_tracks:
                track = self._tracks[track_id]
                if track.color != detection.observed_color or not track.history:
                    continue
                previous = track.history[-1]
                distance = hypot(
                    detection.centroid[0] - previous[0],
                    detection.centroid[1] - previous[1],
                )
                if distance <= maximum_distance:
                    compatible.append((distance, track_id))
            if compatible:
                _, track_id = min(compatible)
                assignments[detection_index] = track_id
                unmatched_tracks.remove(track_id)

        for detection_index in detection_order:
            if detection_index in assignments:
                continue
            detection = detections[detection_index]
            if detection.centroid is None:
                continue
            track_id = self._next_track_id
            self._next_track_id += 1
            self._tracks[track_id] = _Track(
                track_id=track_id,
                color=detection.observed_color,
                history_size=self.config.history_size,
            )
            assignments[detection_index] = track_id

        updated: list[ObstacleDetection] = []
        matched_track_ids = set(assignments.values())
        for detection_index, detection in enumerate(detections):
            track_id = assignments.get(detection_index)
            if track_id is None or detection.centroid is None:
                updated.append(detection)
                continue
            track = self._tracks[track_id]
            track.missed_frames = 0
            track.history.append(detection.centroid)
            motion, motion_confidence = _classify_history(
                tuple(track.history), self.config, frame_width, frame_height
            )
            updated.append(
                replace(
                    detection,
                    track_id=track_id,
                    motion=motion,
                    confidence=min(
                        1.0,
                        0.55 * detection.confidence + 0.45 * motion_confidence,
                    ),
                )
            )

        expired: list[int] = []
        for track_id, track in self._tracks.items():
            if track_id not in matched_track_ids:
                track.missed_frames += 1
                if track.missed_frames > self.config.maximum_missed_frames:
                    expired.append(track_id)
        for track_id in expired:
            del self._tracks[track_id]

        return tuple(updated)
