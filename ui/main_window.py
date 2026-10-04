"""Main Application Window for FormCheck Desktop."""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from exercises.registry import registry
from services.db import db
from services.settings import (
    APP_NAME,
    APP_TITLE,
    BASE_DIR,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
)
from services.theme import THEME
from services.video_service import video_service
from ui.camera_view import CameraView
from ui.comparison_screen import ComparisonScreen
from ui.editor_screen import EditorScreen
from ui.exercise_panel import ExercisePanel
from ui.feedback_panel import FeedbackPanel
from ui.history_dialog import HistoryDialog
from ui.home_screen import HomeScreen
from ui.results_panel import ResultsPanel
from ui.upload_screen import UploadScreen
from ui.worker import PoseWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary desktop window orchestrating multi-screen athletic analysis workflows."""

    SCREEN_HOME = 0
    SCREEN_DRILL = 1
    SCREEN_UPLOAD = 2
    SCREEN_EDITOR = 3
    SCREEN_COMPARE = 4

    def __init__(self, user: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(1000, 680)

        self._user = user or {"id": None, "username": "Guest", "email": "", "full_name": "Guest User"}
        self._worker: Optional[PoseWorker] = None
        self._selected_camera_index = 0
        names = registry.get_names()
        self._selected_exercise = names[0] if names else "Volleyball: Hitting (Arm Swing)"
        self._session_start_time: Optional[float] = None
        self._nav_buttons: List[QPushButton] = []

        self._init_ui()
        self._connect_signals()
        self._update_auth_ui()
        self.set_active_screen(self.SCREEN_HOME)

    def _init_ui(self) -> None:
        # 1. Menu Bar
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        open_video_action = file_menu.addAction("Open Athletic Video Clip...")
        open_video_action.setShortcut(QKeySequence("Ctrl+O"))
        open_video_action.triggered.connect(self._on_open_video_file)

        file_menu.addSeparator()
        nav_home_action = file_menu.addAction("Go to Dashboard (Home)")
        nav_home_action.triggered.connect(lambda: self.set_active_screen(self.SCREEN_HOME))

        nav_drill_action = file_menu.addAction("Go to Live Recorder")
        nav_drill_action.triggered.connect(lambda: self.set_active_screen(self.SCREEN_DRILL))

        nav_upload_action = file_menu.addAction("Go to Video Vault (Upload)")
        nav_upload_action.triggered.connect(lambda: self.set_active_screen(self.SCREEN_UPLOAD))

        nav_editor_action = file_menu.addAction("Go to Video Editor (Trim/Crop)")
        nav_editor_action.triggered.connect(lambda: self.set_active_screen(self.SCREEN_EDITOR))

        nav_compare_action = file_menu.addAction("Go to Pro Form Comparison")
        nav_compare_action.triggered.connect(lambda: self.set_active_screen(self.SCREEN_COMPARE))

        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)

        # Account Menu
        account_menu = menu_bar.addMenu("&Account")

        username = self._user.get("username", "Guest")
        self.user_info_action = account_menu.addAction(f"Signed in as: {username}")
        self.user_info_action.setEnabled(False)

        account_menu.addSeparator()

        self.history_action = account_menu.addAction("View Athlete Performance Log (SQL)...")
        self.history_action.triggered.connect(self._show_workout_history)
        if not self._user.get("id"):
            self.history_action.setEnabled(False)

        self.switch_user_action = account_menu.addAction("Switch Athlete / Sign In...")
        self.switch_user_action.triggered.connect(self._on_switch_user)

        # Central Master Widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        master_layout = QVBoxLayout(central_widget)
        master_layout.setContentsMargins(12, 10, 12, 10)
        master_layout.setSpacing(10)

        # 2. Top Application Navigation Bar
        self.nav_bar = self._create_top_nav_bar()
        master_layout.addWidget(self.nav_bar)

        # 3. Stacked Screen Container
        self.stacked_widget = QStackedWidget(self)
        master_layout.addWidget(self.stacked_widget, stretch=1)

        # Screen 0: Home Dashboard
        self.home_screen = HomeScreen(user=self._user, parent=self)
        self.stacked_widget.addWidget(self.home_screen)

        # Screen 1: Live Optical Drill Tracker (Original Workspace)
        self.drill_container = self._create_drill_container()
        self.stacked_widget.addWidget(self.drill_container)

        # Screen 2: Video Vault & Upload Screen
        self.upload_screen = UploadScreen(user=self._user, parent=self)
        self.stacked_widget.addWidget(self.upload_screen)

        # Screen 3: Video Trim & Crop Editor
        self.editor_screen = EditorScreen(user=self._user, parent=self)
        self.stacked_widget.addWidget(self.editor_screen)

        # Screen 4: Pro Athlete Form Comparison Screen
        self.comparison_screen = ComparisonScreen(user=self._user, parent=self)
        self.stacked_widget.addWidget(self.comparison_screen)

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_bar("FormCheck AI Engine calibrated. Select athletic module to begin.")

    def _create_top_nav_bar(self) -> QFrame:
        nav = QFrame()
        nav.setStyleSheet(
            f"QFrame {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 6px 12px; "
            f"}}"
        )
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # App Brand
        lbl_brand = QLabel("FORMCHECK //")
        lbl_brand.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 13px; font-weight: 900; letter-spacing: 1px; padding-right: 8px;"
        )
        layout.addWidget(lbl_brand)

        # Navigation Buttons
        self.btn_nav_home = QPushButton("HOME")
        self.btn_nav_drill = QPushButton("LIVE DRILL")
        self.btn_nav_upload = QPushButton("UPLOAD VAULT")
        self.btn_nav_editor = QPushButton("VIDEO EDITOR")
        self.btn_nav_compare = QPushButton("PRO COMPARISON")

        self._nav_buttons = [
            self.btn_nav_home,
            self.btn_nav_drill,
            self.btn_nav_upload,
            self.btn_nav_editor,
            self.btn_nav_compare,
        ]

        self.btn_nav_home.clicked.connect(lambda: self.set_active_screen(self.SCREEN_HOME))
        self.btn_nav_drill.clicked.connect(lambda: self.set_active_screen(self.SCREEN_DRILL))
        self.btn_nav_upload.clicked.connect(lambda: self.set_active_screen(self.SCREEN_UPLOAD))
        self.btn_nav_editor.clicked.connect(lambda: self.set_active_screen(self.SCREEN_EDITOR))
        self.btn_nav_compare.clicked.connect(lambda: self.set_active_screen(self.SCREEN_COMPARE))

        for btn in self._nav_buttons:
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)

        layout.addStretch()

        # Athlete Status & Account Actions
        self.lbl_athlete_badge = QLabel("GUEST")
        self.lbl_athlete_badge.setStyleSheet(
            f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 800; letter-spacing: 0.8px; padding: 4px 8px; "
            f"background-color: {THEME.BG_INPUT}; border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"border: 1px solid {THEME.BORDER_DARK};"
        )
        layout.addWidget(self.lbl_athlete_badge)

        self.btn_history = QPushButton("HISTORY")
        self.btn_history.setCursor(Qt.PointingHandCursor)
        self.btn_history.setStyleSheet(
            f"QPushButton {{ "
            f"  background-color: {THEME.BG_INPUT}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"  color: {THEME.TEXT_MUTED}; "
            f"  font-family: {THEME.FONT_FAMILY_TECH}; "
            f"  font-size: 11px; font-weight: 700; letter-spacing: 0.5px; "
            f"  padding: 5px 10px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"  border-color: {THEME.PRIMARY_COLOR}; "
            f"  color: {THEME.PRIMARY_COLOR}; "
            f"}}"
        )
        self.btn_history.clicked.connect(self._show_workout_history)
        layout.addWidget(self.btn_history)

        self.btn_switch_athlete = QPushButton("SIGN IN")
        self.btn_switch_athlete.setCursor(Qt.PointingHandCursor)
        self.btn_switch_athlete.setStyleSheet(
            f"QPushButton {{ "
            f"  background-color: {THEME.BG_INPUT}; "
            f"  border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"  color: {THEME.PRIMARY_COLOR}; "
            f"  font-family: {THEME.FONT_FAMILY_TECH}; "
            f"  font-size: 11px; font-weight: 800; letter-spacing: 0.5px; "
            f"  padding: 5px 10px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"  background-color: {THEME.PRIMARY_COLOR}; "
            f"  color: #09090b; "
            f"}}"
        )
        self.btn_switch_athlete.clicked.connect(self._on_switch_user)
        layout.addWidget(self.btn_switch_athlete)

        return nav

    def _create_drill_container(self) -> QWidget:
        container = QWidget()
        drill_layout = QHBoxLayout(container)
        drill_layout.setContentsMargins(0, 0, 0, 0)
        drill_layout.setSpacing(14)

        # 1. Left Sidebar: Exercise selection & Controls
        self.exercise_panel = ExercisePanel(self)
        drill_layout.addWidget(self.exercise_panel)

        # 2. Center Column: Camera viewport (top) + Results bar (bottom)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(14)

        self.camera_view = CameraView(self)
        self.results_panel = ResultsPanel(self)

        center_layout.addWidget(self.camera_view, stretch=1)
        center_layout.addWidget(self.results_panel, stretch=0)
        drill_layout.addWidget(center_widget, stretch=1)

        # 3. Right Sidebar: Live Biomechanical Feedback
        self.feedback_panel = FeedbackPanel(self)
        drill_layout.addWidget(self.feedback_panel)

        return container

    def _connect_signals(self) -> None:
        # Cross-screen Navigation Signals
        self.home_screen.navigate_to.connect(self._handle_navigation)
        self.home_screen.switch_user_requested.connect(self._on_switch_user)

        self.upload_screen.navigate_to.connect(self._handle_navigation)
        self.upload_screen.open_editor_requested.connect(self._open_in_editor)
        self.upload_screen.open_comparison_requested.connect(self._open_in_comparison)
        self.upload_screen.switch_user_requested.connect(self._on_switch_user)

        self.editor_screen.navigate_to.connect(self._handle_navigation)
        self.editor_screen.send_to_compare.connect(self._send_editor_to_comparison)

        self.comparison_screen.navigate_to.connect(self._handle_navigation)

        # Live Drill Signals
        self.exercise_panel.start_requested.connect(self._on_start_session)
        self.exercise_panel.pause_requested.connect(self._on_pause_session)
        self.exercise_panel.stop_requested.connect(self._on_stop_session)
        self.exercise_panel.reset_requested.connect(self._on_reset_session)

        self.exercise_panel.exercise_changed.connect(self._on_exercise_changed)
        self.exercise_panel.camera_changed.connect(self._on_camera_changed)
        self.exercise_panel.source_changed.connect(self._on_source_changed)
        self.exercise_panel.video_selected.connect(self._on_video_selected)

    def set_active_screen(self, index: int) -> None:
        """Switches the visible stacked screen and synchronizes navigation bar highlighting."""
        # Pause background drill analysis if navigating away from Live Drill
        if self.stacked_widget.currentIndex() == self.SCREEN_DRILL and index != self.SCREEN_DRILL:
            if self._worker and self._worker.isRunning():
                self._on_pause_session()

        self.stacked_widget.setCurrentIndex(index)

        # Update navigation button visual active states
        for i, btn in enumerate(self._nav_buttons):
            if i == index:
                btn.setStyleSheet(
                    f"QPushButton {{ "
                    f"  background-color: {THEME.BG_INPUT}; "
                    f"  border: 1.5px solid {THEME.PRIMARY_COLOR}; "
                    f"  border-radius: {THEME.BORDER_RADIUS_SM}; "
                    f"  color: {THEME.PRIMARY_COLOR}; "
                    f"  font-family: {THEME.FONT_FAMILY_DISPLAY}; "
                    f"  font-size: 10px; font-weight: 800; letter-spacing: 0.5px; "
                    f"  padding: 5px 10px; "
                    f"}}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ "
                    f"  background-color: transparent; "
                    f"  border: 1px solid {THEME.BORDER_COLOR}; "
                    f"  border-radius: {THEME.BORDER_RADIUS_SM}; "
                    f"  color: {THEME.TEXT_MUTED}; "
                    f"  font-family: {THEME.FONT_FAMILY_DISPLAY}; "
                    f"  font-size: 10px; font-weight: 700; letter-spacing: 0.5px; "
                    f"  padding: 5px 10px; "
                    f"}} "
                    f"QPushButton:hover {{ "
                    f"  background-color: {THEME.BG_INPUT}; "
                    f"  border-color: {THEME.BORDER_LIGHT}; "
                    f"  color: {THEME.TEXT_PRIMARY}; "
                    f"}}"
                )

        # Status bar update
        screen_names = ["Home Dashboard", "Live Drill Tracker", "Upload & Video Vault", "Video Editor Studio", "Pro Comparison"]
        name = screen_names[index] if 0 <= index < len(screen_names) else "Workspace"
        self._update_status_bar(f"Active View: {name}")

    def _handle_navigation(self, target: str) -> None:
        """Route string targets to screen indices."""
        target_map = {
            "home": self.SCREEN_HOME,
            "drill": self.SCREEN_DRILL,
            "upload": self.SCREEN_UPLOAD,
            "editor": self.SCREEN_EDITOR,
            "compare": self.SCREEN_COMPARE,
        }
        idx = target_map.get(target, self.SCREEN_HOME)
        self.set_active_screen(idx)

    def _open_in_editor(self, video_path: str) -> None:
        """Opens specified video in Video Editor studio and navigates there."""
        self.editor_screen.load_video(video_path)
        self.set_active_screen(self.SCREEN_EDITOR)

    def _open_in_comparison(self, video_path: str, category_or_ref_path: str) -> None:
        """Loads video into appropriate slot of Comparison screen and navigates there."""
        if category_or_ref_path and Path(category_or_ref_path).exists():
            # Dual loading: (user_video_path, pro_ref_video_path)
            self.comparison_screen.load_user_video(video_path)
            self.comparison_screen.load_pro_video(category_or_ref_path)
        elif category_or_ref_path == "pro":
            self.comparison_screen.load_pro_video(video_path)
        else:
            self.comparison_screen.load_user_video(video_path)
        self.set_active_screen(self.SCREEN_COMPARE)

    def _send_editor_to_comparison(self, video_path: str) -> None:
        """Sends edited/trimmed video to comparison screen as user performance."""
        self.comparison_screen.load_user_video(video_path)
        self.set_active_screen(self.SCREEN_COMPARE)

    def _update_auth_ui(self) -> None:
        """Refreshes UI elements reflecting current athlete login state."""
        user_id = self._user.get("id")
        username = self._user.get("username", "Guest")

        if user_id:
            self.lbl_athlete_badge.setText(f"ATHLETE: {username.upper()}")
            self.lbl_athlete_badge.setStyleSheet(
                f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; "
                f"font-size: 11px; font-weight: 800; letter-spacing: 1px; padding: 4px 8px; "
                f"background-color: {THEME.BG_INPUT}; border-radius: {THEME.BORDER_RADIUS_SM}; "
                f"border: 1px solid {THEME.BORDER_DARK};"
            )
            self.btn_history.setEnabled(True)
            self.history_action.setEnabled(True)
            self.btn_switch_athlete.setText("SWITCH ATHLETE")
        else:
            self.lbl_athlete_badge.setText("ATHLETE: GUEST")
            self.lbl_athlete_badge.setStyleSheet(
                f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_TECH}; "
                f"font-size: 11px; font-weight: 800; letter-spacing: 1px; padding: 4px 8px; "
                f"background-color: {THEME.BG_INPUT}; border-radius: {THEME.BORDER_RADIUS_SM}; "
                f"border: 1px solid {THEME.BORDER_DARK};"
            )
            self.btn_history.setEnabled(False)
            self.history_action.setEnabled(False)
            self.btn_switch_athlete.setText("SIGN IN")

        self.user_info_action.setText(f"Signed in as: {username}")

    def _update_status_bar(self, message: str) -> None:
        user_str = self._user.get("username", "Guest")
        self.status_bar.showMessage(f"[{user_str}] {message}")

    def _on_start_session(self) -> None:
        """Launches the background camera capture or video file pose analysis worker thread."""
        if self._worker is not None and self._worker.isRunning():
            return

        info = self.exercise_panel.get_current_source_info()
        source = info["source"]
        mode = info["mode"]
        speed = info["speed"]
        loop = info["loop"]
        name = info["name"]

        if mode == "video" and (source is None or not source):
            self.exercise_panel._on_browse_video_clicked()
            info = self.exercise_panel.get_current_source_info()
            source = info["source"]
            speed = info["speed"]
            loop = info["loop"]
            name = info["name"]
            if source is None or not source:
                self._update_status_bar("Drill aborted: No athletic video clip selected.")
                return

        self._session_start_time = time.time()
        self.camera_view.set_source_info(mode=mode, label=name, speed=speed)

        if mode == "video":
            self._update_status_bar(f"Loading athletic video: {name} ({speed:.2f}x speed)...")
        else:
            self._update_status_bar("Initializing optical sensor stream...")

        self.camera_view.set_inactive("Calibrating optical stream and pose kinematics...")

        self._worker = PoseWorker(
            source=source,
            exercise_name=self._selected_exercise,
            playback_speed=speed,
            loop_video=loop,
        )

        # Movement Recording: Auto-save session to server vault if enabled
        if self.exercise_panel.is_recording_enabled():
            staging_dir = BASE_DIR / "server_storage" / "temp_recordings"
            staging_dir.mkdir(parents=True, exist_ok=True)
            stamp = int(time.time())
            slug = self._selected_exercise.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            rec_filename = f"rec_{slug}_{stamp}.mp4"
            rec_path = str(staging_dir / rec_filename)
            self._worker.enable_recording(True, rec_path)
            self.exercise_panel.set_recording_status(True, "● RECORDING MOVEMENT TO SERVER...")

        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.status_message.connect(self._update_status_bar)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.video_finished.connect(self._on_video_finished)
        self._worker.recording_saved.connect(self._on_recording_saved)

        self._worker.start()
        self.exercise_panel.set_session_running(True)

    def _on_pause_session(self) -> None:
        if self._worker:
            is_paused = self._worker.toggle_pause()
            self.exercise_panel.set_paused_state(is_paused)
            if is_paused:
                self._update_status_bar("Recording paused.")
            else:
                self._update_status_bar("Recording resumed.")

    def _on_stop_session(self) -> None:
        if self._worker:
            self._update_status_bar("Terminating sensor stream...")
            self._worker.stop()
            self._worker = None

        self.exercise_panel.set_session_running(False)
        self.exercise_panel.set_paused_state(False)
        self.exercise_panel.set_recording_status(False, "Ready to record")

        info = self.exercise_panel.get_current_source_info()
        if info["mode"] == "video" and info["name"]:
            self.camera_view.set_inactive(
                f"ATHLETIC VIDEO LOADED\n{info['name']}\n\nClick 'START RECORDING' to run biomechanical analysis"
            )
        else:
            self.camera_view.set_inactive("CAMERA OFF\nClick 'START RECORDING' to initiate session.")

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
                    f"Drill completed. Saved {stats['total_reps']} athletic reps to performance log."
                )
                return

        self._update_status_bar("Session terminated.")

    def _on_recording_saved(self, temp_path: str, exercise_name: str, duration: float) -> None:
        """Uploads auto-recordedmovement to server vault and offers pro similarity recommendation."""
        if not Path(temp_path).exists():
            return

        user_id = self._user.get("id")
        sport_category = "General"
        ex_lower = exercise_name.lower()
        if any(w in ex_lower for w in ["baseball", "pitch", "bat", "field"]):
            sport_category = "Baseball"
        elif any(w in ex_lower for w in ["volleyball", "spike", "approach", "hit", "pass", "set"]):
            sport_category = "Volleyball"

        title = f"{exercise_name} ({time.strftime('%b %d, %H:%M')})"
        try:
            uploaded = video_service.upload_video(
                source_path=temp_path,
                title=title,
                sport=sport_category,
                movement_type=exercise_name,
                category="personal",
                user_id=user_id,
                notes=f"Auto-recorded drill session duration {duration:.1f}s",
            )
        except Exception as e:
            logger.exception("Failed to save movement recording to server vault: %s", e)
            return

        # Refresh dropdowns on upload and comparison screens
        self.comparison_screen.set_user(self._user)
        self.upload_screen.set_user(self._user)

        self._update_status_bar(f"Movement saved to Server Vault: {uploaded['title']}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Movement Saved // AI Pro Match")
        msg.setText(
            f"<b>MOVEMENT RECORDING SAVED TO SERVER VAULT</b><br><br>"
            f"<b>Drill:</b> {exercise_name}<br>"
            f"<b>Duration:</b> {duration:.1f}s<br>"
            f"<b>Server Vault File:</b> <code>server_storage/personal/{Path(uploaded['file_path']).name}</code><br><br>"
            f"Would you like to analyze your 16-joint angular variance vectors and find which professional athlete you are closest to?"
        )
        btn_match = msg.addButton("FIND CLOSEST PRO", QMessageBox.AcceptRole)
        btn_compare = msg.addButton("OPEN IN COMPARISON", QMessageBox.ActionRole)
        btn_dismiss = msg.addButton("DISMISS", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_match)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_match:
            self.set_active_screen(self.SCREEN_COMPARE)
            self.comparison_screen.load_user_video(uploaded["file_path"])
            self.comparison_screen._on_find_closest_pro()
        elif clicked == btn_compare:
            self.set_active_screen(self.SCREEN_COMPARE)
            self.comparison_screen.load_user_video(uploaded["file_path"])

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

    def _on_source_changed(self, source: Any, mode: str, speed: float, loop: bool) -> None:
        name = Path(source).name if isinstance(source, str) else f"Sensor Device {source}"
        self.camera_view.set_source_info(mode=mode, label=name, speed=speed)
        if self._worker and self._worker.isRunning():
            if source is not None:
                self._worker.set_source(source, loop=loop)
            self._worker.set_playback_speed(speed)

    def _on_video_selected(self, file_path: str, speed: float, loop: bool) -> None:
        name = Path(file_path).name
        self._update_status_bar(f"Loaded athletic video clip: {name} ({speed:.2f}x speed)")
        self.camera_view.set_source_info("video", name, speed)

    def _on_video_finished(self) -> None:
        self._update_status_bar("Athletic video clip analysis completed.")
        self._on_stop_session()

    def _on_open_video_file(self) -> None:
        self.set_active_screen(self.SCREEN_DRILL)
        idx = self.exercise_panel.combo_source_mode.findData("video")
        if idx >= 0:
            self.exercise_panel.combo_source_mode.setCurrentIndex(idx)
        self.exercise_panel._on_browse_video_clicked()

    def _on_frame_ready(self, q_img, metrics, fps) -> None:
        self.camera_view.set_frame(q_img, fps)
        if metrics:
            self.feedback_panel.update_metrics(metrics)
            self.results_panel.update_metrics(metrics)

    def _on_worker_error(self, message: str) -> None:
        logger.error("PoseWorker error: %s", message)
        self._on_stop_session()
        QMessageBox.critical(self, "Camera / Model Error", message)

    def _show_workout_history(self) -> None:
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
        from ui.login_dialog import LoginDialog

        # Stop active session if running
        self._on_stop_session()

        login_dlg = LoginDialog(self)
        if login_dlg.exec() == LoginDialog.Accepted and login_dlg.authenticated_user:
            self._user = login_dlg.authenticated_user
            username = self._user.get("username", "Guest")

            # Propagate updated user across all screen modules
            self.home_screen.set_user(self._user)
            self.upload_screen.set_user(self._user)
            self.editor_screen.set_user(self._user)
            self.comparison_screen.set_user(self._user)

            self._update_auth_ui()
            self._update_status_bar(f"Switched account to {username}.")

    def closeEvent(self, event) -> None:
        self._on_stop_session()
        event.accept()
