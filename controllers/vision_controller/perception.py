"""Classical OpenCV perception for lane and obstacle analysis."""

from __future__ import annotations

from dataclasses import replace
from math import hypot
from typing import Optional

import cv2
import numpy as np

from .config import ControllerConfig
from .models import LaneEstimate, ObstacleDetection, PerceptionResult
from .tracking import MultiObjectTracker


def webots_bgra_to_bgr(image: bytes, width: int, height: int) -> np.ndarray:
    """Convert Webots' four-channel camera buffer into an OpenCV BGR frame."""

    expected = width * height * 4
    array = np.frombuffer(image, dtype=np.uint8)
    if array.size != expected:
        raise ValueError(f"Expected {expected} camera bytes, received {array.size}")
    bgra = array.reshape((height, width, 4))
    return cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)


class VisionPerception:
    """Extract lane geometry and independently tracked obstacle candidates."""

    def __init__(self, config: Optional[ControllerConfig] = None):
        self.config = config or ControllerConfig()
        self.tracker = MultiObjectTracker(self.config.tracker)

    def process_webots_image(
        self,
        image: bytes,
        width: int,
        height: int,
        timestamp: float,
    ) -> PerceptionResult:
        return self.process_frame(
            webots_bgra_to_bgr(image, width, height),
            timestamp=timestamp,
        )

    @staticmethod
    def webots_frame_to_bgr(image: bytes, width: int, height: int) -> np.ndarray:
        """Expose the camera conversion for optional local diagnostic captures."""

        return webots_bgra_to_bgr(image, width, height)

    def process_frame(self, frame: np.ndarray, timestamp: float = 0.0) -> PerceptionResult:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("process_frame expects a non-empty BGR image")

        height, width = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detected_obstacles, obstacle_mask = self._detect_obstacles(hsv, width, height)
        lane = self._detect_lane(hsv, obstacle_mask, width, height)
        finish_visible = self._detect_finish(hsv, width, height)
        tracked_obstacles = self.tracker.update(detected_obstacles, width, height)
        obstacles = self._rank_obstacles(tracked_obstacles, lane, width, height)
        obstacle = obstacles[0] if obstacles else ObstacleDetection()
        path_blocked = self._path_blocked(obstacles, lane, width, height)

        return PerceptionResult(
            lane=lane,
            obstacle=obstacle,
            obstacles=obstacles,
            frame_width=width,
            frame_height=height,
            timestamp=timestamp,
            finish_visible=finish_visible,
            path_blocked=path_blocked,
        )

    def _lane_corridor(
        self,
        lane: LaneEstimate,
        width: int,
    ) -> tuple[float, float]:
        cfg = self.config.perception
        padding = width * cfg.obstacle_corridor_padding_fraction
        if (
            lane.left_boundary_x is not None
            and lane.right_boundary_x is not None
            and lane.right_boundary_x > lane.left_boundary_x
        ):
            left = lane.left_boundary_x - padding
            right = lane.right_boundary_x + padding
        else:
            nominal_width = width * cfg.nominal_lane_width_fraction
            left = width / 2.0 - nominal_width / 2.0 - padding
            right = width / 2.0 + nominal_width / 2.0 + padding
        return max(0.0, left), min(float(width), right)

    def _rank_obstacles(
        self,
        obstacles: tuple[ObstacleDetection, ...],
        lane: LaneEstimate,
        width: int,
        height: int,
    ) -> tuple[ObstacleDetection, ...]:
        if not obstacles:
            return ()
        corridor_left, corridor_right = self._lane_corridor(lane, width)
        ranked: list[ObstacleDetection] = []
        for obstacle in obstacles:
            if obstacle.centroid is None or obstacle.bbox is None:
                continue
            x, _y, box_width, _box_height = obstacle.bbox
            centroid_x, centroid_y = obstacle.centroid
            vertical_score = min(1.0, max(0.0, centroid_y / max(height, 1)))
            size_score = min(
                1.0,
                obstacle.area_fraction
                / max(self.config.perception.obstacle_min_area_fraction * 8.0, 1e-6),
            )
            overlap = max(
                0.0,
                min(x + box_width, corridor_right) - max(x, corridor_left),
            )
            path_score = min(1.0, overlap / max(box_width, 1))
            motion_score = {
                "MOVING": 1.0,
                "UNKNOWN": 0.85,
                "STATIONARY": 0.55,
            }.get(obstacle.motion.value, 0.0)
            threat_score = (
                0.34 * vertical_score
                + 0.30 * path_score
                + 0.21 * size_score
                + 0.15 * motion_score
            )
            ranked.append(replace(obstacle, threat_score=threat_score))
        ranked.sort(
            key=lambda item: (item.threat_score, item.area_fraction, item.track_id),
            reverse=True,
        )
        return tuple(ranked)

    def _path_blocked(
        self,
        obstacles: tuple[ObstacleDetection, ...],
        lane: LaneEstimate,
        width: int,
        height: int,
    ) -> bool:
        if len(obstacles) < 2:
            return False
        corridor_left, corridor_right = self._lane_corridor(lane, width)
        corridor_width = max(corridor_right - corridor_left, 1.0)
        intervals: list[tuple[float, float]] = []
        closest_y = max(
            obstacle.centroid[1]
            for obstacle in obstacles
            if obstacle.centroid is not None
        )
        for obstacle in obstacles:
            if obstacle.bbox is None or obstacle.centroid is None:
                continue
            if obstacle.centroid[1] < height * 0.52:
                continue
            if closest_y - obstacle.centroid[1] > height * 0.20:
                continue
            x, _y, box_width, _box_height = obstacle.bbox
            start = max(corridor_left, float(x))
            end = min(corridor_right, float(x + box_width))
            if end > start:
                intervals.append((start, end))
        if not intervals:
            return False
        intervals.sort()
        covered = 0.0
        current_start, current_end = intervals[0]
        for start, end in intervals[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                covered += current_end - current_start
                current_start, current_end = start, end
        covered += current_end - current_start
        return covered / corridor_width >= self.config.perception.blocked_corridor_fraction

    def _detect_finish(self, hsv: np.ndarray, width: int, height: int) -> bool:
        cfg = self.config.perception
        mask = cv2.inRange(
            hsv,
            np.array(
                [cfg.finish_hue_low, cfg.finish_min_saturation, cfg.finish_min_value],
                dtype=np.uint8,
            ),
            np.array([cfg.finish_hue_high, 255, 255], dtype=np.uint8),
        )
        mask[: int(height * 0.55), :] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest = max((cv2.contourArea(contour) for contour in contours), default=0.0)
        return largest / max(width * height, 1) >= cfg.finish_min_area_fraction

    def _detect_lane(
        self,
        hsv: np.ndarray,
        obstacle_mask: np.ndarray,
        width: int,
        height: int,
    ) -> LaneEstimate:
        cfg = self.config.perception
        roi_top = int(height * cfg.roi_top_fraction)
        body_top = int(height * cfg.body_mask_top_fraction)
        body_left = int(width * cfg.body_mask_left_fraction)
        body_right = int(width * cfg.body_mask_right_fraction)
        eligible = np.zeros((height, width), dtype=bool)
        eligible[roi_top:, :] = True
        eligible[body_top:, body_left:body_right] = False
        low_saturation = hsv[:, :, 1] <= cfg.white_max_saturation
        background_values = hsv[:, :, 2][eligible & low_saturation]
        if background_values.size and int(np.ptp(background_values)) < 5:
            return LaneEstimate()
        if background_values.size:
            background_value, _ = cv2.threshold(
                background_values.reshape((-1, 1)),
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )
        else:
            background_value = float(cfg.white_min_value)
        adaptive_value = int(
            min(255, max(cfg.white_min_value, background_value + cfg.white_contrast_delta))
        )
        lower = np.array([0, 0, adaptive_value], dtype=np.uint8)
        upper = np.array([179, cfg.white_max_saturation, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        mask[:roi_top, :] = 0
        mask[body_top:, body_left:body_right] = 0
        mask[obstacle_mask > 0] = 0

        kernel = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        ys, xs = np.nonzero(mask)
        if len(xs) < cfg.minimum_lane_pixels:
            return LaneEstimate()

        image_center = width / 2.0
        left_xs = xs[xs < image_center]
        right_xs = xs[xs >= image_center]
        minimum_side_pixels = max(12, cfg.minimum_lane_pixels // 5)

        left = float(np.median(left_xs)) if len(left_xs) >= minimum_side_pixels else None
        right = float(np.median(right_xs)) if len(right_xs) >= minimum_side_pixels else None
        nominal_width = width * cfg.nominal_lane_width_fraction

        if left is not None and right is not None and right > left:
            center = (left + right) / 2.0
            side_score = 1.0
            measured_width = right - left
            width_score = max(0.0, 1.0 - abs(measured_width - nominal_width) / max(nominal_width, 1.0))
        elif left is not None:
            center = left + nominal_width / 2.0
            side_score = 0.48
            width_score = 0.45
        elif right is not None:
            center = right - nominal_width / 2.0
            side_score = 0.48
            width_score = 0.45
        else:
            return LaneEstimate()

        coverage = min(1.0, len(xs) / max(width * (height - roi_top) * 0.035, 1.0))
        confidence = min(1.0, 0.55 * side_score + 0.25 * width_score + 0.20 * coverage)
        normalized_error = float(np.clip((center - image_center) / max(image_center, 1.0), -1.0, 1.0))
        return LaneEstimate(
            center_x=center,
            normalized_error=normalized_error,
            confidence=confidence,
            left_boundary_x=left,
            right_boundary_x=right,
        )

    def _detect_obstacles(
        self,
        hsv: np.ndarray,
        width: int,
        height: int,
    ) -> tuple[tuple[ObstacleDetection, ...], np.ndarray]:
        cfg = self.config.perception
        saturation = cfg.obstacle_min_saturation
        value = cfg.obstacle_min_value

        red_1 = cv2.inRange(
            hsv,
            np.array([cfg.red_hue_low_1, saturation, value], dtype=np.uint8),
            np.array([cfg.red_hue_high_1, 255, 255], dtype=np.uint8),
        )
        red_2 = cv2.inRange(
            hsv,
            np.array([cfg.red_hue_low_2, saturation, value], dtype=np.uint8),
            np.array([cfg.red_hue_high_2, 255, 255], dtype=np.uint8),
        )
        red = cv2.bitwise_or(red_1, red_2)
        blue = cv2.inRange(
            hsv,
            np.array([cfg.blue_hue_low, saturation, value], dtype=np.uint8),
            np.array([cfg.blue_hue_high, 255, 255], dtype=np.uint8),
        )

        roi_top = int(height * cfg.obstacle_roi_top_fraction)
        red[:roi_top, :] = 0
        blue[:roi_top, :] = 0
        kernel = np.ones((5, 5), dtype=np.uint8)
        red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, kernel)
        blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, kernel)

        candidates: list[tuple[float, str, np.ndarray]] = []
        for color, mask in (("red", red), ("blue", blue)):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                candidates.append((cv2.contourArea(contour), color, contour))

        combined = cv2.bitwise_or(red, blue)
        detections: list[ObstacleDetection] = []
        for area, color, contour in sorted(candidates, key=lambda item: item[0], reverse=True):
            area_fraction = area / max(width * height, 1)
            if area_fraction < cfg.obstacle_min_area_fraction:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            moments = cv2.moments(contour)
            if moments["m00"]:
                centroid = (
                    moments["m10"] / moments["m00"],
                    moments["m01"] / moments["m00"],
                )
            else:
                centroid = (x + w / 2.0, y + h / 2.0)
            confidence = min(
                1.0,
                area_fraction / (cfg.obstacle_min_area_fraction * 4.0),
            )
            detection = ObstacleDetection(
                bbox=(x, y, w, h),
                centroid=centroid,
                area_fraction=area_fraction,
                observed_color=color,
                confidence=confidence,
            )
            merge_index = next(
                (
                    index
                    for index, existing in enumerate(detections)
                    if existing.observed_color == color
                    and existing.centroid is not None
                    and hypot(
                        existing.centroid[0] - centroid[0],
                        existing.centroid[1] - centroid[1],
                    )
                    <= hypot(width, height) * 0.08
                ),
                None,
            )
            if merge_index is None:
                detections.append(detection)
            else:
                existing = detections[merge_index]
                assert existing.bbox is not None and existing.centroid is not None
                existing_x, existing_y, existing_w, existing_h = existing.bbox
                merged_x = min(existing_x, x)
                merged_y = min(existing_y, y)
                merged_right = max(existing_x + existing_w, x + w)
                merged_bottom = max(existing_y + existing_h, y + h)
                merged_area = existing.area_fraction + area_fraction
                existing_weight = existing.area_fraction / max(merged_area, 1e-9)
                new_weight = area_fraction / max(merged_area, 1e-9)
                detections[merge_index] = ObstacleDetection(
                    bbox=(
                        merged_x,
                        merged_y,
                        merged_right - merged_x,
                        merged_bottom - merged_y,
                    ),
                    centroid=(
                        existing.centroid[0] * existing_weight + centroid[0] * new_weight,
                        existing.centroid[1] * existing_weight + centroid[1] * new_weight,
                    ),
                    area_fraction=merged_area,
                    observed_color=color,
                    confidence=max(existing.confidence, confidence),
                )
            if len(detections) >= cfg.maximum_obstacles:
                break
        return tuple(detections), combined
