"""Biomechanical video editing engine providing frame-accurate trimming and spatial cropping."""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VideoEditor:
    """Provides video manipulation operations: trimming, cropping, and frame extraction."""

    @staticmethod
    def get_video_stats(video_path: str) -> Optional[Dict[str, Any]]:
        """Probes video dimensions, fps, duration, and frame count."""
        path_obj = Path(video_path)
        if not path_obj.exists():
            return None
        cap = cv2.VideoCapture(str(path_obj.resolve()))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0.0
        cap.release()

        return {
            "path": str(path_obj.resolve()),
            "name": path_obj.name,
            "width": width,
            "height": height,
            "fps": fps,
            "total_frames": total_frames,
            "duration": duration,
            "duration_sec": duration,
        }

    @staticmethod
    def get_frame(video_path: str, frame_idx: int) -> Optional[np.ndarray]:
        """Extracts a specific frame index from video."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx))
        success, frame = cap.read()
        cap.release()
        return frame if success else None

    @staticmethod
    def get_frame_at_time(video_path: str, timestamp_sec: float) -> Optional[np.ndarray]:
        """Extracts a frame closest to the specified timestamp in seconds."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        target_frame = int(timestamp_sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target_frame))
        success, frame = cap.read()
        cap.release()
        return frame if success else None

    @classmethod
    def trim_video(
        cls,
        input_path: str,
        output_path: str,
        start_sec: float,
        end_sec: float,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Trims a video clip between start_sec and end_sec.
        Saves output in MP4 format.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return False, f"Could not open source video: {input_path}"

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        start_frame = max(0, int(start_sec * fps))
        end_frame = min(total_frames, int(end_sec * fps))

        if start_frame >= end_frame:
            cap.release()
            return False, "Start time must be less than end time."

        frames_to_write = end_frame - start_frame

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            cap.release()
            return False, f"Could not initialize output video file: {output_path}"

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current_frame = start_frame
        written = 0

        try:
            while current_frame < end_frame:
                success, frame = cap.read()
                if not success or frame is None:
                    break
                out.write(frame)
                current_frame += 1
                written += 1

                if progress_callback and frames_to_write > 0:
                    progress_callback(written / frames_to_write)

            return True, output_path
        except Exception as e:
            logger.error("Error during video trimming: %s", e)
            return False, f"Trim failed: {str(e)}"
        finally:
            cap.release()
            out.release()

    @classmethod
    def crop_video(
        cls,
        input_path: str,
        output_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Crops a video clip to the specified bounding box (x, y, width, height).
        Ensures dimensions are even for MP4 encoding.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return False, f"Could not open source video: {input_path}"

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Clamp crop coordinates
        x1 = max(0, min(x, orig_w - 2))
        y1 = max(0, min(y, orig_h - 2))
        w = max(2, min(width, orig_w - x1))
        h = max(2, min(height, orig_h - y1))

        # Ensure even dimensions for codecs
        if w % 2 != 0:
            w -= 1
        if h % 2 != 0:
            h -= 1

        x2 = x1 + w
        y2 = y1 + h

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        if not out.isOpened():
            cap.release()
            return False, f"Could not initialize output video file: {output_path}"

        written = 0
        try:
            while True:
                success, frame = cap.read()
                if not success or frame is None:
                    break
                cropped = frame[y1:y2, x1:x2]
                out.write(cropped)
                written += 1

                if progress_callback and total_frames > 0:
                    progress_callback(written / total_frames)

            return True, output_path
        except Exception as e:
            logger.error("Error during video cropping: %s", e)
            return False, f"Crop failed: {str(e)}"
        finally:
            cap.release()
            out.release()


video_editor = VideoEditor()
