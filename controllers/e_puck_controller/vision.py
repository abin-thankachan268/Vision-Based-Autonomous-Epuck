"""Simple fixed-threshold vision and single-target centroid tracking."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import hypot
from typing import Optional

import cv2
import numpy as np


class MotionClass(str, Enum):
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    MOVING = "MOVING"
    STATIONARY = "STATIONARY"


@dataclass(frozen=True)
class LaneObservation:
    center_x: Optional[float] = None
    error: float = 0.0
    confidence: float = 0.0
    left_x: Optional[float] = None
    right_x: Optional[float] = None

    @property
    def visible(self) -> bool:
        return self.center_x is not None and self.confidence > 0.0


@dataclass(frozen=True)
class ObstacleObservation:
    color: str = ""
    bbox: Optional[tuple[int, int, int, int]] = None
    centroid: Optional[tuple[float, float]] = None
    area_fraction: float = 0.0
    motion: MotionClass = MotionClass.NONE
    motion_confidence: float = 0.0

    @property
    def present(self) -> bool:
        return self.bbox is not None and self.centroid is not None


@dataclass(frozen=True)
class SceneObservation:
    lane: LaneObservation = LaneObservation()
    obstacle: ObstacleObservation = ObstacleObservation()
    finish_visible: bool = False
    frame_width: int = 0
    frame_height: int = 0


@dataclass(frozen=True)
class VisionConfig:
    # Fixed thresholds are deliberate: the simplified world uses controlled light.
    roi_top_fraction: float = 0.15
    body_mask_top_fraction: float = 0.52
    body_mask_left_fraction: float = 0.35
    body_mask_right_fraction: float = 0.65
    white_max_saturation: int = 75
    white_min_value: int = 90
    minimum_lane_pixels: int = 80
    minimum_lane_component_height_fraction: float = 0.08
    minimum_lane_confidence: float = 0.35
    maximum_lane_coverage: float = 0.52
    nominal_lane_width_fraction: float = 0.22
    obstacle_roi_top_fraction: float = 0.28
    obstacle_min_area_fraction: float = 0.0015
    obstacle_min_saturation: int = 90
    obstacle_min_value: int = 65
    history_size: int = 6
    minimum_motion_samples: int = 4
    moving_displacement_fraction: float = 0.035
    stationary_spread_fraction: float = 0.014
    association_distance_fraction: float = 0.20
    maximum_missed_frames: int = 4


def webots_bgra_to_bgr(image: bytes, width: int, height: int) -> np.ndarray:
    """Convert a Webots BGRA camera buffer to an OpenCV BGR image."""

    data = np.frombuffer(image, dtype=np.uint8)
    expected = width * height * 4
    if data.size != expected:
        raise ValueError(f"Expected {expected} camera bytes, received {data.size}")
    return cv2.cvtColor(data.reshape((height, width, 4)), cv2.COLOR_BGRA2BGR)


def detect_checkered_finish(frame: np.ndarray) -> bool:
    """Recognize the compact black-and-white racing grid near the robot."""

    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        return False
    height, width = frame.shape[:2]
    crop = frame[int(height * 0.45) : int(height * 0.90), int(width * 0.08) : int(width * 0.92)]
    if crop.size == 0:
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)
    binary = bright > 0
    crop_area = max(crop.shape[0] * crop.shape[1], 1)
    bright_fraction = float(np.count_nonzero(binary)) / crop_area
    horizontal = int(np.max(np.count_nonzero(binary[:, 1:] != binary[:, :-1], axis=1)))
    vertical = int(np.max(np.count_nonzero(binary[1:, :] != binary[:-1, :], axis=0)))
    return 0.025 <= bright_fraction <= 0.45 and horizontal >= 4 and vertical >= 2


class RelevantObjectTracker:
    """Track only the currently relevant obstacle across consecutive frames."""

    def __init__(self, config: VisionConfig):
        self.config = config
        self.color = ""
        self.history: deque[tuple[float, float]] = deque(maxlen=config.history_size)
        self.missed_frames = 0

    def reset(self) -> None:
        self.color = ""
        self.history.clear()
        self.missed_frames = 0

    def missing(self) -> None:
        self.missed_frames += 1
        if self.missed_frames > self.config.maximum_missed_frames:
            self.reset()

    def update(
        self,
        color: str,
        centroid: tuple[float, float],
        width: int,
        height: int,
    ) -> tuple[MotionClass, float]:
        diagonal = max(hypot(width, height), 1.0)
        if (
            self.history
            and (
                color != self.color
                or hypot(
                    centroid[0] - self.history[-1][0],
                    centroid[1] - self.history[-1][1],
                )
                > diagonal * self.config.association_distance_fraction
            )
        ):
            self.reset()
        self.color = color
        self.missed_frames = 0
        self.history.append(centroid)
        if len(self.history) < self.config.minimum_motion_samples:
            return MotionClass.UNKNOWN, len(self.history) / self.config.minimum_motion_samples
        first = self.history[0]
        last = self.history[-1]
        net = hypot(last[0] - first[0], last[1] - first[1]) / diagonal
        spread = max(
            hypot(point[0] - first[0], point[1] - first[1]) / diagonal
            for point in self.history
        )
        if net >= self.config.moving_displacement_fraction:
            return MotionClass.MOVING, min(1.0, net / self.config.moving_displacement_fraction)
        if spread <= self.config.stationary_spread_fraction:
            confidence = 1.0 - spread / max(self.config.stationary_spread_fraction, 1e-6)
            return MotionClass.STATIONARY, max(0.5, confidence)
        return MotionClass.UNKNOWN, 0.4


class SimpleVision:
    """Fixed HSV lane detection plus one relevant red/blue obstacle target."""

    def __init__(self, config: VisionConfig | None = None):
        self.config = config or VisionConfig()
        self.tracker = RelevantObjectTracker(self.config)

    def process_webots_image(self, image: bytes, width: int, height: int) -> SceneObservation:
        return self.process_frame(webots_bgra_to_bgr(image, width, height))

    def process_frame(self, frame: np.ndarray) -> SceneObservation:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("process_frame expects a non-empty BGR image")
        height, width = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        candidates, obstacle_mask = self._obstacle_candidates(hsv, width, height)
        lane = self._detect_lane(hsv, obstacle_mask, width, height)
        obstacle = self._select_relevant(candidates, lane, width, height)
        if obstacle.present and obstacle.centroid is not None:
            motion, confidence = self.tracker.update(
                obstacle.color, obstacle.centroid, width, height
            )
            obstacle = ObstacleObservation(
                color=obstacle.color,
                bbox=obstacle.bbox,
                centroid=obstacle.centroid,
                area_fraction=obstacle.area_fraction,
                motion=motion,
                motion_confidence=confidence,
            )
        else:
            self.tracker.missing()
        return SceneObservation(
            lane=lane,
            obstacle=obstacle,
            finish_visible=detect_checkered_finish(frame) or self._green_finish(hsv, width, height),
            frame_width=width,
            frame_height=height,
        )

    def _detect_lane(
        self,
        hsv: np.ndarray,
        obstacle_mask: np.ndarray,
        width: int,
        height: int,
    ) -> LaneObservation:
        cfg = self.config
        roi_top = int(height * cfg.roi_top_fraction)
        mask = cv2.inRange(
            hsv,
            np.array([0, 0, cfg.white_min_value], dtype=np.uint8),
            np.array([179, cfg.white_max_saturation, 255], dtype=np.uint8),
        )
        mask[:roi_top, :] = 0
        body_top = int(height * cfg.body_mask_top_fraction)
        body_left = int(width * cfg.body_mask_left_fraction)
        body_right = int(width * cfg.body_mask_right_fraction)
        mask[body_top:, body_left:body_right] = 0
        mask[obstacle_mask > 0] = 0
        kernel = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        roi_area = max((height - roi_top) * width, 1)
        if float(np.count_nonzero(mask[roi_top:, :])) / roi_area > cfg.maximum_lane_coverage:
            # A single boundary directly beneath the camera can fill most of
            # the frame.  Reject it instead of splitting that one strip into
            # artificial left and right boundaries.
            return LaneObservation()
        total_pixels = int(np.count_nonzero(mask))
        if total_pixels < cfg.minimum_lane_pixels:
            return LaneObservation()
        image_center = width / 2.0
        component_count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
        minimum_side = max(12, cfg.minimum_lane_pixels // 5)
        components: list[tuple[int, float]] = []
        minimum_component_height = max(
            8, int(height * cfg.minimum_lane_component_height_fraction)
        )
        for label in range(1, component_count):
            x, _y, box_width, box_height, area = stats[label]
            if area < minimum_side:
                continue
            # Real side boundaries extend down into the road view. Thin
            # bright bands at the horizon can otherwise look like two valid
            # boundaries after the robot has left the track.
            if box_height < minimum_component_height:
                continue
            # A stripe spanning the image centre is a transverse boundary,
            # not a pair of lane sides.
            if x < image_center < x + box_width:
                continue
            component_xs = np.where(labels == label)[1]
            components.append((int(area), float(np.median(component_xs))))
        left_components = [item for item in components if item[1] < image_center]
        right_components = [item for item in components if item[1] >= image_center]
        left = max(left_components, default=(0, None), key=lambda item: item[0])[1]
        right = max(right_components, default=(0, None), key=lambda item: item[0])[1]
        nominal_width = width * cfg.nominal_lane_width_fraction
        if left is not None and right is not None and right > left:
            center = (left + right) / 2.0
            boundary_score = 1.0
        elif left is not None:
            center = left + nominal_width / 2.0
            boundary_score = 0.48
        elif right is not None:
            center = right - nominal_width / 2.0
            boundary_score = 0.48
        else:
            return LaneObservation()
        coverage = min(
            1.0,
            sum(area for area, _center in components)
            / max(width * (height - roi_top) * 0.025, 1.0),
        )
        confidence = min(1.0, 0.75 * boundary_score + 0.25 * coverage)
        error = float(np.clip((center - image_center) / max(image_center, 1.0), -1.0, 1.0))
        return LaneObservation(center, error, confidence, left, right)

    def _obstacle_candidates(
        self, hsv: np.ndarray, width: int, height: int
    ) -> tuple[list[ObstacleObservation], np.ndarray]:
        cfg = self.config
        lower_common = (cfg.obstacle_min_saturation, cfg.obstacle_min_value)
        red_a = cv2.inRange(
            hsv,
            np.array([0, *lower_common], dtype=np.uint8),
            np.array([12, 255, 255], dtype=np.uint8),
        )
        red_b = cv2.inRange(
            hsv,
            np.array([168, *lower_common], dtype=np.uint8),
            np.array([179, 255, 255], dtype=np.uint8),
        )
        red = cv2.bitwise_or(red_a, red_b)
        blue = cv2.inRange(
            hsv,
            np.array([95, *lower_common], dtype=np.uint8),
            np.array([135, 255, 255], dtype=np.uint8),
        )
        roi_top = int(height * cfg.obstacle_roi_top_fraction)
        red[:roi_top, :] = 0
        blue[:roi_top, :] = 0
        kernel = np.ones((5, 5), dtype=np.uint8)
        red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, kernel)
        blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, kernel)
        candidates: list[ObstacleObservation] = []
        for color, mask in (("red", red), ("blue", blue)):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                area_fraction = area / max(width * height, 1)
                if area_fraction < cfg.obstacle_min_area_fraction:
                    continue
                x, y, box_width, box_height = cv2.boundingRect(contour)
                moments = cv2.moments(contour)
                centroid = (
                    (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
                    if moments["m00"]
                    else (x + box_width / 2.0, y + box_height / 2.0)
                )
                candidates.append(
                    ObstacleObservation(color, (x, y, box_width, box_height), centroid, area_fraction)
                )
        return candidates, cv2.bitwise_or(red, blue)

    def _select_relevant(
        self,
        candidates: list[ObstacleObservation],
        lane: LaneObservation,
        width: int,
        height: int,
    ) -> ObstacleObservation:
        if not candidates:
            return ObstacleObservation()
        lane_center = lane.center_x if lane.center_x is not None else width / 2.0
        corridor = width * 0.22

        def score(item: ObstacleObservation) -> float:
            assert item.centroid is not None
            vertical = item.centroid[1] / max(height, 1)
            near_lane = max(0.0, 1.0 - abs(item.centroid[0] - lane_center) / max(corridor, 1.0))
            size = min(1.0, item.area_fraction / max(self.config.obstacle_min_area_fraction * 8, 1e-6))
            return 0.50 * vertical + 0.30 * near_lane + 0.20 * size

        return max(candidates, key=score)

    @staticmethod
    def _green_finish(hsv: np.ndarray, width: int, height: int) -> bool:
        mask = cv2.inRange(
            hsv,
            np.array([38, 90, 70], dtype=np.uint8),
            np.array([88, 255, 255], dtype=np.uint8),
        )
        mask[: int(height * 0.55), :] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = max((cv2.contourArea(contour) for contour in contours), default=0.0)
        return area / max(width * height, 1) >= 0.025
