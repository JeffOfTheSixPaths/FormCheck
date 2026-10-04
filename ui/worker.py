"""Background worker thread for camera capture and pose analysis without GUI freezing."""

import logging
import time
from pathlib import Path
from typing import Optional, Union
import cv2
import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal
from PySide6.QtGui import QImage

from exercises.base_exercise import BaseExercise, ExerciseMetrics
from exercises.registry import registry
from pose.detector import PoseDetector
from services.camera import CameraService
from services.settings import (
    BASE_DIR,
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    DEFAULT_CAMERA_INDEX,
)

logger = logging.getLogger(__name__)


class PoseWorker(QThread):
    """QThread worker running OpenCV capture/video playback, MediaPipe inference, and exercise biomechanics."""

    frame_ready = Signal(QImage, object, float)  # frame, metrics, fps
    status_message = Signal(str)
    error_occurred = Signal(str)
    video_finished = Signal()
    recording_saved = Signal(str, str, float)  # file_path, exercise_name, duration_seconds

    def __init__(
        self,
        source: Union[int, str] = DEFAULT_CAMERA_INDEX,
        exercise_name: str = "Volleyball: Hitting (Arm Swing)",
        playback_speed: float = 1.0,
        loop_video: bool = True,
    ) -> None:
        super().__init__()
        self._source = source
        self._exercise_name = exercise_name
        self._playback_speed = float(playback_speed)
        self._loop_video = loop_video

        self._running = False
        self._is_paused = False
        self._mutex = QMutex()

        self._camera_service: Optional[CameraService] = None
        self._detector: Optional[PoseDetector] = None
        self._exercise: Optional[BaseExercise] = None

        # Movement Recording to Server
        self._is_recording: bool = False
        self._recording_path: Optional[str] = None
        self._recording_writer: Optional[cv2.VideoWriter] = None
        self._recording_frame_count: int = 0

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

    def set_source(self, source: Union[int, str], loop: Optional[bool] = None) -> None:
        """Changes the active source (camera index int or video file str)."""
        with QMutexLocker(self._mutex):
            self._source = source
            if loop is not None:
                self._loop_video = loop
            if self._camera_service and self._running:
                self._camera_service.open(source, loop=self._loop_video)

    def set_camera(self, camera_index: int) -> None:
        """Legacy helper for camera hardware index."""
        self.set_source(camera_index)

    def set_playback_speed(self, speed: float) -> None:
        """Updates playback speed multiplier for video files (e.g. 0.5 for slow motion)."""
        with QMutexLocker(self._mutex):
            self._playback_speed = max(0.1, min(float(speed), 4.0))

    def set_loop(self, loop: bool) -> None:
        """Toggles looping behavior for video files."""
        with QMutexLocker(self._mutex):
            self._loop_video = loop
            if self._camera_service:
                self._camera_service.loop = loop

    def toggle_pause(self) -> bool:
        """Toggles analysis pause state."""
        with QMutexLocker(self._mutex):
            self._is_paused = not self._is_paused
            return self._is_paused

    def enable_recording(self, enabled: bool = True, output_path: Optional[str] = None) -> None:
        """Enables frame-by-frame recording of the athletic movement to server storage."""
        with QMutexLocker(self._mutex):
            self._is_recording = enabled
            self._recording_path = output_path

    def stop(self) -> None:
        """Stops the worker thread safely."""
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(2000)

    def run(self) -> None:
        """Main background loop."""
        self._running = True
        is_video_file = isinstance(self._source, str)
        source_desc = f"video '{Path(self._source).name}'" if is_video_file else f"sensor device {self._source}"
        self.status_message.emit(f"Initializing optical stream from {source_desc}...")

        try:
            self._detector = PoseDetector()
            self._exercise = registry.create(self._exercise_name)
            self._camera_service = CameraService(
                source=self._source,
                width=CAMERA_WIDTH,
                height=CAMERA_HEIGHT,
                loop=self._loop_video,
            )

            if not self._camera_service.open():
                self.error_occurred.emit(f"Could not open {source_desc}.")
                return

        except Exception as e:
            logger.exception("Initialization error in PoseWorker")
            self.error_occurred.emit(f"Initialization error: {str(e)}")
            return

        self.status_message.emit("Optical stream and Pose Detector active.")

        start_time = time.perf_counter()
        frame_count = 0
        fps = 0.0
        synthetic_timestamp_ms = 0

        while True:
            cycle_start = time.perf_counter()

            with QMutexLocker(self._mutex):
                if not self._running:
                    break
                is_paused = self._is_paused
                exercise = self._exercise
                speed = self._playback_speed

            if is_paused:
                time.sleep(0.05)
                continue

            success, frame = self._camera_service.read_frame()
            if not success or frame is None:
                if self._camera_service.is_file and not self._camera_service.loop:
                    self.status_message.emit("Video analysis completed.")
                    self.video_finished.emit()
                    break
                time.sleep(0.01)
                continue

            # Performance FPS tracking
            frame_count += 1
            elapsed = time.perf_counter() - start_time
            if elapsed >= 0.5:
                fps = frame_count / elapsed
                frame_count = 0
                start_time = time.perf_counter()

            # Mirror live webcam horizontally for natural mirror feel; DO NOT mirror uploaded video files!
            if not self._camera_service.is_file:
                frame = cv2.flip(frame, 1)

            # BGR -> RGB for MediaPipe inference
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Monotonic timestamp for MediaPipe detector
            if self._camera_service.is_file:
                fps_rate = self._camera_service.native_fps if self._camera_service.native_fps > 0 else 30.0
                synthetic_timestamp_ms = int((self._camera_service.current_frame_idx / fps_rate) * 1000)
                timestamp_ms = synthetic_timestamp_ms
            else:
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

            # Write frame to video recording writer if enabled
            with QMutexLocker(self._mutex):
                is_rec = self._is_recording
                rec_path = self._recording_path

            if is_rec:
                if self._recording_writer is None:
                    if not rec_path:
                        staging_dir = BASE_DIR / "server_storage" / "staging"
                        staging_dir.mkdir(parents=True, exist_ok=True)
                        rec_path = str(staging_dir / f"drill_rec_{int(time.time() * 1000)}.mp4")
                        self._recording_path = rec_path
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    self._recording_writer = cv2.VideoWriter(rec_path, fourcc, 25.0, (w, h))

                if self._recording_writer and self._recording_writer.isOpened():
                    self._recording_writer.write(frame)
                    self._recording_frame_count += 1

            # Convert BGR frame to QImage for Qt UI display
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888).copy()

            self.frame_ready.emit(q_img, metrics, fps)

            # Video playback pacing control for uploaded files
            if self._camera_service.is_file:
                target_fps = (self._camera_service.native_fps or 30.0) * speed
                frame_interval = 1.0 / max(1.0, target_fps)
                cycle_duration = time.perf_counter() - cycle_start
                sleep_remainder = frame_interval - cycle_duration
                if sleep_remainder > 0:
                    time.sleep(sleep_remainder)

        # Cleanup & Finalize Recording
        if self._recording_writer is not None:
            self._recording_writer.release()
            self._recording_writer = None
            duration_rec = self._recording_frame_count / 25.0
            if self._recording_path and self._recording_frame_count > 0:
                logger.info("Saved movement recording to: %s (%d frames)", self._recording_path, self._recording_frame_count)
                self.recording_saved.emit(self._recording_path, self._exercise_name, duration_rec)

        if self._camera_service:
            self._camera_service.release()
        if self._detector:
            self._detector.close()
        self.status_message.emit("Analysis stopped.")
