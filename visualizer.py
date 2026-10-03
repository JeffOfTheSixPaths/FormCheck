"""
Visualizer module: Renders skeletal tracking, joint angle callouts, angle arcs,
and a real-time HUD telemetry panel onto video frames.
"""

from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from kinematics import LandmarkIndex, JOINT_DEFINITIONS


# Bone connections grouped by body region
SKELETON_CONNECTIONS = {
    # Left Arm (Cyan / Light Blue)
    "left_arm": [(11, 13), (13, 15), (15, 17), (15, 19), (15, 21)],
    # Right Arm (Yellow / Amber)
    "right_arm": [(12, 14), (14, 16), (16, 18), (16, 20), (16, 22)],
    # Left Leg (Cyan / Light Blue)
    "left_leg": [(23, 25), (25, 27), (27, 29), (29, 31), (27, 31)],
    # Right Leg (Yellow / Amber)
    "right_leg": [(24, 26), (26, 28), (28, 30), (30, 32), (28, 32)],
    # Torso (Green)
    "torso": [(11, 12), (11, 23), (12, 24), (23, 24)],
    # Face (White / Gray)
    "face": [(0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10)],
}

COLOR_PALETTE = {
    "left_arm": (255, 200, 0),      # Cyan-ish blue in BGR
    "right_arm": (0, 200, 255),     # Yellow / Gold
    "left_leg": (255, 180, 50),     # Bright blue
    "right_leg": (50, 220, 255),    # Bright yellow/orange
    "torso": (0, 255, 120),         # Vibrant green
    "face": (200, 200, 200),        # Light gray
    "joint_dot": (255, 255, 255),   # White
    "hud_bg": (20, 22, 28),         # Dark slate
    "hud_border": (60, 70, 85),
    "hud_accent": (0, 255, 180),
}


