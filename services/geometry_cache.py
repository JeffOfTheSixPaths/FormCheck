"""Pre-computed Skeletal Geometry Storage Service.

Extracts, serializes, and caches frame-by-frame 3D skeletal landmarks and joint angles
to disk for each video clip. Allows instantaneous video comparison and overlay rendering
without running real-time neural network pose estimation during playback or scrubbing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import cv2
import numpy as np

from kinematics import JOINT_DEFINITIONS, calculate_angle_3d, calculate_trunk_angle
from pose.detector import PoseDetector
from services.settings import BASE_DIR

logger = logging.getLogger(__name__)

GEOMETRY_DIR = BASE_DIR / "server_storage" / "geometry"
GEOMETRY_DIR.mkdir(parents=True, exist_ok=True)


class GeometryCache:
    """Manages disk persistence and in-memory caching of video skeletal geometry."""

    def __init__(self) -> None:
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self.detector = PoseDetector()

    def _get_cache_path(self, video_path: str) -> Path:
        stem = Path(video_path).stem
        # Use filename stem for human-readable geometry file
        return GEOMETRY_DIR / f"{stem}_geometry.json"

    def has_geometry(self, video_path: str) -> bool:
        """Checks if pre-computed geometry already exists on disk."""
        if not video_path:
            return False
        if str(video_path) in self._memory_cache:
            return True
        return self._get_cache_path(video_path).exists()

    def get_or_compute_geometry(
        self,
        video_path: str,
        initial_bbox: Optional[Tuple[int, int, int, int]] = None,
        start_frame: int = 0,
        force_recompute: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves cached skeletal geometry from memory/disk, or extracts and saves it
        if not yet computed or if athlete-specific tracking is requested.
        """
        video_p = Path(video_path)
        if not video_p.exists():
            return {"total_frames": 0, "frames": []}

        canon_path = str(video_p.resolve())

        # Check memory & disk cache if not forcing recompute with a specific athlete target
        if not force_recompute and initial_bbox is None:
            if canon_path in self._memory_cache:
                return self._memory_cache[canon_path]

            cache_file = self._get_cache_path(canon_path)
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._memory_cache[canon_path] = data
                    return data
                except Exception as e:
                    logger.warning("Error reading geometry cache %s: %s", cache_file, e)

        # Extract and serialize geometry for entire video
        data = self._extract_video_geometry(
            canon_path,
            initial_bbox=initial_bbox,
            start_frame=start_frame,
            progress_callback=progress_callback,
        )
        cache_file = self._get_cache_path(canon_path)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            logger.info("Saved geometry cache to %s (%d frames)", cache_file, len(data.get("frames", [])))
        except Exception as e:
            logger.error("Failed to write geometry cache to %s: %s", cache_file, e)

        self._memory_cache[canon_path] = data
        return data

    def _extract_video_geometry(
        self,
        video_path: str,
        initial_bbox: Optional[Tuple[int, int, int, int]] = None,
        start_frame: int = 0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """Runs pose estimation across all frames of the video and captures 3D landmarks & joint angles."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"total_frames": 0, "frames": []}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)

        tracker = None
        if initial_bbox is not None:
            try:
                from tracker import PersonPoseTracker
                from services.settings import MODEL_PATH
                tracker = PersonPoseTracker(
                    model_path=str(MODEL_PATH),
                    min_detection_confidence=0.20,
                    min_tracking_confidence=0.20,
                )
            except Exception as e:
                logger.warning("Could not initialize PersonPoseTracker: %s", e)
                tracker = None

        frames_list: List[Dict[str, Any]] = []

        try:
            if tracker is not None and initial_bbox is not None:
                # Target-locked bidirectional tracking: starts at chosen start_frame and covers full video
                lms_by_frame: Dict[int, Optional[List]] = {}

                # Step A: Anchor on start_frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                ret, anchor_frame = cap.read()
                if not ret or anchor_frame is None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    start_frame = 0
                    ret, anchor_frame = cap.read()

                if ret and anchor_frame is not None:
                    # Forward pass from start_frame to end of video
                    tracker.init_tracker(anchor_frame, initial_bbox)
                    # Process anchor frame
                    res_anchor = tracker.process_frame(anchor_frame, start_frame, start_frame / fps)
                    lms_by_frame[start_frame] = res_anchor.image_landmarks if res_anchor.is_tracked else None

                    for f_idx in range(start_frame + 1, total_frames):
                        ret_f, f_data = cap.read()
                        if not ret_f or f_data is None:
                            break
                        res_f = tracker.process_frame(f_data, f_idx, f_idx / fps)
                        lms_by_frame[f_idx] = res_f.image_landmarks if res_f.is_tracked else None
                        if progress_callback and total_frames > 0 and f_idx % 10 == 0:
                            progress_callback(f_idx, total_frames)

                    # Backward pass from start_frame - 1 down to 0
                    if start_frame > 0:
                        try:
                            tracker_bwd = PersonPoseTracker(
                                model_path=str(MODEL_PATH),
                                min_detection_confidence=0.20,
                                min_tracking_confidence=0.20,
                            )
                            tracker_bwd.init_tracker(anchor_frame, initial_bbox)
                            for step, f_idx in enumerate(range(start_frame - 1, -1, -1)):
                                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                                ret_b, f_bwd = cap.read()
                                if ret_b and f_bwd is not None:
                                    res_b = tracker_bwd.process_frame(f_bwd, f_idx, (step + 1) * (1.0 / fps))
                                    lms_by_frame[f_idx] = res_b.image_landmarks if res_b.is_tracked else None
                            tracker_bwd.close()
                        except Exception as ex_bwd:
                            logger.warning("Backward tracking exception: %s", ex_bwd)

                # Assemble frames in chronological 0..N order
                for f_idx in range(total_frames):
                    lms = lms_by_frame.get(f_idx)
                    if lms is not None:
                        pts = [
                            {
                                "x": round(float(lm.x), 4),
                                "y": round(float(lm.y), 4),
                                "z": round(float(lm.z), 4),
                                "visibility": round(float(getattr(lm, "visibility", 1.0) or 1.0), 3),
                            }
                            for lm in lms
                        ]
                        angles = self._calculate_frame_angles(pts)
                        frames_list.append({
                            "frame_idx": f_idx,
                            "detected": True,
                            "landmarks": pts,
                            "angles": angles,
                        })
                    else:
                        frames_list.append({
                            "frame_idx": f_idx,
                            "detected": False,
                            "landmarks": [],
                            "angles": {},
                        })

            else:
                # Standard sequential forward pass (no specific athlete chosen)
                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    timestamp_ms = int(frame_idx * (1000.0 / fps))
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    res = self.detector.detect(rgb, timestamp_ms)
                    lms = res.pose_landmarks[0] if res and res.pose_landmarks else None

                    if lms is not None:
                        pts = [
                            {
                                "x": round(float(lm.x), 4),
                                "y": round(float(lm.y), 4),
                                "z": round(float(lm.z), 4),
                                "visibility": round(float(getattr(lm, "visibility", 1.0) or 1.0), 3),
                            }
                            for lm in lms
                        ]
                        angles = self._calculate_frame_angles(pts)
                        frames_list.append({
                            "frame_idx": frame_idx,
                            "detected": True,
                            "landmarks": pts,
                            "angles": angles,
                        })
                    else:
                        frames_list.append({
                            "frame_idx": frame_idx,
                            "detected": False,
                            "landmarks": [],
                            "angles": {},
                        })

                    frame_idx += 1
                    if progress_callback and total_frames > 0 and frame_idx % 10 == 0:
                        progress_callback(frame_idx, total_frames)

        finally:
            cap.release()
            if tracker is not None:
                tracker.close()

        return {
            "video_path": video_path,
            "total_frames": len(frames_list),
            "fps": fps,
            "width": width,
            "height": height,
            "tracked_bbox": list(initial_bbox) if initial_bbox else None,
            "start_frame": start_frame,
            "frames": frames_list,
        }

    def _calculate_frame_angles(self, pts: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculates 3D interior angles from serializable landmark list."""
        coords = {}
        for idx, lm in enumerate(pts):
            coords[idx] = np.array([lm["x"], lm["y"], lm["z"]])

        angles = {}
        for joint_key, (idx_a, idx_b, idx_c, _) in JOINT_DEFINITIONS.items():
            if idx_a in coords and idx_b in coords and idx_c in coords:
                ang = calculate_angle_3d(coords[idx_a], coords[idx_b], coords[idx_c])
                if ang is not None:
                    angles[joint_key] = round(float(ang), 1)

        # Trunk lean
        if all(k in coords for k in [11, 12, 23, 24]):
            trunk = calculate_trunk_angle(coords[11], coords[12], coords[23], coords[24])
            if trunk is not None:
                angles["trunk_lean"] = round(float(trunk), 1)

        # Shoulder tilt
        if 11 in coords and 12 in coords:
            dx = coords[12][0] - coords[11][0]
            dy = coords[12][1] - coords[11][1]
            tilt = np.degrees(np.arctan2(dy, dx))
            angles["shoulder_tilt"] = round(float(abs(tilt)), 1)

        return angles


geometry_cache = GeometryCache()
