"""Biomechanical comparison engine: computes joint angles, segment variances (Arms, Shoulders, Hips, Legs),
and generates normalized direct skeleton overlays between user and pro athletes."""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from kinematics import (
    JOINT_DEFINITIONS,
    LandmarkIndex,
    calculate_angle_3d,
    calculate_trunk_angle,
)
from pose.detector import PoseDetector

logger = logging.getLogger(__name__)


@dataclass
class SegmentVariance:
    """Biomechanical variance and deviation metrics for a specific body region."""
    name: str
    variance: float = 0.0          # Angular variance (sigma^2)
    std_dev: float = 0.0           # Standard deviation
    mean_delta_deg: float = 0.0    # Absolute angular difference against pro
    match_percentage: float = 100.0# 0 - 100% alignment score
    joint_details: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class ComparisonMetrics:
    """Consolidated variance metrics comparing user movement to pro athlete form."""
    arms: SegmentVariance
    shoulders: SegmentVariance
    hips: SegmentVariance
    legs: SegmentVariance
    overall_score: float = 100.0   # Composite biomechanical form score (0-100%)
    primary_coaching_cue: str = "Movement patterns aligned with professional baseline."


class ComparisonEngine:
    """Extracts poses, normalizes skeletal scale, overlays forms, and computes biomechanical variances."""

    def __init__(self) -> None:
        self.detector = PoseDetector()

    def extract_landmarks(self, frame: np.ndarray, timestamp_ms: int = 0) -> Optional[List]:
        """Detects pose landmarks from BGR frame."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.detector.detect(rgb, timestamp_ms)
        if res and res.pose_landmarks and len(res.pose_landmarks) > 0:
            return res.pose_landmarks[0]
        return None

    @staticmethod
    def calculate_angles(landmarks: List) -> Dict[str, float]:
        """Calculates 3D interior angles for all defined joints."""
        coords = {}
        for idx, lm in enumerate(landmarks):
            coords[idx] = np.array([lm.x, lm.y, lm.z])

        angles = {}
        for joint_key, (idx_a, idx_b, idx_c, _) in JOINT_DEFINITIONS.items():
            if idx_a in coords and idx_b in coords and idx_c in coords:
                ang = calculate_angle_3d(coords[idx_a], coords[idx_b], coords[idx_c])
                if ang is not None:
                    angles[joint_key] = float(ang)

        # Trunk angle
        if all(k in coords for k in [11, 12, 23, 24]):
            trunk = calculate_trunk_angle(coords[11], coords[12], coords[23], coords[24])
            if trunk is not None:
                angles["trunk_lean"] = float(trunk)

        # Shoulder line tilt relative to horizontal
        if 11 in coords and 12 in coords:
            dx = coords[12][0] - coords[11][0]
            dy = coords[12][1] - coords[11][1]
            tilt = np.degrees(np.arctan2(dy, dx))
            angles["shoulder_tilt"] = float(abs(tilt))

        # Stance width normalized to hip width
        if all(k in coords for k in [23, 24, 27, 28]):
            hip_w = np.linalg.norm(coords[23] - coords[24])
            ankle_w = np.linalg.norm(coords[27] - coords[28])
            if hip_w > 1e-4:
                angles["stance_ratio"] = float(ankle_w / hip_w)

        return angles

    @classmethod
    def compare_frames(
        cls,
        user_landmarks: Optional[List],
        pro_landmarks: Optional[List],
    ) -> ComparisonMetrics:
        """Convenience method to calculate angles and compute segment variances."""
        user_angles = cls.calculate_angles(user_landmarks) if user_landmarks else {}
        pro_angles = cls.calculate_angles(pro_landmarks) if pro_landmarks else {}
        return cls.compute_variances(user_angles, pro_angles)

    @classmethod
    def compute_variances(
        cls,
        user_angles: Dict[str, float],
        pro_angles: Dict[str, float],
    ) -> ComparisonMetrics:
        """Computes delta and variance for Arms, Shoulders, Hips, and Legs."""

        # 1. Arms (Elbows, Arm Extension)
        arm_joints = ["left_elbow", "right_elbow"]
        arm_deltas = []
        arm_details = {}
        for j in arm_joints:
            u = user_angles.get(j, 160.0)
            p = pro_angles.get(j, 160.0)
            d = abs(u - p)
            arm_deltas.append(d)
            arm_details[j] = {"user": round(u, 1), "pro": round(p, 1), "delta": round(d, 1)}

        arm_mean_delta = float(np.mean(arm_deltas)) if arm_deltas else 0.0
        arm_var = float(np.var(arm_deltas)) if len(arm_deltas) > 1 else 0.0
        arm_score = max(0.0, min(100.0, 100.0 - (arm_mean_delta * 1.8)))
        arms_seg = SegmentVariance(
            name="Arms & Elbows",
            variance=round(arm_var, 2),
            std_dev=round(float(np.sqrt(arm_var)), 2),
            mean_delta_deg=round(arm_mean_delta, 1),
            match_percentage=round(arm_score, 1),
            joint_details=arm_details,
        )

        # 2. Shoulders (Shoulder tilt, Abduction)
        shoulder_joints = ["left_shoulder", "right_shoulder", "shoulder_tilt"]
        sh_deltas = []
        sh_details = {}
        for j in shoulder_joints:
            u = user_angles.get(j, 45.0)
            p = pro_angles.get(j, 45.0)
            d = abs(u - p)
            sh_deltas.append(d)
            sh_details[j] = {"user": round(u, 1), "pro": round(p, 1), "delta": round(d, 1)}

        sh_mean_delta = float(np.mean(sh_deltas)) if sh_deltas else 0.0
        sh_var = float(np.var(sh_deltas)) if len(sh_deltas) > 1 else 0.0
        sh_score = max(0.0, min(100.0, 100.0 - (sh_mean_delta * 2.0)))
        shoulders_seg = SegmentVariance(
            name="Shoulder Axis",
            variance=round(sh_var, 2),
            std_dev=round(float(np.sqrt(sh_var)), 2),
            mean_delta_deg=round(sh_mean_delta, 1),
            match_percentage=round(sh_score, 1),
            joint_details=sh_details,
        )

        # 3. Hips (Hip Flexion, Pelvic Abduction, Torso Lean)
        hip_joints = ["left_hip", "right_hip", "trunk_lean"]
        hip_deltas = []
        hip_details = {}
        for j in hip_joints:
            u = user_angles.get(j, 90.0)
            p = pro_angles.get(j, 90.0)
            d = abs(u - p)
            hip_deltas.append(d)
            hip_details[j] = {"user": round(u, 1), "pro": round(p, 1), "delta": round(d, 1)}

        hip_mean_delta = float(np.mean(hip_deltas)) if hip_deltas else 0.0
        hip_var = float(np.var(hip_deltas)) if len(hip_deltas) > 1 else 0.0
        hip_score = max(0.0, min(100.0, 100.0 - (hip_mean_delta * 1.6)))
        hips_seg = SegmentVariance(
            name="Hips & Core",
            variance=round(hip_var, 2),
            std_dev=round(float(np.sqrt(hip_var)), 2),
            mean_delta_deg=round(hip_mean_delta, 1),
            match_percentage=round(hip_score, 1),
            joint_details=hip_details,
        )

        # 4. Legs (Knees, Ankles, Stance)
        leg_joints = ["left_knee", "right_knee", "left_ankle", "right_ankle"]
        leg_deltas = []
        leg_details = {}
        for j in leg_joints:
            u = user_angles.get(j, 120.0)
            p = pro_angles.get(j, 120.0)
            d = abs(u - p)
            leg_deltas.append(d)
            leg_details[j] = {"user": round(u, 1), "pro": round(p, 1), "delta": round(d, 1)}

        leg_mean_delta = float(np.mean(leg_deltas)) if leg_deltas else 0.0
        leg_var = float(np.var(leg_deltas)) if len(leg_deltas) > 1 else 0.0
        leg_score = max(0.0, min(100.0, 100.0 - (leg_mean_delta * 1.5)))
        legs_seg = SegmentVariance(
            name="Legs & Stance",
            variance=round(leg_var, 2),
            std_dev=round(float(np.sqrt(leg_var)), 2),
            mean_delta_deg=round(leg_mean_delta, 1),
            match_percentage=round(leg_score, 1),
            joint_details=leg_details,
        )

        # Overall Form Score
        overall = (arm_score * 0.25) + (sh_score * 0.25) + (hip_score * 0.25) + (leg_score * 0.25)

        # Generate actionable cue
        cues = []
        if leg_mean_delta > 15:
            cues.append("Adjust knee flexion to match pro depth.")
        if hip_mean_delta > 15:
            cues.append("Correct hip hinge and maintain upright torso posture.")
        if sh_mean_delta > 15:
            cues.append("Square shoulder alignment with athletic baseline.")
        if arm_mean_delta > 15:
            cues.append("Refine arm extension and elbow angle.")

        cue = " | ".join(cues) if cues else "Movement mechanics closely mirror professional athlete form."

        return ComparisonMetrics(
            arms=arms_seg,
            shoulders=shoulders_seg,
            hips=hips_seg,
            legs=legs_seg,
            overall_score=round(overall, 1),
            primary_coaching_cue=cue,
        )

    @classmethod
    def render_direct_overlay(
        cls,
        base_frame: np.ndarray,
        pro_landmarks: Optional[List],
        user_landmarks: Optional[List],
        metrics: Optional[ComparisonMetrics] = None,
        pro_label: str = "REFERENCE BENCHMARK",
        user_label: str = "YOUR ATHLETIC FORM",
    ) -> np.ndarray:
        """
        Renders the Reference/Pro skeleton and User skeleton directly onto the same frame.
        Anchored centrally Right Shoulder to Right Shoulder (Landmark 12) with proportional torso scaling.
        Pro/Ref skeleton: Neon Cyan (#00f0ff)
        User skeleton: Normalized in scale & center, rendered in Coral Rose (#f43f5e)
        Disparity vectors: Orange/red connecting lines highlighting form breaks.
        """
        canvas = base_frame.copy()
        h, w = canvas.shape[:2]

        def _get_coords(lm):
            if isinstance(lm, dict):
                vis = lm.get("visibility", lm.get("v", 1.0))
                if vis is None or vis > 0.30:
                    return float(lm["x"] * w), float(lm["y"] * h)
            elif lm is not None:
                vis = getattr(lm, "visibility", 1.0)
                if vis is None or vis > 0.30:
                    return float(lm.x * w), float(lm.y * h)
            return None

        # 1. Draw Reference/Pro Skeleton (Neon Cyan)
        pro_pts = {}
        if pro_landmarks:
            for idx, lm in enumerate(pro_landmarks):
                coords = _get_coords(lm)
                if coords:
                    pro_pts[idx] = (int(coords[0]), int(coords[1]))

            cls._draw_skeleton_lines(canvas, pro_pts, color_bgr=(255, 240, 0), thickness=3)
            for pt in pro_pts.values():
                cv2.circle(canvas, pt, 5, (255, 240, 0), -1, cv2.LINE_AA)

        # 2. Normalize and Draw User Skeleton (Coral Rose) anchored Right Shoulder to Right Shoulder
        user_pts = {}
        if user_landmarks:
            raw_user_pts = {}
            for idx, lm in enumerate(user_landmarks):
                coords = _get_coords(lm)
                if coords:
                    raw_user_pts[idx] = coords

            # Right Shoulder to Right Shoulder Central Anchor (Landmark 12)
            if pro_pts and 12 in pro_pts and 12 in raw_user_pts:
                p_r_sho = pro_pts[12]
                u_r_sho = raw_user_pts[12]

                # Compute anatomical scale factor from torso (right shoulder to right hip 12 -> 24)
                scale = 1.0
                if 24 in pro_pts and 24 in raw_user_pts:
                    p_torso = np.hypot(p_r_sho[0] - pro_pts[24][0], p_r_sho[1] - pro_pts[24][1])
                    u_torso = np.hypot(u_r_sho[0] - raw_user_pts[24][0], u_r_sho[1] - raw_user_pts[24][1])
                    if u_torso > 12:
                        scale = max(0.5, min(2.0, p_torso / u_torso))
                elif 11 in pro_pts and 11 in raw_user_pts:
                    p_span = np.hypot(p_r_sho[0] - pro_pts[11][0], p_r_sho[1] - pro_pts[11][1])
                    u_span = np.hypot(u_r_sho[0] - raw_user_pts[11][0], u_r_sho[1] - raw_user_pts[11][1])
                    if u_span > 12:
                        scale = max(0.5, min(2.0, p_span / u_span))

                for idx, (ux, uy) in raw_user_pts.items():
                    norm_x = int(p_r_sho[0] + (ux - u_r_sho[0]) * scale)
                    norm_y = int(p_r_sho[1] + (uy - u_r_sho[1]) * scale)
                    user_pts[idx] = (norm_x, norm_y)

            elif pro_pts and 11 in pro_pts and 11 in raw_user_pts:
                # Fallback to Left Shoulder anchor (Landmark 11)
                p_l_sho = pro_pts[11]
                u_l_sho = raw_user_pts[11]
                scale = 1.0
                if 23 in pro_pts and 23 in raw_user_pts:
                    p_torso = np.hypot(p_l_sho[0] - pro_pts[23][0], p_l_sho[1] - pro_pts[23][1])
                    u_torso = np.hypot(u_l_sho[0] - raw_user_pts[23][0], u_l_sho[1] - raw_user_pts[23][1])
                    if u_torso > 12:
                        scale = max(0.5, min(2.0, p_torso / u_torso))
                for idx, (ux, uy) in raw_user_pts.items():
                    norm_x = int(p_l_sho[0] + (ux - u_l_sho[0]) * scale)
                    norm_y = int(p_l_sho[1] + (uy - u_l_sho[1]) * scale)
                    user_pts[idx] = (norm_x, norm_y)
            else:
                for idx, (ux, uy) in raw_user_pts.items():
                    user_pts[idx] = (int(ux), int(uy))

            # Draw User Skeleton (BGR Coral/Rose: 94, 63, 244)
            cls._draw_skeleton_lines(canvas, user_pts, color_bgr=(94, 63, 244), thickness=2)
            for pt in user_pts.values():
                cv2.circle(canvas, pt, 4, (94, 63, 244), -1, cv2.LINE_AA)

            # Draw Disparity Vectors connecting key deviating joints
            key_joints = [13, 14, 15, 16, 25, 26, 27, 28]  # Elbows, wrists, knees, ankles
            for kj in key_joints:
                if kj in pro_pts and kj in user_pts:
                    p1 = pro_pts[kj]
                    p2 = user_pts[kj]
                    dist = np.hypot(p1[0] - p2[0], p1[1] - p2[1])
                    if dist > 18:
                        cv2.line(canvas, p1, p2, (0, 165, 255), 1, cv2.LINE_AA)

        # 3. Legend Badge (Top Left)
        cv2.rectangle(canvas, (16, 16), (280, 72), (9, 9, 11), -1)
        cv2.rectangle(canvas, (16, 16), (280, 72), (50, 50, 56), 1)

        # Ref legend line
        cv2.line(canvas, (28, 36), (56, 36), (255, 240, 0), 3)
        cv2.putText(canvas, pro_label, (66, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 240, 0), 1, cv2.LINE_AA)

        # User legend line
        cv2.line(canvas, (28, 54), (56, 54), (94, 63, 244), 3)
        cv2.putText(canvas, user_label, (66, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (94, 63, 244), 1, cv2.LINE_AA)

        return canvas

    @staticmethod
    def _draw_skeleton_lines(frame: np.ndarray, pts: Dict[int, Tuple[int, int]], color_bgr: Tuple[int, int, int], thickness: int = 2):
        """Draws standard skeletal linkages."""
        connections = [
            (11, 12), (11, 13), (13, 15), # L Arm
            (12, 14), (14, 16),          # R Arm
            (11, 23), (12, 24), (23, 24), # Torso
            (23, 25), (25, 27),          # L Leg
            (24, 26), (26, 28),          # R Leg
        ]
        for a, b in connections:
            if a in pts and b in pts:
                cv2.line(frame, pts[a], pts[b], color_bgr, thickness, cv2.LINE_AA)


comparison_engine = ComparisonEngine()
