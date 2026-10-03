"""Camera capture service using OpenCV."""

import logging
from typing import List, Optional, Tuple
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
    """Manages OpenCV VideoCapture lifecycle and frame acquisition."""

    def __init__(
        self,
        camera_index: int = DEFAULT_CAMERA_INDEX,
        width: int = CAMERA_WIDTH,
        height: int = CAMERA_HEIGHT,
        fps: int = CAMERA_FPS,
    ) -> None:
        self.camera_index = camera_index
        self.target_width = width
        self.target_height = height
        self.target_fps = fps

        self._cap: Optional[cv2.VideoCapture] = None

    def open(self, camera_index: Optional[int] = None) -> bool:
        """Opens the camera stream."""
        if camera_index is not None:
            self.camera_index = camera_index

        self.release()

        # On Windows, try CAP_DSHOW first for faster startup, fallback to default
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.camera_index)

        if not self._cap.isOpened():
            logger.error("Failed to open camera index %d", self.camera_index)
            self._cap = None
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a single frame from the camera."""
        if self._cap is None or not self._cap.isOpened():
            return False, None

        success, frame = self._cap.read()
        return success, frame

    def is_opened(self) -> bool:
        """Checks if the camera device is currently opened."""
        return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        """Releases the camera hardware."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning("Error releasing camera: %s", e)
            finally:
                self._cap = None

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
