"""
Person tracking and pose estimation module: Follows the selected person across
video frames, maintains robust bounding box tracking, and extracts pose landmarks.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.components.containers import landmark as mp_landmark
import numpy as np


@dataclass
class PoseDetectionResult:
    """Encapsulates the detected landmarks and bounding box for the tracked person."""

    frame_idx: int
    timestamp_s: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h) in full-frame pixels
    image_landmarks: Optional[List[mp_landmark.NormalizedLandmark]]  # Full-frame normalized landmarks
    world_landmarks: Optional[List[mp_landmark.Landmark]]  # 3D world landmarks (meters)
    confidence: float
    is_tracked: bool


class PersonPoseTracker:
    """
    Combines visual object tracking (OpenCV CSRT) with MediaPipe Pose Landmarker
    to isolate and track the user's chosen person across all video frames.
    """

    def __init__(
        self,
        model_path: str = "pose_landmarker.task",
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        pad_ratio_w: float = 0.25,
        pad_ratio_h: float = 0.20,
    ):
        self.model_path = model_path
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.pad_ratio_w = pad_ratio_w
        self.pad_ratio_h = pad_ratio_h

        # OpenCV Tracker
        self.tracker = None
        self.current_bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
        self.smoothed_bbox: Optional[Tuple[float, float, float, float]] = None

        # MediaPipe Landmarker (VIDEO mode for temporal smoothing)
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        self.options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(self.options)

        # Multi-pose fallback detector for full-frame recovery
        self.recovery_options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=4,
            min_pose_detection_confidence=min_detection_confidence,
        )
        self.recovery_landmarker = vision.PoseLandmarker.create_from_options(
            self.recovery_options
        )

    def init_tracker(self, frame: np.ndarray, initial_bbox: Tuple[int, int, int, int]):
        """Initializes the object tracker with the user-selected bounding box."""
        self.current_bbox = initial_bbox
        self.smoothed_bbox = tuple(float(v) for v in initial_bbox)

        # Prefer CSRT for high accuracy; fallback to MIL if CSRT unavailable
        if hasattr(cv2, "TrackerCSRT_create"):
            self.tracker = cv2.TrackerCSRT_create()
        elif hasattr(cv2, "TrackerMIL_create"):
            self.tracker = cv2.TrackerMIL_create()
        else:
            self.tracker = None

        if self.tracker is not None:
            self.tracker.init(frame, initial_bbox)

    def _get_padded_crop(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> Tuple[np.ndarray, int, int, int, int]:
        """Pads and clamps bounding box, then crops frame."""
        h, w = frame.shape[:2]
        bx, by, bw, bh = bbox

        pad_w = int(bw * self.pad_ratio_w)
        pad_h = int(bh * self.pad_ratio_h)

        x1 = max(0, bx - pad_w)
        y1 = max(0, by - pad_h)
        x2 = min(w, bx + bw + pad_w)
        y2 = min(h, by + bh + pad_h)

        crop = frame[y1:y2, x1:x2]
        return crop, x1, y1, x2 - x1, y2 - y1

    def _update_bbox_from_landmarks(
        self,
        full_landmarks: List[mp_landmark.NormalizedLandmark],
        frame_shape: Tuple[int, int],
    ) -> Tuple[int, int, int, int]:
        """Calculates a tight bounding box around the detected person landmarks."""
        h, w = frame_shape
        xs = [lm.x * w for lm in full_landmarks if getattr(lm, "visibility", 1.0) > 0.25]
        ys = [lm.y * h for lm in full_landmarks if getattr(lm, "visibility", 1.0) > 0.25]

        if len(xs) < 8:
            return self.current_bbox

        min_x = max(0, int(min(xs) - 15))
        min_y = max(0, int(min(ys) - 25))
        max_x = min(w, int(max(xs) + 15))
        max_y = min(h, int(max(ys) + 20))

        return (min_x, min_y, max(1, max_x - min_x), max(1, max_y - min_y))

    def _smooth_bbox(
        self, new_bbox: Tuple[int, int, int, int], alpha: float = 0.35
    ) -> Tuple[int, int, int, int]:
        """Applies exponential moving average to stabilize bounding box dimensions."""
        if self.smoothed_bbox is None:
            self.smoothed_bbox = tuple(float(v) for v in new_bbox)
            return new_bbox

        smoothed = [
            alpha * new_bbox[i] + (1.0 - alpha) * self.smoothed_bbox[i]
            for i in range(4)
        ]
        self.smoothed_bbox = tuple(smoothed)
        return (
            int(round(smoothed[0])),
            int(round(smoothed[1])),
            int(round(smoothed[2])),
            int(round(smoothed[3])),
        )

    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp_s: float
    ) -> PoseDetectionResult:
        """
        Processes a single video frame: tracks target person, runs pose estimation,
        and projects landmarks to full frame.
        """
        h, w = frame.shape[:2]
        timestamp_ms = int(timestamp_s * 1000)

        # Step 1: Update visual tracker if available
        tracking_ok = False
        if self.tracker is not None:
            tracking_ok, tracked_box = self.tracker.update(frame)
            if tracking_ok:
                self.current_bbox = (
                    int(tracked_box[0]),
                    int(tracked_box[1]),
                    int(tracked_box[2]),
                    int(tracked_box[3]),
                )

        if self.current_bbox is None:
            self.current_bbox = (0, 0, w, h)

        # Step 2: Crop around current bounding box with padding
        crop, cx, cy, cw, ch = self._get_padded_crop(frame, self.current_bbox)

        detected_pose_landmarks = None
        detected_world_landmarks = None
        confidence = 0.0

        if crop.size > 0 and cw >= 20 and ch >= 20:
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            mp_crop = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_crop)
            result = self.landmarker.detect_for_video(mp_crop, timestamp_ms)

            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                crop_lms = result.pose_landmarks[0]
                world_lms = (
                    result.pose_world_landmarks[0]
                    if result.pose_world_landmarks
                    else None
                )

                # Project crop-normalized coordinates back to full-frame normalized coordinates
                full_frame_lms = []
                visibilities = []
                for lm in crop_lms:
                    pixel_x = cx + lm.x * cw
                    pixel_y = cy + lm.y * ch
                    full_norm_x = pixel_x / w
                    full_norm_y = pixel_y / h

                    full_lm = mp_landmark.NormalizedLandmark(
                        x=float(full_norm_x),
                        y=float(full_norm_y),
                        z=float(lm.z),
                        visibility=float(getattr(lm, "visibility", 1.0)),
                        presence=float(getattr(lm, "presence", 1.0)),
                    )
                    full_frame_lms.append(full_lm)
                    visibilities.append(getattr(lm, "visibility", 1.0))

                detected_pose_landmarks = full_frame_lms
                detected_world_landmarks = world_lms
                confidence = float(np.mean(visibilities)) if visibilities else 0.0

                # Update bounding box from landmarks to keep it centered on target
                raw_new_bbox = self._update_bbox_from_landmarks(
                    full_frame_lms, (h, w)
                )
                self.current_bbox = self._smooth_bbox(raw_new_bbox)

                # Re-anchor the tracker occasionally or after significant shift
                if self.tracker is not None and frame_idx % 15 == 0:
                    try:
                        self.tracker.init(frame, self.current_bbox)
                    except Exception:
                        pass

        # Step 3: Fallback recovery if pose was lost in crop
        if detected_pose_landmarks is None:
            rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_full = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_full)
            rec_result = self.recovery_landmarker.detect(mp_full)

            if rec_result.pose_landmarks:
                # Find pose whose bounding box or centroid is closest to last known bbox
                best_match = None
                best_dist = float("inf")
                target_center_x = self.current_bbox[0] + self.current_bbox[2] / 2.0
                target_center_y = self.current_bbox[1] + self.current_bbox[3] / 2.0

                for p_idx, p_lms in enumerate(rec_result.pose_landmarks):
                    p_xs = [lm.x * w for lm in p_lms]
                    p_ys = [lm.y * h for lm in p_lms]
                    center_x = np.mean(p_xs)
                    center_y = np.mean(p_ys)
                    dist = np.hypot(center_x - target_center_x, center_y - target_center_y)
                    if dist < best_dist:
                        best_dist = dist
                        best_match = (p_idx, p_lms)

                # Accept if within 25% of image diagonal
                max_allowed_dist = 0.25 * np.hypot(w, h)
                if best_match and best_dist < max_allowed_dist:
                    p_idx, p_lms = best_match
                    detected_pose_landmarks = p_lms
                    detected_world_landmarks = (
                        rec_result.pose_world_landmarks[p_idx]
                        if rec_result.pose_world_landmarks
                        else None
                    )
                    confidence = 0.7
                    raw_new_bbox = self._update_bbox_from_landmarks(p_lms, (h, w))
                    self.current_bbox = self._smooth_bbox(raw_new_bbox)
                    if self.tracker is not None:
                        try:
                            self.tracker.init(frame, self.current_bbox)
                        except Exception:
                            pass

        return PoseDetectionResult(
            frame_idx=frame_idx,
            timestamp_s=timestamp_s,
            bbox=self.current_bbox,
            image_landmarks=detected_pose_landmarks,
            world_landmarks=detected_world_landmarks,
            confidence=confidence,
            is_tracked=(detected_pose_landmarks is not None),
        )

    def close(self):
        """Releases MediaPipe resources."""
        if hasattr(self, "landmarker") and self.landmarker:
            self.landmarker.close()
        if hasattr(self, "recovery_landmarker") and self.recovery_landmarker:
            self.recovery_landmarker.close()
