"""Sidebar panel for selecting exercises, camera hardware, and session control."""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from exercises.registry import registry
from services.camera import CameraService


class ExercisePanel(QWidget):
    """Control panel for exercise setup and session lifecycle."""

    exercise_changed = Signal(str)
    camera_changed = Signal(int)
    start_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(280)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # 1. Exercise Selection Group
        ex_group = QGroupBox("Exercise")
        ex_layout = QVBoxLayout(ex_group)
        ex_layout.setSpacing(8)

        self.combo_exercise = QComboBox()
        self.combo_exercise.addItems(registry.get_names())
        self.combo_exercise.currentTextChanged.connect(self._on_exercise_changed)
        ex_layout.addWidget(QLabel("Select Workout:"))
        ex_layout.addWidget(self.combo_exercise)

        self.lbl_description = QLabel()
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet("color: #8b949e; font-size: 11px;")
        ex_layout.addWidget(self.lbl_description)
        layout.addWidget(ex_group)

        # 2. Camera Hardware Group
        cam_group = QGroupBox("Video Source")
        cam_layout = QVBoxLayout(cam_group)
        cam_layout.setSpacing(8)

        self.combo_camera = QComboBox()
        available_cams = CameraService.list_available_cameras(3)
        for cam_id in available_cams:
            self.combo_camera.addItem(f"Camera Device {cam_id}", cam_id)
        self.combo_camera.currentIndexChanged.connect(self._on_camera_changed)
        cam_layout.addWidget(QLabel("Camera Device:"))
        cam_layout.addWidget(self.combo_camera)
        layout.addWidget(cam_group)

        # 3. Session Controls Group
        ctrl_group = QGroupBox("Session Controls")
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(10)

        self.btn_start = QPushButton("▶  Start Session")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.start_requested.emit)
        ctrl_layout.addWidget(self.btn_start)

        h_ctrl = QHBoxLayout()
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.clicked.connect(self.pause_requested.emit)
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_stop.setEnabled(False)

        h_ctrl.addWidget(self.btn_pause)
        h_ctrl.addWidget(self.btn_stop)
        ctrl_layout.addLayout(h_ctrl)

        self.btn_reset = QPushButton("↺  Reset Reps")
        self.btn_reset.setObjectName("btn_reset")
        self.btn_reset.clicked.connect(self.reset_requested.emit)
        ctrl_layout.addWidget(self.btn_reset)

        layout.addWidget(ctrl_group)

        # Spacer to push everything to top
        layout.addStretch()

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

    def _on_camera_changed(self, index: int) -> None:
        cam_id = self.combo_camera.currentData()
        if cam_id is not None:
            self.camera_changed.emit(int(cam_id))

    def set_session_running(self, running: bool) -> None:
        """Updates button states according to active session state."""
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running)
        self.btn_stop.setEnabled(running)
        self.combo_camera.setEnabled(not running)

    def set_paused_state(self, is_paused: bool) -> None:
        """Updates pause button text."""
        self.btn_pause.setText("▶ Resume" if is_paused else "⏸ Pause")
