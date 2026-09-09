"""Generate deterministic synthetic camera frames for offline tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


WIDTH = 320
HEIGHT = 240


def lane_frame(offset: int = 0, obstacle: str | None = None, obstacle_x: int = 160) -> np.ndarray:
    image = np.full((HEIGHT, WIDTH, 3), (42, 42, 42), dtype=np.uint8)
    vanishing = (WIDTH // 2 + offset // 3, 90)
    cv2.line(image, (45 + offset, HEIGHT - 1), vanishing, (255, 255, 255), 7)
    cv2.line(image, (275 + offset, HEIGHT - 1), vanishing, (255, 255, 255), 7)
    if obstacle:
        color = (0, 0, 255) if obstacle == "red" else (255, 0, 0)
        cv2.rectangle(image, (obstacle_x - 18, 145), (obstacle_x + 18, 195), color, -1)
    return image


def finish_frame() -> np.ndarray:
    image = lane_frame()
    cv2.rectangle(image, (40, 195), (280, 225), (0, 210, 0), -1)
    return image


def write_fixtures(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "lane_centered.png": lane_frame(),
        "lane_left.png": lane_frame(offset=-35),
        "lane_right.png": lane_frame(offset=35),
        "stationary_red.png": lane_frame(obstacle="red"),
        "moving_blue_1.png": lane_frame(obstacle="blue", obstacle_x=120),
        "moving_blue_2.png": lane_frame(obstacle="blue", obstacle_x=145),
        "moving_blue_3.png": lane_frame(obstacle="blue", obstacle_x=170),
        "moving_blue_4.png": lane_frame(obstacle="blue", obstacle_x=195),
        "lane_missing.png": np.full((HEIGHT, WIDTH, 3), (42, 42, 42), dtype=np.uint8),
        "finish_visible.png": finish_frame(),
    }
    for name, frame in fixtures.items():
        if not cv2.imwrite(str(directory / name), frame):
            raise RuntimeError(f"Unable to write fixture {name}")


if __name__ == "__main__":
    write_fixtures(Path(__file__).resolve().parent)
