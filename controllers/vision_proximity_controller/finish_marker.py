"""Interactive black-and-white racing-grid finish detection."""

from __future__ import annotations

import cv2
import numpy as np


def detect_checkered_finish(frame: np.ndarray) -> bool:
    """Detect several compact white tiles separated by the dark road."""

    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        return False
    height, width = frame.shape[:2]
    y0, y1 = int(height * 0.45), int(height * 0.88)
    x0, x1 = int(width * 0.08), int(width * 0.92)
    crop = frame[y0:y1, x0:x1]
    if crop.size == 0:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(
        bright,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    crop_area = max(crop.shape[0] * crop.shape[1], 1)
    centers: list[tuple[float, float]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(8.0, crop_area * 0.00035) or area > crop_area * 0.04:
            continue
        x, y, tile_width, tile_height = cv2.boundingRect(contour)
        aspect = tile_width / max(tile_height, 1)
        if not 0.22 <= aspect <= 4.5:
            continue
        centers.append((x + tile_width / 2.0, y + tile_height / 2.0))

    if len(centers) >= 4:
        horizontal_span = max(x for x, _ in centers) - min(x for x, _ in centers)
        vertical_span = max(y for _, y in centers) - min(y for _, y in centers)
        if (
            horizontal_span >= crop.shape[1] * 0.20
            and vertical_span >= crop.shape[0] * 0.05
        ):
            return True

    # Adjacent diagonal white tiles may form one 8-connected contour. Their
    # repeated internal corners still distinguish the grid from two long lane
    # boundaries.
    binary = bright > 0
    horizontal_transitions = int(
        np.max(np.count_nonzero(binary[:, 1:] != binary[:, :-1], axis=1))
    )
    vertical_transitions = int(
        np.max(np.count_nonzero(binary[1:, :] != binary[:-1, :], axis=0))
    )
    bright_fraction = float(np.count_nonzero(bright)) / crop_area
    return (
        0.025 <= bright_fraction <= 0.45
        and horizontal_transitions >= 6
        and vertical_transitions >= 4
    )
