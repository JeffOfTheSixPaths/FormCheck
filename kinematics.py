"""
Kinematics module for calculating joint angles and statistical metrics
(Expected Value, Variance, Standard Deviation, Range of Motion) from pose landmarks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


# MediaPipe Pose Landmark Indices
class LandmarkIndex:
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


# Joint definitions: (Point A, Vertex B, Point C) -> Angle at B between segment BA and segment BC
# BA is the proximal segment, BC is the distal segment
JOINT_DEFINITIONS: Dict[str, Tuple[int, int, int, str]] = {
    # Lower Body Joints
    "left_knee": (
        LandmarkIndex.LEFT_HIP,
        LandmarkIndex.LEFT_KNEE,
        LandmarkIndex.LEFT_ANKLE,
        "Left Knee (Femur & Shin)",
    ),
    "right_knee": (
        LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.RIGHT_KNEE,
        LandmarkIndex.RIGHT_ANKLE,
        "Right Knee (Femur & Shin)",
    ),
    "left_hip": (
        LandmarkIndex.LEFT_SHOULDER,
        LandmarkIndex.LEFT_HIP,
        LandmarkIndex.LEFT_KNEE,
        "Left Hip (Torso & Femur)",
    ),
    "right_hip": (
        LandmarkIndex.RIGHT_SHOULDER,
        LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.RIGHT_KNEE,
        "Right Hip (Torso & Femur)",
    ),
    "left_pelvis_femur": (
        LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.LEFT_HIP,
        LandmarkIndex.LEFT_KNEE,
        "Left Pelvis-Femur (Abduction)",
    ),
    "right_pelvis_femur": (
        LandmarkIndex.LEFT_HIP,
        LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.RIGHT_KNEE,
        "Right Pelvis-Femur (Abduction)",
    ),
    "left_ankle": (
        LandmarkIndex.LEFT_KNEE,
        LandmarkIndex.LEFT_ANKLE,
        LandmarkIndex.LEFT_FOOT_INDEX,
        "Left Ankle (Shin & Foot)",
    ),
    "right_ankle": (
        LandmarkIndex.RIGHT_KNEE,
        LandmarkIndex.RIGHT_ANKLE,
        LandmarkIndex.RIGHT_FOOT_INDEX,
        "Right Ankle (Shin & Foot)",
    ),
    # Upper Body Joints
    "left_elbow": (
        LandmarkIndex.LEFT_SHOULDER,
        LandmarkIndex.LEFT_ELBOW,
        LandmarkIndex.LEFT_WRIST,
        "Left Elbow (Arm & Forearm)",
    ),
    "right_elbow": (
        LandmarkIndex.RIGHT_SHOULDER,
        LandmarkIndex.RIGHT_ELBOW,
        LandmarkIndex.RIGHT_WRIST,
        "Right Elbow (Arm & Forearm)",
    ),
    "left_shoulder": (
        LandmarkIndex.LEFT_HIP,
        LandmarkIndex.LEFT_SHOULDER,
        LandmarkIndex.LEFT_ELBOW,
        "Left Shoulder (Torso & Arm)",
    ),
    "right_shoulder": (
        LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.RIGHT_SHOULDER,
        LandmarkIndex.RIGHT_ELBOW,
        "Right Shoulder (Torso & Arm)",
    ),
}


def calculate_angle_3d(
    a: np.ndarray, b: np.ndarray, c: np.ndarray
) -> Optional[float]:
    """
    Calculates the 3D interior angle at vertex b between vectors (a - b) and (c - b).
    Returns angle in degrees [0, 180], or None if inputs are degenerate.
    """
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return None

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = np.clip(cosine, -1.0, 1.0)
    angle_deg = float(np.degrees(np.arccos(cosine)))
    return angle_deg


def calculate_trunk_angle(
    left_shoulder: np.ndarray,
    right_shoulder: np.ndarray,
    left_hip: np.ndarray,
    right_hip: np.ndarray,
) -> Optional[float]:
    """
    Calculates torso/trunk inclination angle relative to vertical axis (upward [0, -1, 0]).
    0° = perfectly upright vertical torso.
    """
    mid_shoulder = (left_shoulder + right_shoulder) / 2.0
    mid_hip = (left_hip + right_hip) / 2.0
    torso_vec = mid_shoulder - mid_hip  # Points upward from hip to shoulder
    norm = np.linalg.norm(torso_vec)
    if norm < 1e-6:
        return None

    # In MediaPipe world coordinates:
    # Y is negative upward, positive downward.
    # So upward vertical unit vector is [0, -1, 0]
    vertical_up = np.array([0.0, -1.0, 0.0])
    cosine = np.dot(torso_vec, vertical_up) / norm
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


@dataclass
class JointStats:
    """Statistical summary of a joint angle across recorded video frames."""

    joint_key: str
    name: str
    count: int
    expected_value: float  # Mean (E[X])
    variance: float  # Var(X) = sigma^2
    std_dev: float  # sigma = sqrt(variance)
    min_angle: float
    max_angle: float
    range_of_motion: float  # max - min
    median: float
    q25: float
    q75: float


class KinematicTracker:
    """
    Records joint angles across video frames and computes statistics
    (Expected value, Variance, Standard Deviation, Range of Motion).
    """

    def __init__(self, min_visibility: float = 0.5):
        self.min_visibility = min_visibility
        # Time series: {joint_key: [(frame_idx, timestamp_s, angle_deg), ...]}
        self.history: Dict[str, List[Tuple[int, float, float]]] = {
            key: [] for key in JOINT_DEFINITIONS
        }
        self.history["trunk_inclination"] = []
        self.frame_count = 0

    def process_frame(
        self,
        frame_idx: int,
        timestamp_s: float,
        world_landmarks: Optional[List],
        image_landmarks: Optional[List],
    ) -> Dict[str, Optional[float]]:
        """
        Calculates joint angles for the current frame and records them.
        Returns a dictionary mapping joint keys to their current angles in degrees.
        """
        current_angles: Dict[str, Optional[float]] = {}
        self.frame_count = max(self.frame_count, frame_idx + 1)

        if not world_landmarks and not image_landmarks:
            for k in self.history:
                current_angles[k] = None
            return current_angles

        # Extract landmark 3D positions if available (otherwise fallback to 2D image coords)
        # Using world landmarks provides metric 3D angles invariant to camera viewpoint.
        use_world = world_landmarks is not None and len(world_landmarks) >= 33
        target_lms = world_landmarks if use_world else image_landmarks

        points: Dict[int, np.ndarray] = {}
        visibilities: Dict[int, float] = {}

        for i, lm in enumerate(target_lms):
            points[i] = np.array([lm.x, lm.y, getattr(lm, "z", 0.0)], dtype=np.float64)
            # Visibility or presence
            vis = getattr(lm, "visibility", 1.0)
            if vis is None:
                vis = 1.0
            visibilities[i] = vis

        # Compute each standard joint angle
        for joint_key, (idx_a, idx_b, idx_c, _) in JOINT_DEFINITIONS.items():
            if (
                idx_a in points
                and idx_b in points
                and idx_c in points
                and visibilities.get(idx_a, 1.0) >= self.min_visibility
                and visibilities.get(idx_b, 1.0) >= self.min_visibility
                and visibilities.get(idx_c, 1.0) >= self.min_visibility
            ):
                angle = calculate_angle_3d(points[idx_a], points[idx_b], points[idx_c])
            else:
                angle = None

            current_angles[joint_key] = angle
            if angle is not None:
                self.history[joint_key].append((frame_idx, timestamp_s, angle))

        # Compute trunk inclination
        trunk_idxs = [
            LandmarkIndex.LEFT_SHOULDER,
            LandmarkIndex.RIGHT_SHOULDER,
            LandmarkIndex.LEFT_HIP,
            LandmarkIndex.RIGHT_HIP,
        ]
        if all(
            idx in points and visibilities.get(idx, 1.0) >= self.min_visibility
            for idx in trunk_idxs
        ):
            trunk_angle = calculate_trunk_angle(
                points[LandmarkIndex.LEFT_SHOULDER],
                points[LandmarkIndex.RIGHT_SHOULDER],
                points[LandmarkIndex.LEFT_HIP],
                points[LandmarkIndex.RIGHT_HIP],
            )
        else:
            trunk_angle = None

        current_angles["trunk_inclination"] = trunk_angle
        if trunk_angle is not None:
            self.history["trunk_inclination"].append(
                (frame_idx, timestamp_s, trunk_angle)
            )

        return current_angles

    def get_running_stats(self, joint_key: str) -> Optional[Tuple[float, float]]:
        """
        Returns (expected_value, variance) up to current frame for the given joint.
        """
        series = self.history.get(joint_key, [])
        if not series:
            return None
        angles = [a for _, _, a in series]
        mean = float(np.mean(angles))
        var = float(np.var(angles))
        return mean, var

    def compute_all_stats(self) -> Dict[str, JointStats]:
        """
        Computes final statistics (Expected Value, Variance, Std Dev, Min, Max, ROM, Quartiles)
        for all tracked joint angles.
        """
        stats: Dict[str, JointStats] = {}

        # Joint name mapping
        names = {k: v[3] for k, v in JOINT_DEFINITIONS.items()}
        names["trunk_inclination"] = "Trunk Inclination (Torso Lean)"

        for key, series in self.history.items():
            if not series:
                continue

            angles = np.array([a for _, _, a in series], dtype=np.float64)
            count = len(angles)
            if count == 0:
                continue

            mean = float(np.mean(angles))
            variance = float(np.var(angles))  # Var(X) = E[(X - E[X])^2]
            std_dev = float(np.std(angles))
            min_ang = float(np.min(angles))
            max_ang = float(np.max(angles))
            rom = max_ang - min_ang
            median = float(np.median(angles))
            q25 = float(np.percentile(angles, 25))
            q75 = float(np.percentile(angles, 75))

            stats[key] = JointStats(
                joint_key=key,
                name=names.get(key, key),
                count=count,
                expected_value=mean,
                variance=variance,
                std_dev=std_dev,
                min_angle=min_ang,
                max_angle=max_ang,
                range_of_motion=rom,
                median=median,
                q25=q25,
                q75=q75,
            )

        return stats
