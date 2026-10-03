"""Video Editor Screen for trimming athletic movement windows and cropping camera angles."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from services.theme import THEME
from services.video_editor import video_editor
from services.video_service import video_service

logger = logging.getLogger(__name__)


class CropOverlayCanvas(QWidget):
    """Viewport rendering video frame with an interactive draggable crop rectangle."""

    crop_changed = Signal(int, int, int, int)  # x, y, w, h in native video pixels

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 320)
        self._frame: Optional[np.ndarray] = None
        self._pixmap: Optional[QPixmap] = None

        self._native_w: int = 1920
        self._native_h: int = 1080

        # Normalized crop coordinates [0.0 - 1.0]
        self._crop_x_norm: float = 0.0
        self._crop_y_norm: float = 0.0
        self._crop_w_norm: float = 1.0
        self._crop_h_norm: float = 1.0

        self._is_dragging: bool = False
        self._drag_start: QPoint = QPoint()

    def set_frame(self, frame: np.ndarray) -> None:
        self._frame = frame
        self._native_h, self._native_w = frame.shape[:2]

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self._pixmap = QPixmap.fromImage(q_img)
        self.update()

    def set_crop_normalized(self, x: float, y: float, w: float, h: float) -> None:
        self._crop_x_norm = max(0.0, min(x, 0.95))
        self._crop_y_norm = max(0.0, min(y, 0.95))
        self._crop_w_norm = max(0.05, min(w, 1.0 - self._crop_x_norm))
        self._crop_h_norm = max(0.05, min(h, 1.0 - self._crop_y_norm))
        self._emit_crop_native()
        self.update()

    def reset_crop(self) -> None:
        self.set_crop_normalized(0.0, 0.0, 1.0, 1.0)

    def get_native_crop_rect(self) -> Tuple[int, int, int, int]:
        x = int(self._crop_x_norm * self._native_w)
        y = int(self._crop_y_norm * self._native_h)
        w = int(self._crop_w_norm * self._native_w)
        h = int(self._crop_h_norm * self._native_h)
        return x, y, w, h

    def _emit_crop_native(self) -> None:
        x, y, w, h = self.get_native_crop_rect()
        self.crop_changed.emit(x, y, w, h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(THEME.BG_BASE))

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ox = (self.width() - scaled.width()) // 2
            oy = (self.height() - scaled.height()) // 2
            painter.drawPixmap(ox, oy, scaled)

            # Draw Crop Box Overlay
            cx = ox + int(self._crop_x_norm * scaled.width())
            cy = oy + int(self._crop_y_norm * scaled.height())
            cw = int(self._crop_w_norm * scaled.width())
            ch = int(self._crop_h_norm * scaled.height())
            crop_rect = QRect(cx, cy, cw, ch)

            # Dim exterior region
            dim_color = QColor(9, 9, 11, 150)
            painter.fillRect(ox, oy, scaled.width(), cy - oy, dim_color)  # Top
            painter.fillRect(ox, cy + ch, scaled.width(), (oy + scaled.height()) - (cy + ch), dim_color)  # Bottom
            painter.fillRect(ox, cy, cx - ox, ch, dim_color)  # Left
            painter.fillRect(cx + cw, cy, (ox + scaled.width()) - (cx + cw), ch, dim_color)  # Right

            # Crop boundary outline
            pen = QPen(QColor(THEME.PRIMARY_COLOR), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(crop_rect)

            # Corner handles
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(THEME.PRIMARY_COLOR))
            handle_size = 8
            painter.drawRect(cx - handle_size // 2, cy - handle_size // 2, handle_size, handle_size)
            painter.drawRect(cx + cw - handle_size // 2, cy - handle_size // 2, handle_size, handle_size)
            painter.drawRect(cx - handle_size // 2, cy + ch - handle_size // 2, handle_size, handle_size)
            painter.drawRect(cx + cw - handle_size // 2, cy + ch - handle_size // 2, handle_size, handle_size)

        else:
            painter.setPen(QColor(THEME.TEXT_MUTED))
            painter.setFont(QFont("Orbitron", 12, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, "NO ATHLETIC VIDEO LOADED\nChoose local file or select from Vault")

        # Frame outline
        painter.setPen(QPen(QColor(THEME.BORDER_COLOR), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), THEME.radius_int, THEME.radius_int)


class EditorScreen(QWidget):
    """Full screen for trimming movement duration and cropping video bounding boxes."""

    navigate_to = Signal(str)  # 'home', 'upload', 'compare', 'drill'
    send_to_compare = Signal(str)  # video path

    def __init__(self, user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user or {"id": None, "username": "Guest"}
        self._video_path: Optional[str] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._total_frames: int = 0
        self._fps: float = 30.0
        self._duration: float = 0.0
        self._is_playing: bool = False

        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._on_play_step)

        self._init_ui()

    def set_user(self, user: Dict[str, Any]) -> None:
        self._user = user

    def load_video(self, file_path: str) -> None:
        """Loads video file into editor."""
        if not Path(file_path).exists():
            QMessageBox.warning(self, "File Not Found", f"Cannot locate: {file_path}")
            return

        self._video_path = file_path
        if self._cap:
            self._cap.release()

        self._cap = cv2.VideoCapture(file_path)
        if not self._cap.isOpened():
            QMessageBox.critical(self, "Load Error", "Failed to open video file.")
            return

        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._duration = self._total_frames / self._fps if self._fps > 0 else 0.0

        self.slider.setRange(0, max(0, self._total_frames - 1))
        self.slider.setValue(0)

        # Trimming bounds
        self.spin_start.setRange(0.0, self._duration)
        self.spin_start.setValue(0.0)
        self.spin_end.setRange(0.0, self._duration)
        self.spin_end.setValue(self._duration)

        # Update info labels
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.lbl_info.setText(f"{Path(file_path).name}  |  {w}x{h} @ {self._fps:.0f}fps  |  {self._duration:.2f}s")
        self.canvas.reset_crop()

        self._show_frame_at_index(0)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Top Navigation Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 10px 14px;"
        )
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(4, 2, 4, 2)

        btn_home = QPushButton("< BACK TO HOME")
        btn_home.clicked.connect(lambda: self.navigate_to.emit("home"))
        tb_layout.addWidget(btn_home)

        lbl_title = QLabel("BIOMECHANICAL VIDEO TRIM & CROP STUDIO")
        lbl_title.setStyleSheet(
            f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 16px; font-weight: 800; letter-spacing: 1.2px; margin-left: 10px;"
        )
        tb_layout.addWidget(lbl_title)
        tb_layout.addStretch()

        btn_vault = QPushButton("UPLOAD VAULT")
        btn_vault.clicked.connect(lambda: self.navigate_to.emit("upload"))
        tb_layout.addWidget(btn_vault)

        btn_compare = QPushButton("PRO COMPARISON")
        btn_compare.clicked.connect(lambda: self.navigate_to.emit("compare"))
        tb_layout.addWidget(btn_compare)

        main_layout.addWidget(top_bar)

        # 2. Source Loader Bar
        load_bar = QFrame()
        load_bar.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 8px 14px;"
        )
        lb_layout = QHBoxLayout(load_bar)
        lb_layout.setSpacing(10)

        btn_browse = QPushButton("CHOOSE LOCAL VIDEO...")
        btn_browse.clicked.connect(self._on_browse_local)
        lb_layout.addWidget(btn_browse)

        self.combo_vault = QComboBox()
        self.combo_vault.setMinimumWidth(220)
        self.combo_vault.addItem("-- Select from Athlete Vault --", "")
        self.combo_vault.currentIndexChanged.connect(self._on_vault_selected)
        lb_layout.addWidget(self.combo_vault)

        self.lbl_info = QLabel("No video loaded")
        self.lbl_info.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 12px; font-weight: 700;"
        )
        lb_layout.addWidget(self.lbl_info, stretch=1)
        main_layout.addWidget(load_bar)

        # 3. Main Center Split (Canvas Viewport on Left, Control Toolbox on Right)
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(14)

        # Left Column: Canvas & Scrubber
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.canvas = CropOverlayCanvas(self)
        self.canvas.crop_changed.connect(self._on_crop_coords_changed)
        left_layout.addWidget(self.canvas, stretch=1)

        # Scrubber bar
        scrub_box = QFrame()
        scrub_box.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 8px;"
        )
        sb_layout = QHBoxLayout(scrub_box)
        sb_layout.setSpacing(10)

        self.btn_play = QPushButton("PLAY")
        self.btn_play.setFixedWidth(70)
        self.btn_play.clicked.connect(self._toggle_play)
        sb_layout.addWidget(self.btn_play)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        sb_layout.addWidget(self.slider, stretch=1)

        self.lbl_timecode = QLabel("00:00.00 / 00:00.00")
        self.lbl_timecode.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 12px; font-weight: 800;"
        )
        sb_layout.addWidget(self.lbl_timecode)
        left_layout.addWidget(scrub_box)

        split_layout.addWidget(left_col, stretch=1)

        # Right Column: Toolset (Trim + Crop)
        tools_col = QWidget()
        t_layout = QVBoxLayout(tools_col)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(10)

        # Group 1: Trimming Controls
        trim_group = QGroupBox("VIDEO TEMPORAL TRIMMING")
        tg_layout = QVBoxLayout(trim_group)
        tg_layout.setSpacing(8)

        h_start = QHBoxLayout()
        lbl_st = QLabel("Start:")
        lbl_st.setFixedWidth(40)
        lbl_st.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setDecimals(2)
        self.spin_start.setSingleStep(0.1)
        btn_set_start = QPushButton("SET IN")
        btn_set_start.setFixedWidth(72)
        btn_set_start.setStyleSheet(f"font-size: 10px; font-weight: 800; padding: 4px;")
        btn_set_start.clicked.connect(self._mark_start)
        h_start.addWidget(lbl_st)
        h_start.addWidget(self.spin_start, stretch=1)
        h_start.addWidget(btn_set_start)
        tg_layout.addLayout(h_start)

        h_end = QHBoxLayout()
        lbl_et = QLabel("End:")
        lbl_et.setFixedWidth(40)
        lbl_et.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        self.spin_end = QDoubleSpinBox()
        self.spin_end.setDecimals(2)
        self.spin_end.setSingleStep(0.1)
        btn_set_end = QPushButton("SET OUT")
        btn_set_end.setFixedWidth(72)
        btn_set_end.setStyleSheet(f"font-size: 10px; font-weight: 800; padding: 4px;")
        btn_set_end.clicked.connect(self._mark_end)
        h_end.addWidget(lbl_et)
        h_end.addWidget(self.spin_end, stretch=1)
        h_end.addWidget(btn_set_end)
        tg_layout.addLayout(h_end)

        self.lbl_trim_dur = QLabel("Trim Window: 0.00s")
        self.lbl_trim_dur.setStyleSheet(f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 700;")
        tg_layout.addWidget(self.lbl_trim_dur)
        self.spin_start.valueChanged.connect(self._update_trim_label)
        self.spin_end.valueChanged.connect(self._update_trim_label)

        t_layout.addWidget(trim_group)

        # Group 2: Spatial Cropping Controls
        crop_group = QGroupBox("CAMERA ANGLE CROPPING")
        cg_layout = QVBoxLayout(crop_group)
        cg_layout.setSpacing(8)

        # Crop Presets in 2x2 grid
        grid_presets = QGridLayout()
        grid_presets.setSpacing(6)
        btn_p1 = QPushButton("16:9 WIDE")
        btn_p1.setFixedHeight(28)
        btn_p1.clicked.connect(lambda: self.canvas.set_crop_normalized(0.1, 0.1, 0.8, 0.45))
        btn_p2 = QPushButton("9:16 VERTICAL")
        btn_p2.setFixedHeight(28)
        btn_p2.clicked.connect(lambda: self.canvas.set_crop_normalized(0.3, 0.05, 0.4, 0.9))
        btn_p3 = QPushButton("1:1 SQUARE")
        btn_p3.setFixedHeight(28)
        btn_p3.clicked.connect(lambda: self.canvas.set_crop_normalized(0.2, 0.1, 0.6, 0.6))
        btn_p4 = QPushButton("RESET CROP")
        btn_p4.setFixedHeight(28)
        btn_p4.clicked.connect(self.canvas.reset_crop)

        grid_presets.addWidget(btn_p1, 0, 0)
        grid_presets.addWidget(btn_p2, 0, 1)
        grid_presets.addWidget(btn_p3, 1, 0)
        grid_presets.addWidget(btn_p4, 1, 1)
        cg_layout.addLayout(grid_presets)

        self.lbl_crop_coords = QLabel("Crop Area: 1920 x 1080 (0, 0)")
        self.lbl_crop_coords.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 700;"
        )
        cg_layout.addWidget(self.lbl_crop_coords)
        t_layout.addWidget(crop_group)

        # Group 3: Export & Comparison Actions
        act_group = QGroupBox("EXPORT & WORKFLOW")
        ag_layout = QVBoxLayout(act_group)
        ag_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        ag_layout.addWidget(self.progress_bar)

        self.btn_apply_trim = QPushButton("APPLY TRIM")
        self.btn_apply_trim.clicked.connect(self._on_apply_trim)
        ag_layout.addWidget(self.btn_apply_trim)

        self.btn_apply_crop = QPushButton("APPLY CROP")
        self.btn_apply_crop.clicked.connect(self._on_apply_crop)
        ag_layout.addWidget(self.btn_apply_crop)

        self.btn_apply_both = QPushButton("APPLY BOTH (TRIM & CROP)")
        self.btn_apply_both.setObjectName("btn_start")
        self.btn_apply_both.setMinimumHeight(44)
        self.btn_apply_both.clicked.connect(self._on_apply_both)
        ag_layout.addWidget(self.btn_apply_both)

        self.btn_send_compare = QPushButton("SEND TO PRO COMPARISON >")
        self.btn_send_compare.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; border: 1px solid {THEME.COLOR_SUCCESS_BRIGHT}; "
            f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-weight: 800; min-height: 40px; border-radius: {THEME.BORDER_RADIUS_SM}; }}"
            f"QPushButton:hover {{ background-color: {THEME.COLOR_SUCCESS_BRIGHT}; color: #09090b; }}"
        )
        self.btn_send_compare.clicked.connect(self._on_send_to_comparison)
        ag_layout.addWidget(self.btn_send_compare)

        t_layout.addWidget(act_group)
        t_layout.addStretch()

        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFixedWidth(350)
        tools_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tools_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        tools_scroll.setWidget(tools_col)
        split_layout.addWidget(tools_scroll)
        main_layout.addWidget(split_widget, stretch=1)

        self.refresh_vault_combo()

    def refresh_vault_combo(self) -> None:
        """Populates vault dropdown with current server videos."""
        self.combo_vault.blockSignals(True)
        self.combo_vault.clear()
        self.combo_vault.addItem("-- Select from Athlete Vault --", "")
        vids = video_service.get_library(category=None, user_id=self._user.get("id"))
        for v in vids:
            title = v.get("title", "Untitled")
            sport = v.get("sport", "")
            cat = "PRO" if v.get("category") == "pro" else "USER"
            self.combo_vault.addItem(f"[{cat}] {title} ({sport})", v.get("file_path"))
        self.combo_vault.blockSignals(False)

    def _on_browse_local(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Athletic Video to Edit",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)",
        )
        if path:
            self.load_video(path)

    def _on_vault_selected(self, idx: int) -> None:
        path = self.combo_vault.currentData()
        if path:
            self.load_video(path)

    def _toggle_play(self) -> None:
        if not self._cap or not self._cap.isOpened():
            return
        self._is_playing = not self._is_playing
        self.btn_play.setText("PAUSE" if self._is_playing else "PLAY")
        if self._is_playing:
            interval = int(1000 / max(10.0, self._fps))
            self._play_timer.start(interval)
        else:
            self._play_timer.stop()

    def _on_play_step(self) -> None:
        curr = self.slider.value()
        next_frame = curr + 1
        if next_frame >= self._total_frames:
            next_frame = 0
        self.slider.setValue(next_frame)
        self._show_frame_at_index(next_frame)

    def _on_slider_moved(self, val: int) -> None:
        self._show_frame_at_index(val)

    def _show_frame_at_index(self, idx: int) -> None:
        if not self._cap or not self._cap.isOpened():
            return
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        success, frame = self._cap.read()
        if success and frame is not None:
            self.canvas.set_frame(frame)
            current_sec = idx / self._fps if self._fps > 0 else 0.0
            self.lbl_timecode.setText(f"{self._format_time(current_sec)} / {self._format_time(self._duration)}")

    @staticmethod
    def _format_time(sec: float) -> str:
        mins = int(sec // 60)
        s = sec % 60
        return f"{mins:02d}:{s:05.2f}"

    def _mark_start(self) -> None:
        curr_sec = self.slider.value() / self._fps if self._fps > 0 else 0.0
        self.spin_start.setValue(curr_sec)

    def _mark_end(self) -> None:
        curr_sec = self.slider.value() / self._fps if self._fps > 0 else 0.0
        self.spin_end.setValue(curr_sec)

    def _update_trim_label(self) -> None:
        dur = max(0.0, self.spin_end.value() - self.spin_start.value())
        frames = int(dur * self._fps)
        self.lbl_trim_dur.setText(f"Trim Window: {dur:.2f}s ({frames} frames)")

    def _on_crop_coords_changed(self, x: int, y: int, w: int, h: int) -> None:
        self.lbl_crop_coords.setText(f"Crop Area: {w} x {h} (X:{x}, Y:{y})")

    def _on_apply_trim(self) -> None:
        if not self._video_path:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Trimmed Video", "trimmed_movement.mp4", "MP4 Video (*.mp4)")
        if not out_path:
            return

        self._show_progress(True)
        ok, msg = video_editor.trim_video(
            self._video_path,
            out_path,
            self.spin_start.value(),
            self.spin_end.value(),
            progress_callback=lambda p: self.progress_bar.setValue(int(p * 100)),
        )
        self._show_progress(False)
        if ok:
            QMessageBox.information(self, "Trim Success", f"Trimmed video saved successfully:\n{out_path}")
            self.load_video(out_path)
        else:
            QMessageBox.critical(self, "Trim Failed", msg)

    def _on_apply_crop(self) -> None:
        if not self._video_path:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Cropped Video", "cropped_angle.mp4", "MP4 Video (*.mp4)")
        if not out_path:
            return

        x, y, w, h = self.canvas.get_native_crop_rect()
        self._show_progress(True)
        ok, msg = video_editor.crop_video(
            self._video_path,
            out_path,
            x, y, w, h,
            progress_callback=lambda p: self.progress_bar.setValue(int(p * 100)),
        )
        self._show_progress(False)
        if ok:
            QMessageBox.information(self, "Crop Success", f"Cropped video saved successfully:\n{out_path}")
            self.load_video(out_path)
        else:
            QMessageBox.critical(self, "Crop Failed", msg)

    def _on_apply_both(self) -> None:
        """Trims then crops in sequence."""
        if not self._video_path:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Trimmed & Cropped Video", "athletic_clip_final.mp4", "MP4 Video (*.mp4)")
        if not out_path:
            return

        temp_trim = str(Path(out_path).parent / f"temp_{Path(out_path).name}")
        self._show_progress(True)

        ok1, msg1 = video_editor.trim_video(
            self._video_path,
            temp_trim,
            self.spin_start.value(),
            self.spin_end.value(),
            progress_callback=lambda p: self.progress_bar.setValue(int(p * 50)),
        )
        if not ok1:
            self._show_progress(False)
            QMessageBox.critical(self, "Trim Step Failed", msg1)
            return

        x, y, w, h = self.canvas.get_native_crop_rect()
        ok2, msg2 = video_editor.crop_video(
            temp_trim,
            out_path,
            x, y, w, h,
            progress_callback=lambda p: self.progress_bar.setValue(50 + int(p * 50)),
        )
        self._show_progress(False)

        if Path(temp_trim).exists():
            try:
                os.remove(temp_trim)
            except Exception:
                pass

        if ok2:
            QMessageBox.information(self, "Processing Complete", f"Saved final athletic clip:\n{out_path}")
            self.load_video(out_path)
        else:
            QMessageBox.critical(self, "Crop Step Failed", msg2)

    def _on_send_to_comparison(self) -> None:
        if not self._video_path:
            QMessageBox.warning(self, "No Video", "Please load a video clip first.")
            return
        self.send_to_compare.emit(self._video_path)

    def _show_progress(self, show: bool) -> None:
        self.progress_bar.setVisible(show)
        self.progress_bar.setValue(0)
