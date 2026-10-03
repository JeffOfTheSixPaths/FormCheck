"""Landmark indices, anatomical enum mappings, and skeleton connections."""

from enum import IntEnum
from typing import List, Tuple


class PoseLandmark(IntEnum):
    """MediaPipe 33 pose landmark indices."""

    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


# MediaPipe's 33 pose landmarks connections.
# Each tuple connects two landmark indexes.
POSE_CONNECTIONS: List[Tuple[int, int]] = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Torso
    (11, 12),
    (11, 23),
    (12, 24),
    (23, 24),
    # Left Arm
    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21),
    # Right Arm
    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22),
    # Left Leg
    (23, 25), (25, 27),
    (27, 29), (29, 31),
    # Right Leg
    (24, 26), (26, 28),
    (28, 30), (30, 32),
]
