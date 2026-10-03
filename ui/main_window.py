"""Main Application Window for FormCheck Desktop."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

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

from services.db import db
from services.settings import (
    APP_NAME,
    APP_TITLE,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
)
from ui.camera_view import CameraView
from ui.exercise_panel import ExercisePanel
from ui.feedback_panel import FeedbackPanel
from ui.history_dialog import HistoryDialog
from ui.results_panel import ResultsPanel
from ui.worker import PoseWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary desktop window orchestrating views, controls, and asynchronous analysis worker."""

    def __init__(self, user: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(960, 640)

        self._user = user or {"id": None, "username": "Guest", "email": "", "full_name": "Guest User"}
        self._worker: Optional[PoseWorker] = None
        self._selected_camera_index = 0
        self._selected_exercise = "Squat"
        self._session_start_time: Optional[float] = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        # Menu Bar
        menu_bar = self.menuBar()
        account_menu = menu_bar.addMenu("&Account")

        username = self._user.get("username", "Guest")
        self.user_info_action = account_menu.addAction(f"Signed in as: {username}")
        self.user_info_action.setEnabled(False)

        account_menu.addSeparator()

        self.history_action = account_menu.addAction("📊 View Workout History (SQL)...")
        self.history_action.triggered.connect(self._show_workout_history)
        if not self._user.get("id"):
            self.history_action.setEnabled(False)

        self.switch_user_action = account_menu.addAction("🔄 Switch User / Sign In...")
        self.switch_user_action.triggered.connect(self._on_switch_user)

        account_menu.addSeparator()
        exit_action = account_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

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
        self._update_status_bar("Ready. Select workout and click Start Session.")

    def _update_status_bar(self, message: str) -> None:
        user_str = self._user.get("username", "Guest")
        self.status_bar.showMessage(f"[{user_str}] {message}")

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

        self._update_status_bar("Starting camera stream...")
        self.camera_view.set_inactive("Connecting to camera and loading pose model...")
        self._session_start_time = time.time()

        self._worker = PoseWorker(
            camera_index=self._selected_camera_index,
            exercise_name=self._selected_exercise,
        )

        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.status_message.connect(self._update_status_bar)
        self._worker.error_occurred.connect(self._on_worker_error)

        self._worker.start()
        self.exercise_panel.set_session_running(True)

    def _on_pause_session(self) -> None:
        if self._worker:
            is_paused = self._worker.toggle_pause()
            self.exercise_panel.set_paused_state(is_paused)
            if is_paused:
                self._update_status_bar("Session paused.")
            else:
                self._update_status_bar("Session resumed.")

    def _on_stop_session(self) -> None:
        if self._worker:
            self._update_status_bar("Stopping camera stream...")
            self._worker.stop()
            self._worker = None

        self.exercise_panel.set_session_running(False)
        self.exercise_panel.set_paused_state(False)
        self.camera_view.set_inactive("Session stopped.\nClick 'Start Session' to begin.")

        # Persist workout statistics to SQL database if user is authenticated
        stats = self.results_panel.get_stats()
        user_id = self._user.get("id")

        if user_id and stats["total_reps"] > 0:
            duration = int(time.time() - self._session_start_time) if self._session_start_time else 0
            session_id = db.log_workout_session(
                user_id=user_id,
                exercise_name=self._selected_exercise,
                clean_reps=stats["clean_reps"],
                flawed_reps=stats["flawed_reps"],
                avg_form_score=stats["accuracy"],
                duration_seconds=duration,
            )
            if session_id:
                self._update_status_bar(
                    f"Session stopped. Saved {stats['total_reps']} reps to SQL database!"
                )
                return

        self._update_status_bar("Session stopped.")

    def _on_reset_session(self) -> None:
        if self._worker:
            self._worker.reset_exercise()
        self.results_panel.reset_stats()
        self._session_start_time = time.time()
        self._update_status_bar("Repetition counters reset.")

    def _on_exercise_changed(self, name: str) -> None:
        self._selected_exercise = name
        if self._worker:
            self._worker.set_exercise(name)
        self.results_panel.reset_stats()
        self._update_status_bar(f"Active exercise switched to {name}.")

    def _on_camera_changed(self, index: int) -> None:
        self._selected_camera_index = index
        if self._worker:
            self._worker.set_camera(index)
        self._update_status_bar(f"Camera index set to {index}.")

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

    def _show_workout_history(self) -> None:
        """Opens modal displaying user's historical sessions from SQLite."""
        if not self._user.get("id"):
            QMessageBox.information(
                self,
                "Guest Account",
                "Workout logs are only stored for registered accounts. Please sign in to save and view history.",
            )
            return

        dialog = HistoryDialog(self._user, self)
        dialog.exec()

    def _on_switch_user(self) -> None:
        """Allows switching user or signing into an account from guest mode."""
        from ui.login_dialog import LoginDialog

        # Stop active session if running
        self._on_stop_session()

        login_dlg = LoginDialog(self)
        if login_dlg.exec() == LoginDialog.Accepted and login_dlg.authenticated_user:
            self._user = login_dlg.authenticated_user
            username = self._user.get("username", "Guest")
            self.user_info_action.setText(f"Signed in as: {username}")
            self.history_action.setEnabled(bool(self._user.get("id")))
            self._update_status_bar(f"Switched account to {username}.")

    def closeEvent(self, event) -> None:
        """Ensures background threads are cleanly stopped upon application exit."""
        self._on_stop_session()
        event.accept()