class PoseVisualizer:
    """
    Renders pose skeleton, joint angles, tracking bounding box, and real-time statistics HUD.
    """

    def __init__(self, show_hud: bool = True, show_joint_labels: bool = True):
        self.show_hud = show_hud
        self.show_joint_labels = show_joint_labels

    def draw_skeleton(
        self,
        frame: np.ndarray,
        landmarks: List,
        visibility_threshold: float = 0.4,
    ):
        """Draws color-coded skeleton limbs and joint landmarks."""
        h, w = frame.shape[:2]
        pts = {}

        for idx, lm in enumerate(landmarks):
            vis = getattr(lm, "visibility", 1.0)
            if vis is None or vis >= visibility_threshold:
                px = int(lm.x * w)
                py = int(lm.y * h)
                if 0 <= px < w and 0 <= py < h:
                    pts[idx] = (px, py)

        # Draw bones
        for region, connections in SKELETON_CONNECTIONS.items():
            color = COLOR_PALETTE.get(region, (0, 255, 0))
            for start_idx, end_idx in connections:
                if start_idx in pts and end_idx in pts:
                    cv2.line(frame, pts[start_idx], pts[end_idx], color, 3, cv2.LINE_AA)

        # Draw landmark joints
        for idx, pt in pts.items():
            # Highlight key joints
            if idx in [11, 12, 13, 14, 23, 24, 25, 26, 27, 28]:
                cv2.circle(frame, pt, 6, (0, 0, 255), -1, cv2.LINE_AA)  # Red outer
                cv2.circle(frame, pt, 4, (255, 255, 255), -1, cv2.LINE_AA)  # White inner
            else:
                cv2.circle(frame, pt, 4, (0, 255, 120), -1, cv2.LINE_AA)

    def draw_joint_callouts(
        self,
        frame: np.ndarray,
        landmarks: List,
        current_angles: Dict[str, Optional[float]],
    ):
        """Displays numeric angle callouts directly near the respective joints."""
        h, w = frame.shape[:2]

        callout_map = [
            ("left_knee", LandmarkIndex.LEFT_KNEE, "L Knee", (255, 180, 50)),
            ("right_knee", LandmarkIndex.RIGHT_KNEE, "R Knee", (50, 220, 255)),
            ("left_hip", LandmarkIndex.LEFT_HIP, "L Hip", (255, 180, 50)),
            ("right_hip", LandmarkIndex.RIGHT_HIP, "R Hip", (50, 220, 255)),
            ("left_ankle", LandmarkIndex.LEFT_ANKLE, "L Ankle", (255, 180, 50)),
            ("right_ankle", LandmarkIndex.RIGHT_ANKLE, "R Ankle", (50, 220, 255)),
        ]

        for key, joint_idx, label, color in callout_map:
            angle = current_angles.get(key)
            if angle is None or joint_idx >= len(landmarks):
                continue

            lm = landmarks[joint_idx]
            vis = getattr(lm, "visibility", 1.0)
            if vis is not None and vis < 0.35:
                continue

            jx = int(lm.x * w)
            jy = int(lm.y * h)

            text = f"{label}: {angle:.1f}°"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)

            # Offset tag position
            offset_x = 15 if "right" in key.lower() else -tw - 25
            tx = np.clip(jx + offset_x, 5, w - tw - 15)
            ty = np.clip(jy - 5, th + 10, h - 10)

            # Badge background
            cv2.rectangle(
                frame,
                (int(tx - 4), int(ty - th - 4)),
                (int(tx + tw + 4), int(ty + 4)),
                (20, 20, 20),
                -1,
            )
            cv2.rectangle(
                frame,
                (int(tx - 4), int(ty - th - 4)),
                (int(tx + tw + 4), int(ty + 4)),
                color,
                1,
            )
            cv2.putText(
                frame,
                text,
                (int(tx), int(ty)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    def draw_tracking_box(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        is_tracked: bool = True,
    ):
        """Draws the target bounding box with tracking status."""
        bx, by, bw, bh = bbox
        color = (0, 255, 0) if is_tracked else (0, 165, 255)
        status_text = "TARGET [LOCKED]" if is_tracked else "TARGET [SEARCHING]"

        # Draw corner brackets for a sleek tech HUD appearance
        corner_len = min(25, bw // 4, bh // 4)
        thickness = 2

        # Top-left
        cv2.line(frame, (bx, by), (bx + corner_len, by), color, thickness)
        cv2.line(frame, (bx, by), (bx, by + corner_len), color, thickness)
        # Top-right
        cv2.line(frame, (bx + bw, by), (bx + bw - corner_len, by), color, thickness)
        cv2.line(frame, (bx + bw, by), (bx + bw, by + corner_len), color, thickness)
        # Bottom-left
        cv2.line(frame, (bx, by + bh), (bx + corner_len, by + bh), color, thickness)
        cv2.line(frame, (bx, by + bh), (bx, by + bh - corner_len), color, thickness)
        # Bottom-right
        cv2.line(frame, (bx + bw, by + bh), (bx + bw - corner_len, by + bh), color, thickness)
        cv2.line(frame, (bx + bw, by + bh), (bx + bw, by + bh - corner_len), color, thickness)

        # Thin bounding rectangle
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 1)

        # Tag label
        (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y = max(th + 5, by - 5)
        cv2.rectangle(
            frame,
            (bx, tag_y - th - 4),
            (bx + tw + 8, tag_y + 4),
            (20, 20, 20),
            -1,
        )
        cv2.putText(
            frame,
            status_text,
            (bx + 4, tag_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    def draw_hud(
        self,
        frame: np.ndarray,
        frame_idx: int,
        total_frames: int,
        fps: float,
        current_angles: Dict[str, Optional[float]],
        kinematic_tracker,
    ):
        """Draws semi-transparent HUD overlay with live joint angles, Expected Value, and Variance."""
        h, w = frame.shape[:2]

        hud_w = 440
        hud_h = 320
        hud_x = w - hud_w - 20
        hud_y = 20

        # Create semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (hud_x, hud_y),
            (hud_x + hud_w, hud_y + hud_h),
            COLOR_PALETTE["hud_bg"],
            -1,
        )
        cv2.rectangle(
            overlay,
            (hud_x, hud_y),
            (hud_x + hud_w, hud_y + hud_h),
            COLOR_PALETTE["hud_border"],
            2,
        )
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

        # Header Title
        title = "FORMCHECK: KINEMATICS TELEMETRY"
        cv2.putText(
            frame,
            title,
            (hud_x + 15, hud_y + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            COLOR_PALETTE["hud_accent"],
            2,
            cv2.LINE_AA,
        )

        # Progress / FPS info
        progress_pct = ((frame_idx + 1) / total_frames * 100) if total_frames > 0 else 0
        info_str = f"Frame: {frame_idx + 1}/{total_frames} ({progress_pct:.0f}%) | FPS: {fps:.1f}"
        cv2.putText(
            frame,
            info_str,
            (hud_x + 15, hud_y + 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (180, 190, 205),
            1,
            cv2.LINE_AA,
        )

        # Divider line
        cv2.line(
            frame,
            (hud_x + 10, hud_y + 58),
            (hud_x + hud_w - 10, hud_y + 58),
            (60, 70, 85),
            1,
        )

        # Table Column Headers
        # Joint | Current | E[Angle] | Var(Angle)
        headers = ["Joint", "Current", "E[X] (Mean)", "Var(X) (σ²)"]
        col_x = [hud_x + 15, hud_x + 160, hud_x + 245, hud_x + 345]

        for header, cx in zip(headers, col_x):
            cv2.putText(
                frame,
                header,
                (cx, hud_y + 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                (140, 160, 180),
                1,
                cv2.LINE_AA,
            )

        # Selected joints to display in HUD
        display_joints = [
            ("left_knee", "L Knee (Femur-Shin)"),
            ("right_knee", "R Knee (Femur-Shin)"),
            ("left_hip", "L Hip (Torso-Femur)"),
            ("right_hip", "R Hip (Torso-Femur)"),
            ("left_ankle", "L Ankle (Shin-Foot)"),
            ("right_ankle", "R Ankle (Shin-Foot)"),
            ("trunk_inclination", "Trunk Inclination"),
        ]

        row_y = hud_y + 98
        for key, display_name in display_joints:
            cur_angle = current_angles.get(key)
            stats = kinematic_tracker.get_running_stats(key)

            # Column 1: Joint Name
            cv2.putText(
                frame,
                display_name,
                (col_x[0], row_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (220, 230, 240),
                1,
                cv2.LINE_AA,
            )

            # Column 2: Current Angle
            if cur_angle is not None:
                cur_str = f"{cur_angle:5.1f}°"
                cur_color = (0, 255, 255)
            else:
                cur_str = "  --  "
                cur_color = (120, 120, 120)

            cv2.putText(
                frame,
                cur_str,
                (col_x[1], row_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                cur_color,
                1,
                cv2.LINE_AA,
            )

            # Column 3: Expected Value (Running Mean)
            if stats is not None:
                mean_str = f"{stats[0]:5.1f}°"
                mean_color = (255, 255, 255)
            else:
                mean_str = "  --  "
                mean_color = (120, 120, 120)

            cv2.putText(
                frame,
                mean_str,
                (col_x[2], row_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                mean_color,
                1,
                cv2.LINE_AA,
            )

            # Column 4: Variance (Running Var)
            if stats is not None:
                var_str = f"{stats[1]:6.1f}°²"
                var_color = (100, 220, 255)
            else:
                var_str = "   --   "
                var_color = (120, 120, 120)

            cv2.putText(
                frame,
                var_str,
                (col_x[3], row_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                var_color,
                1,
                cv2.LINE_AA,
            )

            row_y += 24

        # Footer note
        footer_text = "Press 'Q' to finish analysis | Press Space to pause"
        cv2.putText(
            frame,
            footer_text,
            (hud_x + 15, hud_y + hud_h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.36,
            (130, 140, 155),
            1,
            cv2.LINE_AA,
        )

    def render(
        self,
        frame: np.ndarray,
        detection_result,
        current_angles: Dict[str, Optional[float]],
        kinematic_tracker,
        frame_idx: int,
        total_frames: int,
        fps: float,
    ) -> np.ndarray:
        """Draws all annotations onto a copy of the frame and returns it."""
        output = frame.copy()

        # 1. Bounding box
        if detection_result.bbox is not None:
            self.draw_tracking_box(
                output, detection_result.bbox, detection_result.is_tracked
            )

        # 2. Skeleton & Joint callouts
        if detection_result.image_landmarks:
            self.draw_skeleton(output, detection_result.image_landmarks)
            if self.show_joint_labels:
                self.draw_joint_callouts(
                    output, detection_result.image_landmarks, current_angles
                )

        # 3. HUD telemetry panel
        if self.show_hud:
            self.draw_hud(
                output,
                frame_idx,
                total_frames,
                fps,
                current_angles,
                kinematic_tracker,
            )

        return output
