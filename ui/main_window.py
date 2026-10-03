"""Main Application Window for FormCheck Desktop."""

import logging
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from services.settings import (
    APP_TITLE,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
)
from ui.camera_view import CameraView
from ui.exercise_panel import ExercisePanel
from ui.feedback_panel import FeedbackPanel
from ui.results_panel import ResultsPanel
from ui.worker import PoseWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary desktop window orchestrating views, controls, and asynchronous analysis worker."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(960, 640)

        self._worker: Optional[PoseWorker] = None
        self._selected_camera_index = 0
        self._selected_exercise = "Squat"

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # 1. Left Sidebar: Exercise selection & Controls
        self.exercise_panel = ExercisePanel(self)
        root_layout.addWidget(self.exercise_panel)

        # 2. Center Column: Camera viewport (top) + Results bar (bottom)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(12)

        self.camera_view = CameraView(self)
        self.results_panel = ResultsPanel(self)

        center_layout.addWidget(self.camera_view, stretch=1)
        center_layout.addWidget(self.results_panel, stretch=0)
        root_layout.addWidget(center_widget, stretch=1)

        # 3. Right Sidebar: Live Biomechanical Feedback
        self.feedback_panel = FeedbackPanel(self)
        root_layout.addWidget(self.feedback_panel)

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select workout and click Start Session.")

    def _connect_signals(self) -> None:
        self.exercise_panel.start_requested.connect(self._on_start_session)
        self.exercise_panel.pause_requested.connect(self._on_pause_session)
        self.exercise_panel.stop_requested.connect(self._on_stop_session)
        self.exercise_panel.reset_requested.connect(self._on_reset_session)

        self.exercise_panel.exercise_changed.connect(self._on_exercise_changed)
        self.exercise_panel.camera_changed.connect(self._on_camera_changed)

    def _on_start_session(self) -> None:
        """Launches the background camera capture and pose analysis worker thread."""
        if self._worker is not None and self._worker.isRunning():
            return

        self.status_bar.showMessage("Starting camera stream...")
        self.camera_view.set_inactive("Connecting to camera and loading pose model...")

        self._worker = PoseWorker(
            camera_index=self._selected_camera_index,
            exercise_name=self._selected_exercise,
        )

        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.status_message.connect(self.status_bar.showMessage)
        self._worker.error_occurred.connect(self._on_worker_error)

        self._worker.start()
        self.exercise_panel.set_session_running(True)

    def _on_pause_session(self) -> None:
        if self._worker:
            is_paused = self._worker.toggle_pause()
            self.exercise_panel.set_paused_state(is_paused)
            if is_paused:
                self.status_bar.showMessage("Session paused.")
            else:
                self.status_bar.showMessage("Session resumed.")

    def _on_stop_session(self) -> None:
        if self._worker:
            self.status_bar.showMessage("Stopping camera stream...")
            self._worker.stop()
            self._worker = None

        self.exercise_panel.set_session_running(False)
        self.exercise_panel.set_paused_state(False)
        self.camera_view.set_inactive("Session stopped.\nClick 'Start Session' to begin.")
        self.status_bar.showMessage("Session stopped.")

    def _on_reset_session(self) -> None:
        if self._worker:
            self._worker.reset_exercise()
        self.results_panel.reset_stats()
        self.status_bar.showMessage("Repetition counters reset.")

    def _on_exercise_changed(self, name: str) -> None:
        self._selected_exercise = name
        if self._worker:
            self._worker.set_exercise(name)
        self.results_panel.reset_stats()
        self.status_bar.showMessage(f"Active exercise switched to {name}.")

    def _on_camera_changed(self, index: int) -> None:
        self._selected_camera_index = index
        if self._worker:
            self._worker.set_camera(index)
        self.status_bar.showMessage(f"Camera index set to {index}.")

    def _on_frame_ready(self, q_img, metrics, fps) -> None:
        """UI thread slot receiving processed frames and analysis metrics."""
        self.camera_view.set_frame(q_img, fps)
        if metrics:
            self.feedback_panel.update_metrics(metrics)
            self.results_panel.update_metrics(metrics)

    def _on_worker_error(self, message: str) -> None:
        logger.error("PoseWorker error: %s", message)
        self._on_stop_session()
        QMessageBox.critical(self, "Camera / Model Error", message)

    def closeEvent(self, event) -> None:
        """Ensures background threads are cleanly stopped upon application exit."""
        self._on_stop_session()
        event.accept()
