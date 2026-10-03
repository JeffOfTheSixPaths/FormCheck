"""Geometric and kinematic analysis of human pose landmarks."""

import math
from typing import Any, Optional, Tuple
import numpy as np

from pose.landmarks import PoseLandmark


def get_landmark_coords(
    landmarks: Any,
    index: int,
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None,
) -> Optional[Tuple[float, float]]:
    """Extracts (x, y) coordinates for a landmark index.

    If frame dimensions are provided, returns pixel coordinates (int, int),
    otherwise returns normalized [0.0, 1.0] coordinates.
    """
    if landmarks is None or index < 0 or index >= len(landmarks):
        return None

    lm = landmarks[index]
    if frame_width is not None and frame_height is not None:
        return (lm.x * frame_width, lm.y * frame_height)
    return (lm.x, lm.y)


def calculate_angle_2d(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> float:
    """Calculates the 2D interior angle at vertex b between rays ba and bc.

    Returns an angle in degrees [0, 180].
    """
    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float32)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=np.float32)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return 0.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    # Clip to avoid numerical precision errors outside [-1, 1]
    cosine = np.clip(cosine, -1.0, 1.0)
    angle_rad = np.arccos(cosine)
    return float(np.degrees(angle_rad))


def calculate_angle_to_vertical(
    p_top: Tuple[float, float],
    p_bottom: Tuple[float, float],
) -> float:
    """Calculates the angle in degrees between the line (p_bottom -> p_top)

    and the true vertical axis.
    A perfectly upright vertical posture yields 0 degrees.
    """
    dx = p_top[0] - p_bottom[0]
    dy = p_top[1] - p_bottom[1]

    # In image coordinates, y increases downwards, so vertical upward vector is (0, -1)
    # Vector bottom -> top is (dx, dy)
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        return 0.0

    # Angle relative to vertical
    angle_rad = math.atan2(abs(dx), -dy)
    return float(math.degrees(angle_rad))


def calculate_distance_2d(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
) -> float:
    """Calculates Euclidean distance between two points."""
    return float(math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
