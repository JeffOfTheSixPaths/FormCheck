"""Camera and video file capture service using OpenCV."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from services.settings import (
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    DEFAULT_CAMERA_INDEX,
)

logger = logging.getLogger(__name__)


class CameraService:
    """Manages OpenCV VideoCapture lifecycle for both live webcams and uploaded athletic videos."""

    def __init__(
        self,
        source: Union[int, str] = DEFAULT_CAMERA_INDEX,
        width: int = CAMERA_WIDTH,
        height: int = CAMERA_HEIGHT,
        fps: int = CAMERA_FPS,
        loop: bool = True,
    ) -> None:
        self.source: Union[int, str] = source
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.loop = loop

        self.is_file: bool = False
        self.file_path: Optional[str] = None
        self.native_fps: float = float(fps)
        self.total_frames: int = 0
        self.current_frame_idx: int = 0

        self._cap: Optional[cv2.VideoCapture] = None

    def open(
        self,
        source: Optional[Union[int, str]] = None,
        loop: Optional[bool] = None,
    ) -> bool:
        """Opens either a camera device index (int) or an uploaded video file (str)."""
        if source is not None:
            self.source = source
        if loop is not None:
            self.loop = loop

        self.release()

        # 1. Video File Input
        if isinstance(self.source, str):
            path_obj = Path(self.source)
            if not path_obj.exists():
                logger.error("Video file does not exist: %s", self.source)
                return False

            self._cap = cv2.VideoCapture(str(path_obj.resolve()))
            if not self._cap.isOpened():
                logger.error("Failed to open video file: %s", self.source)
                self._cap = None
                return False

            self.is_file = True
            self.file_path = str(path_obj.resolve())

            # Read video file properties
            fps = self._cap.get(cv2.CAP_PROP_FPS)
            self.native_fps = float(fps) if fps and fps > 0 else float(self.target_fps)
            self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.current_frame_idx = 0
            logger.info(
                "Opened athletic video clip '%s': %d frames at %.2f FPS",
                path_obj.name,
                self.total_frames,
                self.native_fps,
            )
            return True

        # 2. Live Hardware Camera Input
        self.is_file = False
        self.file_path = None
        camera_idx = int(self.source)

        # On Windows, try CAP_DSHOW first for faster startup, fallback to default
        self._cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(camera_idx)

        if not self._cap.isOpened():
            logger.error("Failed to open camera index %d", camera_idx)
            self._cap = None
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        self.native_fps = float(self.target_fps)
        self.total_frames = 0
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a single frame. Automatically loops video files if loop=True."""
        if self._cap is None or not self._cap.isOpened():
            return False, None

        success, frame = self._cap.read()
        if success and frame is not None:
            if self.is_file:
                self.current_frame_idx += 1
            return True, frame

        # Handle end of video stream
        if self.is_file and self.loop and self._cap is not None:
            # Rewind to first frame
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame_idx = 0
            success, frame = self._cap.read()
            if success and frame is not None:
                self.current_frame_idx += 1
                return True, frame

        return False, None

    def seek_frame(self, frame_num: int) -> bool:
        """Seeks to a specific frame index in a video file."""
        if self._cap is not None and self.is_file:
            clamped = max(0, min(frame_num, max(0, self.total_frames - 1)))
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, clamped)
            self.current_frame_idx = clamped
            return True
        return False

    def is_opened(self) -> bool:
        """Checks if the video source is currently opened."""
        return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        """Releases the camera hardware or closes the video file."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning("Error releasing video source: %s", e)
            finally:
                self._cap = None
                self.current_frame_idx = 0

    @staticmethod
    def get_video_info(file_path: str) -> Optional[Dict[str, Any]]:
        """Extracts resolution, frame count, FPS, and duration for an uploaded video."""
        path_obj = Path(file_path)
        if not path_obj.exists():
            return None

        cap = cv2.VideoCapture(str(path_obj.resolve()))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frames / fps if fps > 0 else 0.0
        cap.release()

        return {
            "name": path_obj.name,
            "path": str(path_obj.resolve()),
            "fps": fps,
            "total_frames": frames,
            "width": w,
            "height": h,
            "duration_seconds": round(duration, 2),
        }

    @staticmethod
    def list_available_cameras(max_tested: int = 4) -> List[int]:
        """Scans and lists active camera device indices."""
        available = []
        for idx in range(max_tested):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(idx)
                cap.release()
            else:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    available.append(idx)
                    cap.release()
        return available if available else [0]
