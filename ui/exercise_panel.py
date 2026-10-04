"""Sidebar panel for selecting athletic movement patterns, optical input sources, and drill telemetry."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from exercises.registry import registry
from services.camera import CameraService
from services.theme import THEME


class ExercisePanel(QWidget):
    """Control panel for exercise setup, optical video source selection, and session lifecycle."""

    exercise_changed = Signal(str)
    camera_changed = Signal(int)
    video_selected = Signal(str, float, bool)
    source_changed = Signal(object, str, float, bool)  # source, mode, speed, loop
    start_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(360)
        self._selected_video_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # 1. Exercise Selection Group
        ex_group = QGroupBox("ATHLETIC DRILL")
        ex_layout = QVBoxLayout(ex_group)
        ex_layout.setSpacing(8)

        lbl_workout = QLabel("Select Movement Pattern:")
        lbl_workout.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        ex_layout.addWidget(lbl_workout)

        self.combo_exercise = QComboBox()
        self.combo_exercise.addItems(registry.get_names())
        self.combo_exercise.currentTextChanged.connect(self._on_exercise_changed)
        ex_layout.addWidget(self.combo_exercise)

        self.lbl_description = QLabel()
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 12px; padding: 4px 2px;")
        ex_layout.addWidget(self.lbl_description)
        layout.addWidget(ex_group)

        # 2. Input Source Modality Group (Live Optical Sensor OR Video Upload)
        source_group = QGroupBox("INPUT SOURCE")
        source_layout = QVBoxLayout(source_group)
        source_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        source_layout.setSpacing(10)

        lbl_mode = QLabel("Input Modality:")
        lbl_mode.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        source_layout.addWidget(lbl_mode)

        self.combo_source_mode = QComboBox()
        self.combo_source_mode.addItem("Live Camera", "camera")
        self.combo_source_mode.addItem("Upload Athletic Video", "video")
        self.combo_source_mode.currentIndexChanged.connect(self._on_source_mode_changed)
        source_layout.addWidget(self.combo_source_mode)

        # 2A. Sub-panel: Live Camera Device
        self.camera_subpanel = QWidget()
        cam_sub_layout = QVBoxLayout(self.camera_subpanel)
        cam_sub_layout.setContentsMargins(0, 4, 0, 0)
        cam_sub_layout.setSpacing(6)

        lbl_camera = QLabel("Tracking Camera Device:")
        lbl_camera.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        cam_sub_layout.addWidget(lbl_camera)

        self.combo_camera = QComboBox()
        available_cams = CameraService.list_available_cameras(3)
        for cam_id in available_cams:
            self.combo_camera.addItem(f"Sensor Device {cam_id}", cam_id)
        self.combo_camera.currentIndexChanged.connect(self._on_camera_changed)
        cam_sub_layout.addWidget(self.combo_camera)
        source_layout.addWidget(self.camera_subpanel)

        # 2B. Sub-panel: Uploaded Video File
        self.video_subpanel = QWidget()
        vid_sub_layout = QVBoxLayout(self.video_subpanel)
        vid_sub_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        vid_sub_layout.setContentsMargins(0, 4, 0, 0)
        vid_sub_layout.setSpacing(8)

        lbl_video = QLabel("Athlete Training Video Clip:")
        lbl_video.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        vid_sub_layout.addWidget(lbl_video)

        self.btn_select_video = QPushButton("CHOOSE VIDEO FILE...")
        self.btn_select_video.setObjectName("btn_select_video")
        self.btn_select_video.setMinimumHeight(44)
        self.btn_select_video.setStyleSheet(
            f"QPushButton#btn_select_video {{ "
            f"border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"color: #ffffff; "
            f"font-size: 12px; font-weight: 800; letter-spacing: 1px; "
            f"}}"
        )
        self.btn_select_video.clicked.connect(self._on_browse_video_clicked)
        vid_sub_layout.addWidget(self.btn_select_video)

        self.lbl_video_filename = QLabel("No video selected")
        self.lbl_video_filename.setWordWrap(True)
        self.lbl_video_filename.setMinimumHeight(46)
        self.lbl_video_filename.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"padding: 8px; background-color: {THEME.BG_INPUT}; border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"border: 1px solid {THEME.BORDER_COLOR};"
        )
        vid_sub_layout.addWidget(self.lbl_video_filename)

        # Speed Dropdown
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(6)
        lbl_speed = QLabel("Playback:")
        lbl_speed.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        self.combo_speed = QComboBox()
        self.combo_speed.addItem("1.0x (Normal)", 1.0)
        self.combo_speed.addItem("0.5x (Slow-Mo)", 0.5)
        self.combo_speed.addItem("0.25x (Precision)", 0.25)
        self.combo_speed.currentIndexChanged.connect(self._on_video_settings_changed)
        speed_layout.addWidget(lbl_speed)
        speed_layout.addWidget(self.combo_speed)
        vid_sub_layout.addLayout(speed_layout)

        # Loop Checkbox
        self.chk_loop = QCheckBox("Loop video clip")
        self.chk_loop.setChecked(True)
        self.chk_loop.toggled.connect(self._on_video_settings_changed)
        vid_sub_layout.addWidget(self.chk_loop)

        self.video_subpanel.setVisible(False)
        source_layout.addWidget(self.video_subpanel)

        layout.addWidget(source_group)

        # 3. Session Controls Group
        ctrl_group = QGroupBox("DRILL TELEMETRY")
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        ctrl_layout.setSpacing(10)

        # Recording Options
        self.chk_auto_record = QCheckBox("Record Movement to Server Vault")
        self.chk_auto_record.setChecked(True)
        self.chk_auto_record.setStyleSheet(
            f"QCheckBox {{ color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 2px 0; }}"
        )
        ctrl_layout.addWidget(self.chk_auto_record)

        self.lbl_record_status = QLabel("● SERVER AUTO-ARCHIVE READY")
        self.lbl_record_status.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 10px; font-weight: 800; letter-spacing: 0.8px; padding-left: 2px;"
        )
        ctrl_layout.addWidget(self.lbl_record_status)

        self.btn_start = QPushButton("START RECORDING")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setMinimumHeight(52)
        self.btn_start.clicked.connect(self.start_requested.emit)
        ctrl_layout.addWidget(self.btn_start)

        h_ctrl = QHBoxLayout()
        h_ctrl.setSpacing(8)
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setMinimumHeight(42)
        self.btn_pause.clicked.connect(self.pause_requested.emit)
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton("END DRILL")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setMinimumHeight(42)
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_stop.setEnabled(False)

        h_ctrl.addWidget(self.btn_pause)
        h_ctrl.addWidget(self.btn_stop)
        ctrl_layout.addLayout(h_ctrl)

        self.btn_reset = QPushButton("RESET TELEMETRY")
        self.btn_reset.setObjectName("btn_reset")
        self.btn_reset.setMinimumHeight(40)
        self.btn_reset.clicked.connect(self.reset_requested.emit)
        ctrl_layout.addWidget(self.btn_reset)

        layout.addWidget(ctrl_group)
        layout.addStretch()

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        # Initialize description
        self._update_description(self.combo_exercise.currentText())

    def _on_exercise_changed(self, text: str) -> None:
        self._update_description(text)
        self.exercise_changed.emit(text)

    def _update_description(self, exercise_name: str) -> None:
        try:
            ex = registry.create(exercise_name)
            self.lbl_description.setText(ex.description)
        except Exception:
            self.lbl_description.setText("")

    def _on_source_mode_changed(self, index: int) -> None:
        mode = self.combo_source_mode.currentData()
        is_video = (mode == "video")
        self.camera_subpanel.setVisible(not is_video)
        self.video_subpanel.setVisible(is_video)
        self._emit_source_changed()

    def _on_camera_changed(self, index: int) -> None:
        cam_id = self.combo_camera.currentData()
        if cam_id is not None:
            self.camera_changed.emit(int(cam_id))
            self._emit_source_changed()

    def _on_browse_video_clicked(self) -> None:
        """Opens file dialog for uploading video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Athlete Training Video Drill",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)",
        )
        if file_path:
            self.set_video_file(file_path)

    def set_video_file(self, file_path: str) -> None:
        """Selects and validates an uploaded video file."""
        self._selected_video_path = file_path
        info = CameraService.get_video_info(file_path)
        if info:
            text = f"{info['name']}\n{info['width']}x{info['height']} @ {info['fps']:.0f}fps ({info['duration_seconds']}s)"
            self.lbl_video_filename.setText(text)
            self.lbl_video_filename.setMinimumHeight(46)
            self.lbl_video_filename.setStyleSheet(
                f"color: {THEME.PRIMARY_COLOR}; font-size: 11px; font-weight: 700; "
                f"font-family: {THEME.FONT_FAMILY_TECH}; padding: 8px; background-color: {THEME.BG_INPUT}; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; border: 1px solid {THEME.PRIMARY_COLOR};"
            )
            self.lbl_video_filename.setToolTip(str(Path(file_path).resolve()))
        else:
            self.lbl_video_filename.setText(Path(file_path).name)

        speed = float(self.combo_speed.currentData() or 1.0)
        loop = self.chk_loop.isChecked()
        self.video_selected.emit(file_path, speed, loop)
        self._emit_source_changed()

    def _on_video_settings_changed(self) -> None:
        self._emit_source_changed()

    def _emit_source_changed(self) -> None:
        info = self.get_current_source_info()
        self.source_changed.emit(info["source"], info["mode"], info["speed"], info["loop"])

    def get_current_source_info(self) -> Dict[str, Any]:
        """Returns the currently active source configuration."""
        mode = self.combo_source_mode.currentData()
        if mode == "video":
            speed = float(self.combo_speed.currentData() or 1.0)
            loop = self.chk_loop.isChecked()
            return {
                "mode": "video",
                "source": self._selected_video_path,
                "speed": speed,
                "loop": loop,
                "name": Path(self._selected_video_path).name if self._selected_video_path else "",
            }
        else:
            cam_id = self.combo_camera.currentData()
            idx = int(cam_id) if cam_id is not None else 0
            return {
                "mode": "camera",
                "source": idx,
                "speed": 1.0,
                "loop": True,
                "name": f"Sensor Device {idx}",
            }

    def is_recording_enabled(self) -> bool:
        """Checks if movement recording to server is active."""
        return self.chk_auto_record.isChecked()

    def set_recording_status(self, is_recording: bool, text: Optional[str] = None) -> None:
        """Updates recording indicator status."""
        if text:
            self.lbl_record_status.setText(text)
        elif is_recording:
            self.lbl_record_status.setText("● RECORDING MOVEMENT TO SERVER...")
        else:
            self.lbl_record_status.setText("● SERVER AUTO-ARCHIVE READY")

        color = THEME.COLOR_DANGER_BRIGHT if is_recording else THEME.TEXT_MUTED
        self.lbl_record_status.setStyleSheet(
            f"color: {color}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 10px; font-weight: 800; letter-spacing: 0.8px; padding-left: 2px;"
        )

    def set_session_running(self, running: bool) -> None:
        """Updates button states according to active session state."""
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running)
        self.btn_stop.setEnabled(running)
        self.combo_source_mode.setEnabled(not running)
        self.combo_camera.setEnabled(not running)
        self.btn_select_video.setEnabled(not running)
        self.combo_speed.setEnabled(not running)
        self.chk_loop.setEnabled(not running)
        self.chk_auto_record.setEnabled(not running)

        if running and self.chk_auto_record.isChecked():
            self.lbl_record_status.setText("● RECORDING MOVEMENT TO SERVER...")
            self.lbl_record_status.setStyleSheet(
                f"color: {THEME.COLOR_DANGER_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; "
                f"font-size: 10px; font-weight: 800; letter-spacing: 0.8px; padding-left: 2px;"
            )
        else:
            self.lbl_record_status.setText("● SERVER AUTO-ARCHIVE READY")
            self.lbl_record_status.setStyleSheet(
                f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; "
                f"font-size: 10px; font-weight: 800; letter-spacing: 0.8px; padding-left: 2px;"
            )

    def set_paused_state(self, is_paused: bool) -> None:
        """Updates pause button text."""
        self.btn_pause.setText("▶" if is_paused else "⏸")
