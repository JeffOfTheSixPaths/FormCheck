"""MediaPipe Pose Landmarker detector and overlay visualizer."""

import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np

from pose.landmarks import POSE_CONNECTIONS
from services.settings import (
    MIN_POSE_DETECTION_CONFIDENCE,
    MIN_POSE_PRESENCE_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
    MODEL_PATH,
    MODEL_URL,
    NUM_POSES,
)

logger = logging.getLogger(__name__)


def ensure_model_file(model_path: Path = MODEL_PATH, url: str = MODEL_URL) -> str:
    """Verifies that the pose landmarker model exists locally, downloading if necessary."""
    path_str = str(model_path)
    if not os.path.exists(path_str):
        logger.info("Pose model not found at %s. Downloading...", path_str)
        print(f"Downloading pose estimation model to {path_str}...")

        def _reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = min(100, int(count * block_size * 100 / total_size))
                downloaded_mb = count * block_size / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                sys.stdout.write(f"\rDownloading model: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, path_str, reporthook=_reporthook)
        print("\nModel download finished successfully.")
    return path_str


class PoseDetector:
    """Encapsulates MediaPipe Tasks Vision PoseLandmarker."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        num_poses: int = NUM_POSES,
        min_detection_confidence: float = MIN_POSE_DETECTION_CONFIDENCE,
        min_presence_confidence: float = MIN_POSE_PRESENCE_CONFIDENCE,
        min_tracking_confidence: float = MIN_TRACKING_CONFIDENCE,
    ) -> None:
        target_path = model_path if model_path is not None else MODEL_PATH
        resolved_model_path = ensure_model_file(target_path)

        base_options = python.BaseOptions(model_asset_path=resolved_model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=num_poses,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    def detect(self, rgb_frame: np.ndarray, timestamp_ms: int) -> Any:
        """Runs pose estimation on an RGB frame at the given timestamp."""
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame,
        )
        return self._landmarker.detect_for_video(mp_image, timestamp_ms)

    def close(self) -> None:
        """Closes the underlying landmarker."""
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None

    @staticmethod
    def draw_pose(
        frame: np.ndarray,
        landmarks: Any,
        landmark_color: Tuple[int, int, int] = (0, 255, 0),
        connection_color: Tuple[int, int, int] = (255, 0, 0),
        joint_highlights: Optional[Dict[int, Tuple[int, int, int]]] = None,
    ) -> None:
        """Draws skeleton connections and landmark points on an image in-place.

        Preserves existing visualization aesthetics from pose.py while allowing
        custom joint colors for form feedback alerts.
        """
        height, width = frame.shape[:2]

        # Draw connections
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx >= len(landmarks) or end_idx >= len(landmarks):
                continue

            start = landmarks[start_idx]
            end = landmarks[end_idx]

            x1 = int(start.x * width)
            y1 = int(start.y * height)
            x2 = int(end.x * width)
            y2 = int(end.y * height)

            # Determine connection color
            conn_col = connection_color
            if joint_highlights:
                if start_idx in joint_highlights:
                    conn_col = joint_highlights[start_idx]
                elif end_idx in joint_highlights:
                    conn_col = joint_highlights[end_idx]

            cv2.line(frame, (x1, y1), (x2, y2), conn_col, 2)

        # Draw landmarks
        for idx, landmark in enumerate(landmarks):
            x = int(landmark.x * width)
            y = int(landmark.y * height)

            if 0 <= x < width and 0 <= y < height:
                pt_color = landmark_color
                radius = 5
                if joint_highlights and idx in joint_highlights:
                    pt_color = joint_highlights[idx]
                    radius = 7

                cv2.circle(frame, (x, y), radius, pt_color, -1)
                # Subtle border around landmark points
                cv2.circle(frame, (x, y), radius + 1, (255, 255, 255), 1)
