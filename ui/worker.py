"""Background worker thread for camera capture and pose analysis without GUI freezing."""

import logging
import time
from typing import Optional
import cv2
import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal
from PySide6.QtGui import QImage

from exercises.base_exercise import BaseExercise, ExerciseMetrics
from exercises.registry import registry
from pose.detector import PoseDetector
from services.camera import CameraService
from services.settings import (
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    DEFAULT_CAMERA_INDEX,
)

logger = logging.getLogger(__name__)


class PoseWorker(QThread):
    """QThread worker running OpenCV capture, MediaPipe inference, and exercise biomechanics."""

    frame_ready = Signal(QImage, object, float)  # frame, metrics, fps
    status_message = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        camera_index: int = DEFAULT_CAMERA_INDEX,
        exercise_name: str = "Squat",
    ) -> None:
        super().__init__()
        self._camera_index = camera_index
        self._exercise_name = exercise_name

        self._running = False
        self._is_paused = False
        self._mutex = QMutex()

        self._camera_service: Optional[CameraService] = None
        self._detector: Optional[PoseDetector] = None
        self._exercise: Optional[BaseExercise] = None

    def set_exercise(self, name: str) -> None:
        """Safely switches the active exercise analyzer."""
        with QMutexLocker(self._mutex):
            self._exercise_name = name
            try:
                self._exercise = registry.create(name)
                logger.info("Switched exercise to %s", name)
            except Exception as e:
                logger.error("Failed to switch exercise: %s", e)

    def reset_exercise(self) -> None:
        """Resets the statistics of the active exercise."""
        with QMutexLocker(self._mutex):
            if self._exercise:
                self._exercise.reset()

    def set_camera(self, camera_index: int) -> None:
        """Changes the active camera hardware index."""
        with QMutexLocker(self._mutex):
            self._camera_index = camera_index
            if self._camera_service and self._running:
                self._camera_service.open(camera_index)

    def toggle_pause(self) -> bool:
        """Toggles analysis pause state."""
        with QMutexLocker(self._mutex):
            self._is_paused = not self._is_paused
            return self._is_paused

    def stop(self) -> None:
        """Stops the worker thread safely."""
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(2000)

    def run(self) -> None:
        """Main background loop."""
        self._running = True
        self.status_message.emit("Initializing camera and pose model...")

        try:
            self._detector = PoseDetector()
            self._exercise = registry.create(self._exercise_name)
            self._camera_service = CameraService(
                camera_index=self._camera_index,
                width=CAMERA_WIDTH,
                height=CAMERA_HEIGHT,
            )

            if not self._camera_service.open():
                self.error_occurred.emit(f"Could not open camera device {self._camera_index}.")
                return

        except Exception as e:
            logger.exception("Initialization error in PoseWorker")
            self.error_occurred.emit(f"Initialization error: {str(e)}")
            return

        self.status_message.emit("Camera and Pose Detector active.")

        start_time = time.perf_counter()
        frame_count = 0
        fps = 0.0

        while True:
            with QMutexLocker(self._mutex):
                if not self._running:
                    break
                is_paused = self._is_paused
                exercise = self._exercise

            if is_paused:
                time.sleep(0.05)
                continue

            success, frame = self._camera_service.read_frame()
            if not success or frame is None:
                time.sleep(0.01)
                continue

            # Performance FPS tracking
            frame_count += 1
            elapsed = time.perf_counter() - start_time
            if elapsed >= 0.5:
                fps = frame_count / elapsed
                frame_count = 0
                start_time = time.perf_counter()

            # Mirror frame horizontally for natural webcam user experience
            frame = cv2.flip(frame, 1)

            # BGR -> RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp_ms = int(time.perf_counter() * 1000)

            # Detect pose landmarks
            detection_result = self._detector.detect(rgb_frame, timestamp_ms)

            metrics = ExerciseMetrics()
            if detection_result and detection_result.pose_landmarks:
                first_pose = detection_result.pose_landmarks[0]
                if exercise:
                    metrics = exercise.analyze(first_pose, frame.shape)

                # Draw pose overlay onto BGR frame
                PoseDetector.draw_pose(
                    frame,
                    first_pose,
                    joint_highlights=metrics.joint_highlights,
                )

            # Convert BGR frame to QImage for Qt UI display
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888).copy()

            self.frame_ready.emit(q_img, metrics, fps)

        # Cleanup
        if self._camera_service:
            self._camera_service.release()
        if self._detector:
            self._detector.close()
        self.status_message.emit("Camera stopped.")
