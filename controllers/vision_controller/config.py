"""Configuration values shared by perception, control and telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PerceptionConfig:
    """OpenCV thresholds expressed independently of a specific Webots world."""

    roi_top_fraction: float = 0.10
    body_mask_top_fraction: float = 0.45
    body_mask_left_fraction: float = 0.34
    body_mask_right_fraction: float = 0.66
    white_max_saturation: int = 75
    white_min_value: int = 40
    white_contrast_delta: int = 1
    minimum_lane_pixels: int = 100
    nominal_lane_width_fraction: float = 0.22
    minimum_lane_confidence: float = 0.28
    obstacle_min_area_fraction: float = 0.0015
    maximum_obstacles: int = 8
    obstacle_roi_top_fraction: float = 0.28
    obstacle_corridor_padding_fraction: float = 0.06
    blocked_corridor_fraction: float = 0.72
    red_hue_low_1: int = 0
    red_hue_high_1: int = 12
    red_hue_low_2: int = 168
    red_hue_high_2: int = 179
    blue_hue_low: int = 95
    blue_hue_high: int = 135
    obstacle_min_saturation: int = 90
    obstacle_min_value: int = 70
    finish_hue_low: int = 38
    finish_hue_high: int = 88
    finish_min_saturation: int = 90
    finish_min_value: int = 70
    finish_min_area_fraction: float = 0.025


@dataclass(frozen=True)
class TrackerConfig:
    """Parameters for classifying motion from a centroid history."""

    history_size: int = 8
    minimum_samples: int = 4
    moving_displacement_fraction: float = 0.035
    stationary_displacement_fraction: float = 0.012
    maximum_missed_frames: int = 4
    association_distance_fraction: float = 0.18


@dataclass(frozen=True)
class ControlConfig:
    """Closed-loop motor and state-machine configuration."""

    maximum_speed: float = 6.28
    cruise_speed: float = 4.6
    cautious_speed: float = 2.8
    kp: float = 8.0
    ki: float = 0.02
    kd: float = 0.08
    steering_deadband: float = 0.005
    integral_limit: float = 1.0
    lost_lane_frames: int = 5
    clear_obstacle_frames: int = 5
    stationary_confirm_frames: int = 5
    rejoin_confirm_frames: int = 5
    rejoin_timeout_seconds: float = 8.0
    stop_wait_timeout_seconds: float = 12.0
    avoidance_timeout_seconds: float = 10.0
    avoidance_turn_speed: float = 1.5
    avoidance_leg_seconds: float = 1.8
    avoidance_commit_seconds: float = 3.6
    search_turn_speed: float = 1.5
    minimum_finish_time_seconds: float = 5.0


@dataclass(frozen=True)
class ControllerConfig:
    """Top-level immutable configuration for a reproducible run."""

    perception: PerceptionConfig = field(default_factory=PerceptionConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    telemetry_filename: str = "vision_telemetry.csv"
