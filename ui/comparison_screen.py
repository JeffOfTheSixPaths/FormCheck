"""Comparison screen providing dual video loading (local/online), direct skeleton overlay,
and biomechanical variance analysis across Arms, Shoulders, Hips, and Legs."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.comparison_engine import ComparisonMetrics, comparison_engine
from services.geometry_cache import geometry_cache
from services.pro_similarity_service import pro_similarity_service
from services.theme import THEME
from services.video_service import video_service
from ui.pro_recommendation_dialog import ProRecommendationDialog

logger = logging.getLogger(__name__)


class ComparisonViewport(QWidget):
    """Viewport rendering either direct skeleton overlay or synchronized side-by-side video feeds."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(600, 360)

        self._mode: str = "overlay"  # "overlay" or "split"
        self._overlay_pixmap: Optional[QPixmap] = None
        self._user_pixmap: Optional[QPixmap] = None
        self._pro_pixmap: Optional[QPixmap] = None

    def set_display_mode(self, mode: str) -> None:
        self._mode = mode
        self.update()

    def set_overlay_frame(self, frame: np.ndarray) -> None:
        h, w, ch = frame.shape
        q_img = QImage(frame.data, w, h, ch * w, QImage.Format_BGR888)
        self._overlay_pixmap = QPixmap.fromImage(q_img)
        self.update()

    def set_split_frames(self, user_frame: Optional[np.ndarray], pro_frame: Optional[np.ndarray]) -> None:
        if user_frame is not None:
            uh, uw, uch = user_frame.shape
            self._user_pixmap = QPixmap.fromImage(QImage(user_frame.data, uw, uh, uch * uw, QImage.Format_BGR888))
        else:
            self._user_pixmap = None

        if pro_frame is not None:
            ph, pw, pch = pro_frame.shape
            self._pro_pixmap = QPixmap.fromImage(QImage(pro_frame.data, pw, ph, pch * pw, QImage.Format_BGR888))
        else:
            self._pro_pixmap = None

        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(THEME.BG_BASE))

        if self._mode == "overlay":
            if self._overlay_pixmap and not self._overlay_pixmap.isNull():
                scaled = self._overlay_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ox = (self.width() - scaled.width()) // 2
                oy = (self.height() - scaled.height()) // 2
                painter.drawPixmap(ox, oy, scaled)
            else:
                self._draw_placeholder(painter, "SELECT USER AND REFERENCE VIDEOS TO RUN DIRECT OVERLAY")

        elif self._mode == "split":
            half_w = (self.width() - 8) // 2
            half_h = self.height()
            left_rect = QRect(0, 0, half_w, half_h)
            right_rect = QRect(half_w + 8, 0, half_w, half_h)

            # Left: User
            if self._user_pixmap and not self._user_pixmap.isNull():
                scaled_u = self._user_pixmap.scaled(left_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ux = left_rect.x() + (left_rect.width() - scaled_u.width()) // 2
                uy = left_rect.y() + (left_rect.height() - scaled_u.height()) // 2
                painter.drawPixmap(ux, uy, scaled_u)

                # Label User
                painter.setPen(QColor(THEME.COLOR_DANGER_BRIGHT))
                painter.setFont(QFont("Orbitron", 10, QFont.Bold))
                painter.drawText(ux + 12, uy + 24, "YOUR FORM (USER)")
            else:
                painter.fillRect(left_rect, QColor(THEME.BG_SURFACE))
                painter.setPen(QColor(THEME.TEXT_MUTED))
                painter.drawText(left_rect, Qt.AlignCenter, "NO USER VIDEO LOADED")

            # Right: Pro
            if self._pro_pixmap and not self._pro_pixmap.isNull():
                scaled_p = self._pro_pixmap.scaled(right_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                px = right_rect.x() + (right_rect.width() - scaled_p.width()) // 2
                py = right_rect.y() + (right_rect.height() - scaled_p.height()) // 2
                painter.drawPixmap(px, py, scaled_p)

                # Label Reference Benchmark
                painter.setPen(QColor(THEME.PRIMARY_COLOR))
                painter.setFont(QFont("Orbitron", 10, QFont.Bold))
                painter.drawText(px + 12, py + 24, "REFERENCE BENCHMARK")
            else:
                painter.fillRect(right_rect, QColor(THEME.BG_SURFACE))
                painter.setPen(QColor(THEME.TEXT_MUTED))
                painter.drawText(right_rect, Qt.AlignCenter, "NO REFERENCE VIDEO LOADED")

            # Divider line
            painter.setPen(QPen(QColor(THEME.BORDER_COLOR), 1))
            painter.drawLine(half_w + 4, 0, half_w + 4, self.height())

        # Outer border
        painter.setPen(QPen(QColor(THEME.BORDER_COLOR), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), THEME.radius_int, THEME.radius_int)

    def _draw_placeholder(self, painter: QPainter, text: str) -> None:
        painter.setPen(QColor(THEME.TEXT_MUTED))
        painter.setFont(QFont("Orbitron", 11, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, text)


class SegmentVarianceCard(QFrame):
    """Displays calculated kinematic variance and angular error for a specific body segment."""

    def __init__(self, segment_title: str, accent_color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("seg_card")
        self.setMinimumHeight(86)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"QFrame#seg_card {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 8px 10px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        # Header
        h_head = QHBoxLayout()
        lbl_name = QLabel(segment_title.upper())
        lbl_name.setStyleSheet(
            f"color: {accent_color}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        h_head.addWidget(lbl_name)
        h_head.addStretch()

        self.lbl_score = QLabel("100%")
        self.lbl_score.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 14px; font-weight: 800;"
        )
        h_head.addWidget(self.lbl_score)
        layout.addLayout(h_head)

        # Metrics row: Variance & Mean Delta
        h_stats = QHBoxLayout()
        self.lbl_var = QLabel("Var: 0.00")
        self.lbl_var.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        h_stats.addWidget(self.lbl_var)

        self.lbl_delta = QLabel("Delta: 0.0°")
        self.lbl_delta.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        h_stats.addWidget(self.lbl_delta)
        layout.addLayout(h_stats)

        # Progress bar
        self.bar = QProgressBar()
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background-color: {THEME.BG_INPUT}; border-radius: 4px; border: none; }} "
            f"QProgressBar::chunk {{ background-color: {accent_color}; border-radius: 4px; }}"
        )
        layout.addWidget(self.bar)

        # Joint detail text
        self.lbl_detail = QLabel("Analyzing joint kinematics...")
        self.lbl_detail.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(self.lbl_detail)

    def update_metrics(self, var_val: float, delta_val: float, score: float, details_text: str) -> None:
        self.lbl_score.setText(f"{score:.0f}%")
        self.lbl_var.setText(f"Var: {var_val:.2f}")
        self.lbl_delta.setText(f"Delta: {delta_val:.1f}°")
        self.bar.setValue(int(score))
        self.lbl_detail.setText(details_text)


class ComparisonScreen(QWidget):
    """Screen for loading User vs Pro videos, running dual skeletal overlay, and viewing variance across all 4 segments."""

    navigate_to = Signal(str)  # 'home', 'upload', 'editor', 'drill'

    def __init__(self, user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user or {"id": None, "username": "Guest"}

        self._user_cap: Optional[cv2.VideoCapture] = None
        self._pro_cap: Optional[cv2.VideoCapture] = None

        self._user_path: Optional[str] = None
        self._pro_path: Optional[str] = None

        self._user_geometry: Optional[Dict[str, Any]] = None
        self._pro_geometry: Optional[Dict[str, Any]] = None

        self._user_total_frames: int = 0
        self._pro_total_frames: int = 0
        self._max_frames: int = 0

        self._is_playing: bool = False
        self._playback_speed: float = 1.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_play_step)

        self._init_ui()

    def set_user(self, user: Dict[str, Any]) -> None:
        self._user = user
        self._populate_vault_dropdowns()

    def load_user_video(self, file_path: str) -> None:
        """Loads personal / user athlete video and pre-computed skeletal geometry."""
        if not Path(file_path).exists():
            return
        self._user_path = file_path
        if self._user_cap:
            self._user_cap.release()
        self._user_cap = cv2.VideoCapture(file_path)
        self._user_total_frames = int(self._user_cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Retrieve or pre-compute saved geometry for video
        self._user_geometry = geometry_cache.get_or_compute_geometry(file_path)
        if self._user_geometry and self._user_geometry.get("total_frames"):
            self._user_total_frames = max(self._user_total_frames, self._user_geometry["total_frames"])

        self.lbl_user_loaded.setText(f"Loaded: {Path(file_path).name} ({self._user_total_frames} frames)")

        # Sync combo if present
        for i in range(self.combo_user_vault.count()):
            if self.combo_user_vault.itemData(i) == file_path:
                self.combo_user_vault.blockSignals(True)
                self.combo_user_vault.setCurrentIndex(i)
                self.combo_user_vault.blockSignals(False)
                break

        self._update_timeline_bounds()
        self._render_current_frame()

    def load_pro_video(self, file_path: str) -> None:
        """Loads comparison reference video and pre-computed skeletal geometry."""
        if not Path(file_path).exists():
            return
        self._pro_path = file_path
        if self._pro_cap:
            self._pro_cap.release()
        self._pro_cap = cv2.VideoCapture(file_path)
        self._pro_total_frames = int(self._pro_cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Retrieve or pre-compute saved geometry for reference video
        self._pro_geometry = geometry_cache.get_or_compute_geometry(file_path)
        if self._pro_geometry and self._pro_geometry.get("total_frames"):
            self._pro_total_frames = max(self._pro_total_frames, self._pro_geometry["total_frames"])

        self.lbl_pro_loaded.setText(f"Loaded: {Path(file_path).name} ({self._pro_total_frames} frames)")

        # Sync combo if present
        for i in range(self.combo_pro_vault.count()):
            if self.combo_pro_vault.itemData(i) == file_path:
                self.combo_pro_vault.blockSignals(True)
                self.combo_pro_vault.setCurrentIndex(i)
                self.combo_pro_vault.blockSignals(False)
                break

        self._update_timeline_bounds()
        self._render_current_frame()

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

        lbl_title = QLabel("PRO ATHLETE BIOMECHANICAL COMPARISON & SKELETAL OVERLAY")
        lbl_title.setStyleSheet(
            f"color: {THEME.COLOR_DANGER_BRIGHT}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 15px; font-weight: 800; letter-spacing: 1.2px; margin-left: 10px;"
        )
        tb_layout.addWidget(lbl_title)
        tb_layout.addStretch()

        btn_vault = QPushButton("UPLOAD VAULT")
        btn_vault.clicked.connect(lambda: self.navigate_to.emit("upload"))
        tb_layout.addWidget(btn_vault)

        btn_editor = QPushButton("VIDEO EDITOR")
        btn_editor.clicked.connect(lambda: self.navigate_to.emit("editor"))
        tb_layout.addWidget(btn_editor)

        main_layout.addWidget(top_bar)

        # 2. Dual Video Loading Bar (User Video on Left | AI Pro Match in Center | Pro Video on Right)
        loaders_frame = QFrame()
        loaders_frame.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 10px 14px;"
        )
        lf_layout = QHBoxLayout(loaders_frame)
        lf_layout.setSpacing(14)

        # 2A. User Video Slot
        v_user = QVBoxLayout()
        v_user.setSpacing(6)
        lbl_u_title = QLabel("1. YOUR ATHLETIC VIDEO (PERSONAL / LOCAL / ONLINE):")
        lbl_u_title.setStyleSheet(
            f"color: {THEME.COLOR_DANGER_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800;"
        )
        v_user.addWidget(lbl_u_title)

        h_u_btns = QHBoxLayout()
        btn_u_local = QPushButton("CHOOSE LOCAL...")
        btn_u_local.clicked.connect(self._on_browse_user_local)
        h_u_btns.addWidget(btn_u_local)

        self.combo_user_vault = QComboBox()
        self.combo_user_vault.addItem("-- Choose from Vault --", "")
        self.combo_user_vault.currentIndexChanged.connect(self._on_user_vault_selected)
        h_u_btns.addWidget(self.combo_user_vault)
        v_user.addLayout(h_u_btns)

        self.lbl_user_loaded = QLabel("No user video loaded")
        self.lbl_user_loaded.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px;")
        v_user.addWidget(self.lbl_user_loaded)
        lf_layout.addLayout(v_user, stretch=5)

        # Center AI Matchmaker Column
        v_div1 = QFrame()
        v_div1.setFrameShape(QFrame.VLine)
        v_div1.setStyleSheet(f"color: {THEME.BORDER_COLOR};")
        lf_layout.addWidget(v_div1)

        v_ai_match = QVBoxLayout()
        v_ai_match.setAlignment(Qt.AlignCenter)
        v_ai_match.setSpacing(4)

        lbl_ai_hdr = QLabel("AI FORM BENCHMARK")
        lbl_ai_hdr.setStyleSheet(
            f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;"
        )
        lbl_ai_hdr.setAlignment(Qt.AlignCenter)
        v_ai_match.addWidget(lbl_ai_hdr)

        self.btn_find_pro = QPushButton("AI PRO MATCH")
        self.btn_find_pro.setToolTip("Calculate appendage angle variance cosine similarity and find your closest professional athlete form match")
        self.btn_find_pro.setMinimumHeight(36)
        self.btn_find_pro.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.COLOR_WARNING}; color: #09090b; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 6px 14px; border: none; }} "
            f"QPushButton:hover {{ background-color: {THEME.COLOR_SUCCESS_BRIGHT}; }}"
        )
        self.btn_find_pro.clicked.connect(self._on_find_closest_pro)
        v_ai_match.addWidget(self.btn_find_pro)

        lbl_ai_sub = QLabel("Appendage Variance + Waveform")
        lbl_ai_sub.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 9px;")
        lbl_ai_sub.setAlignment(Qt.AlignCenter)
        v_ai_match.addWidget(lbl_ai_sub)

        lf_layout.addLayout(v_ai_match, stretch=0)

        v_div2 = QFrame()
        v_div2.setFrameShape(QFrame.VLine)
        v_div2.setStyleSheet(f"color: {THEME.BORDER_COLOR};")
        lf_layout.addWidget(v_div2)

        # 2B. Reference / Comparison Video Slot
        v_pro = QVBoxLayout()
        v_pro.setSpacing(6)
        lbl_p_title = QLabel("2. REFERENCE VIDEO TO COMPARE (LOCAL / VAULT):")
        lbl_p_title.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800;"
        )
        v_pro.addWidget(lbl_p_title)

        h_p_btns = QHBoxLayout()
        btn_p_local = QPushButton("CHOOSE LOCAL...")
        btn_p_local.clicked.connect(self._on_browse_pro_local)
        h_p_btns.addWidget(btn_p_local)

        self.combo_pro_vault = QComboBox()
        self.combo_pro_vault.addItem("-- Choose Reference from Vault --", "")
        self.combo_pro_vault.currentIndexChanged.connect(self._on_pro_vault_selected)
        h_p_btns.addWidget(self.combo_pro_vault)
        v_pro.addLayout(h_p_btns)

        self.lbl_pro_loaded = QLabel("No reference video loaded")
        self.lbl_pro_loaded.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px;")
        v_pro.addWidget(self.lbl_pro_loaded)
        lf_layout.addLayout(v_pro, stretch=5)

        main_layout.addWidget(loaders_frame)

        # 3. Main Center Area (Viewport on Left | Variance Dashboard on Right)
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(14)

        # Left: Viewport + Controls
        v_vp = QVBoxLayout()
        v_vp.setContentsMargins(0, 0, 0, 0)
        v_vp.setSpacing(10)

        # Viewport
        self.viewport = ComparisonViewport(self)
        v_vp.addWidget(self.viewport, stretch=1)

        # Scrubber & Transport Box
        trans_frame = QFrame()
        trans_frame.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 8px 12px;"
        )
        tf_layout = QVBoxLayout(trans_frame)
        tf_layout.setSpacing(8)

        # Top row: Mode selector + Play controls
        h_top_ctrl = QHBoxLayout()

        lbl_mode = QLabel("DISPLAY:")
        lbl_mode.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-weight: 700; font-size: 11px;")
        h_top_ctrl.addWidget(lbl_mode)

        self.radio_overlay = QRadioButton("Direct Skeletal Overlay")
        self.radio_overlay.setChecked(True)
        self.radio_overlay.toggled.connect(self._on_mode_toggled)
        h_top_ctrl.addWidget(self.radio_overlay)

        self.radio_split = QRadioButton("Side-by-Side Sync")
        self.radio_split.toggled.connect(self._on_mode_toggled)
        h_top_ctrl.addWidget(self.radio_split)

        h_top_ctrl.addStretch()

        self.btn_play = QPushButton("PLAY")
        self.btn_play.setFixedWidth(70)
        self.btn_play.clicked.connect(self._toggle_play)
        h_top_ctrl.addWidget(self.btn_play)

        btn_step_b = QPushButton("<<")
        btn_step_b.setFixedWidth(36)
        btn_step_b.clicked.connect(lambda: self._step_frame(-1))
        h_top_ctrl.addWidget(btn_step_b)

        btn_step_f = QPushButton(">>")
        btn_step_f.setFixedWidth(36)
        btn_step_f.clicked.connect(lambda: self._step_frame(1))
        h_top_ctrl.addWidget(btn_step_f)

        # Sync offset
        lbl_offset = QLabel("Sync Offset:")
        lbl_offset.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700; margin-left: 8px;")
        h_top_ctrl.addWidget(lbl_offset)
        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(-120, 120)
        self.spin_offset.setValue(0)
        self.spin_offset.valueChanged.connect(self._render_current_frame)
        h_top_ctrl.addWidget(self.spin_offset)

        tf_layout.addLayout(h_top_ctrl)

        # Bottom row: Slider + Frame index readout
        h_slider = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        h_slider.addWidget(self.slider, stretch=1)

        self.lbl_frame_idx = QLabel("Frame 0 / 0")
        self.lbl_frame_idx.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 12px; font-weight: 700;"
        )
        h_slider.addWidget(self.lbl_frame_idx)
        tf_layout.addLayout(h_slider)

        v_vp.addWidget(trans_frame)
        center_layout.addLayout(v_vp, stretch=1)

        # Right: Telemetry & Variance Dashboard
        telemetry_widget = QWidget()
        telem_layout = QVBoxLayout(telemetry_widget)
        telem_layout.setContentsMargins(4, 0, 4, 0)
        telem_layout.setSpacing(10)

        # Overall Match Header
        score_box = QFrame()
        score_box.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 12px;"
        )
        sb_layout = QVBoxLayout(score_box)
        sb_layout.setSpacing(4)
        sb_layout.setAlignment(Qt.AlignCenter)

        lbl_match_title = QLabel("OVERALL FORM MATCH")
        lbl_match_title.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;"
        )
        sb_layout.addWidget(lbl_match_title)

        self.lbl_overall_score = QLabel("100%")
        self.lbl_overall_score.setStyleSheet(
            f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 32px; font-weight: 800;"
        )
        sb_layout.addWidget(self.lbl_overall_score)
        telem_layout.addWidget(score_box)

        # Segment 1: Arms Variance
        self.card_arms = SegmentVarianceCard("Arms & Elbow Angles", THEME.COLOR_SUCCESS_BRIGHT)
        telem_layout.addWidget(self.card_arms)

        # Segment 2: Shoulders Variance
        self.card_shoulders = SegmentVarianceCard("Shoulder Tilt & Arm Axis", THEME.PRIMARY_COLOR)
        telem_layout.addWidget(self.card_shoulders)

        # Segment 3: Hips Variance
        self.card_hips = SegmentVarianceCard("Hip Flexion & Core Hinge", THEME.COLOR_WARNING)
        telem_layout.addWidget(self.card_hips)

        # Segment 4: Legs Variance
        self.card_legs = SegmentVarianceCard("Knee Flexion & Stance Width", THEME.COLOR_DANGER_BRIGHT)
        telem_layout.addWidget(self.card_legs)

        # Coaching Cues Box
        cue_box = QFrame()
        cue_box.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 10px;"
        )
        cb_layout = QVBoxLayout(cue_box)
        cb_layout.setSpacing(4)
        lbl_cue_h = QLabel("BIOMECHANIC COACHING CUE:")
        lbl_cue_h.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 10px; font-weight: 800;"
        )
        cb_layout.addWidget(lbl_cue_h)

        self.lbl_coaching_cue = QLabel("Load user and pro videos to inspect movement variances.")
        self.lbl_coaching_cue.setWordWrap(True)
        self.lbl_coaching_cue.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-size: 12px; font-weight: 600; line-height: 1.3;"
        )
        cb_layout.addWidget(self.lbl_coaching_cue)
        telem_layout.addWidget(cue_box)

        telem_scroll = QScrollArea()
        telem_scroll.setWidgetResizable(True)
        telem_scroll.setFixedWidth(380)
        telem_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        telem_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        telem_scroll.setWidget(telemetry_widget)
        center_layout.addWidget(telem_scroll)
        main_layout.addWidget(center_widget, stretch=1)

        self._populate_vault_dropdowns()

    def _populate_vault_dropdowns(self) -> None:
        """Populates vault dropdowns for User and Pro selections."""
        # User dropdown
        self.combo_user_vault.blockSignals(True)
        self.combo_user_vault.clear()
        self.combo_user_vault.addItem("-- Choose from Vault --", "")
        user_vids = video_service.get_library(category=None, user_id=self._user.get("id"))
        for v in user_vids:
            cat = "USER" if v.get("category") == "personal" else "PRO"
            self.combo_user_vault.addItem(f"[{cat}] {v.get('title')} ({v.get('sport')})", v.get("file_path"))
        self.combo_user_vault.blockSignals(False)

        # Reference comparison dropdown (lists all vault videos freely)
        self.combo_pro_vault.blockSignals(True)
        self.combo_pro_vault.clear()
        self.combo_pro_vault.addItem("-- Choose Reference from Vault --", "")
        all_vids = video_service.get_library(category=None, user_id=self._user.get("id"))
        for v in all_vids:
            self.combo_pro_vault.addItem(f"{v.get('title')} ({v.get('sport')})", v.get("file_path"))
        self.combo_pro_vault.blockSignals(False)

    def _on_browse_user_local(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select User Video", "", "Video Files (*.mp4 *.mov *.avi *.mkv)")
        if p:
            self.load_user_video(p)

    def _on_user_vault_selected(self, idx: int) -> None:
        p = self.combo_user_vault.currentData()
        if p:
            self.load_user_video(p)

    def _on_browse_pro_local(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select Pro Athlete Reference", "", "Video Files (*.mp4 *.mov *.avi *.mkv)")
        if p:
            self.load_pro_video(p)

    def _on_pro_vault_selected(self, idx: int) -> None:
        p = self.combo_pro_vault.currentData()
        if p:
            self.load_pro_video(p)

    def _on_find_closest_pro(self) -> None:
        """Runs appendage angle variance vector cosine similarity & dynamic waveform congruence to recommend the closest pro athlete."""
        if not self._user_path or not Path(self._user_path).exists():
            reply = QMessageBox.question(
                self,
                "Select User Movement Video",
                "No personal movement video loaded yet.\nWould you like to select a video to compare?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._on_browse_user_local()
                if not self._user_path or not Path(self._user_path).exists():
                    return
            else:
                return

        prev_label = self.lbl_user_loaded.text()
        self.lbl_user_loaded.setText("Analyzing 16-joint variance vectors & kinetic sequencing...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        report = None
        try:
            report = pro_similarity_service.recommend_pro_athlete(self._user_path)
        except Exception as e:
            logger.exception("Pro recommendation failed")
            QMessageBox.critical(self, "Analysis Error", f"Failed to analyze movement kinematics:\n{e}")
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.lbl_user_loaded.setText(prev_label)

        if not report or not report.best_match:
            QMessageBox.information(
                self,
                "Insufficient Pose Landmarks",
                "Could not detect clear human skeletal landmarks across enough frames in the video.\n"
                "Please verify that the athlete is fully visible in the frame."
            )
            return

        dialog = ProRecommendationDialog(report, on_load_pro=self.load_pro_video, parent=self)
        dialog.exec()

    def _update_timeline_bounds(self) -> None:
        self._max_frames = max(self._user_total_frames, self._pro_total_frames)
        self.slider.setRange(0, max(0, self._max_frames - 1))
        self.slider.setValue(0)

    def _on_mode_toggled(self) -> None:
        mode = "overlay" if self.radio_overlay.isChecked() else "split"
        self.viewport.set_display_mode(mode)
        self._render_current_frame()

    def _toggle_play(self) -> None:
        self._is_playing = not self._is_playing
        self.btn_play.setText("PAUSE" if self._is_playing else "PLAY")
        if self._is_playing:
            self._timer.start(40)  # ~25 fps
        else:
            self._timer.stop()

    def _on_play_step(self) -> None:
        curr = self.slider.value()
        next_f = curr + 1
        if next_f >= self._max_frames:
            next_f = 0
        self.slider.setValue(next_f)
        self._render_current_frame()

    def _step_frame(self, step: int) -> None:
        curr = self.slider.value()
        clamped = max(0, min(self._max_frames - 1, curr + step))
        self.slider.setValue(clamped)
        self._render_current_frame()

    def _on_slider_moved(self, val: int) -> None:
        self._render_current_frame()

    def _render_current_frame(self) -> None:
        idx = self.slider.value()
        self.lbl_frame_idx.setText(f"Frame {idx} / {self._max_frames}")

        offset = self.spin_offset.value()
        user_idx = max(0, idx + offset)
        pro_idx = idx

        user_frame = None
        pro_frame = None

        if self._user_cap and self._user_cap.isOpened():
            self._user_cap.set(cv2.CAP_PROP_POS_FRAMES, user_idx)
            s_u, f_u = self._user_cap.read()
            if s_u:
                user_frame = f_u

        if self._pro_cap and self._pro_cap.isOpened():
            self._pro_cap.set(cv2.CAP_PROP_POS_FRAMES, pro_idx)
            s_p, f_p = self._pro_cap.read()
            if s_p:
                pro_frame = f_p

        # Retrieve pre-computed skeletal geometry saved on video (no real-time model inference lag)
        user_lm = None
        user_angles = {}
        if self._user_geometry and "frames" in self._user_geometry:
            uf = self._user_geometry["frames"]
            if 0 <= user_idx < len(uf):
                user_lm = uf[user_idx].get("landmarks")
                user_angles = uf[user_idx].get("angles", {})
        elif user_frame is not None:
            user_lm = comparison_engine.extract_landmarks(user_frame)
            user_angles = comparison_engine.calculate_angles(user_lm) if user_lm else {}

        pro_lm = None
        pro_angles = {}
        if self._pro_geometry and "frames" in self._pro_geometry:
            pf = self._pro_geometry["frames"]
            if 0 <= pro_idx < len(pf):
                pro_lm = pf[pro_idx].get("landmarks")
                pro_angles = pf[pro_idx].get("angles", {})
        elif pro_frame is not None:
            pro_lm = comparison_engine.extract_landmarks(pro_frame)
            pro_angles = comparison_engine.calculate_angles(pro_lm) if pro_lm else {}

        # Compute Variances across Arms, Shoulders, Hips, Legs
        metrics = comparison_engine.compute_variances(user_angles, pro_angles)

        # Update HUD Metrics
        self.lbl_overall_score.setText(f"{metrics.overall_score:.0f}%")
        if metrics.overall_score >= 90:
            self.lbl_overall_score.setStyleSheet(f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 32px; font-weight: 800;")
        elif metrics.overall_score >= 75:
            self.lbl_overall_score.setStyleSheet(f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 32px; font-weight: 800;")
        else:
            self.lbl_overall_score.setStyleSheet(f"color: {THEME.COLOR_DANGER_BRIGHT}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 32px; font-weight: 800;")

        # Update 4 Segment Cards
        self.card_arms.update_metrics(
            metrics.arms.variance, metrics.arms.mean_delta_deg, metrics.arms.match_percentage,
            f"L Elbow: {metrics.arms.joint_details.get('left_elbow', {}).get('delta', 0)}° | R Elbow: {metrics.arms.joint_details.get('right_elbow', {}).get('delta', 0)}°"
        )
        self.card_shoulders.update_metrics(
            metrics.shoulders.variance, metrics.shoulders.mean_delta_deg, metrics.shoulders.match_percentage,
            f"Shoulder Tilt: {metrics.shoulders.joint_details.get('shoulder_tilt', {}).get('user', 0)}° vs {metrics.shoulders.joint_details.get('shoulder_tilt', {}).get('pro', 0)}°"
        )
        self.card_hips.update_metrics(
            metrics.hips.variance, metrics.hips.mean_delta_deg, metrics.hips.match_percentage,
            f"Hip Flexion Delta: {metrics.hips.joint_details.get('left_hip', {}).get('delta', 0)}° | Trunk: {metrics.hips.joint_details.get('trunk_lean', {}).get('user', 0)}°"
        )
        self.card_legs.update_metrics(
            metrics.legs.variance, metrics.legs.mean_delta_deg, metrics.legs.match_percentage,
            f"L Knee: {metrics.legs.joint_details.get('left_knee', {}).get('delta', 0)}° | R Knee: {metrics.legs.joint_details.get('right_knee', {}).get('delta', 0)}°"
        )

        self.lbl_coaching_cue.setText(metrics.primary_coaching_cue)

        # Render Viewport (Direct overlay anchored Right Shoulder to Right Shoulder)
        if self.radio_overlay.isChecked():
            base = pro_frame if pro_frame is not None else user_frame
            if base is not None:
                overlay_canvas = comparison_engine.render_direct_overlay(
                    base, pro_lm, user_lm, metrics,
                    pro_label="REFERENCE BENCHMARK",
                    user_label="YOUR ATHLETIC FORM"
                )
                self.viewport.set_overlay_frame(overlay_canvas)
        else:
            # Draw individual skeletons for split view
            u_disp = user_frame.copy() if user_frame is not None else None
            p_disp = pro_frame.copy() if pro_frame is not None else None
            if u_disp is not None and user_lm:
                pts_u = {}
                for idx, lm in enumerate(user_lm):
                    lx = lm["x"] if isinstance(lm, dict) else getattr(lm, "x", 0.0)
                    ly = lm["y"] if isinstance(lm, dict) else getattr(lm, "y", 0.0)
                    pts_u[idx] = (int(lx * u_disp.shape[1]), int(ly * u_disp.shape[0]))
                comparison_engine._draw_skeleton_lines(u_disp, pts_u, (94, 63, 244), 2)
            if p_disp is not None and pro_lm:
                pts_p = {}
                for idx, lm in enumerate(pro_lm):
                    lx = lm["x"] if isinstance(lm, dict) else getattr(lm, "x", 0.0)
                    ly = lm["y"] if isinstance(lm, dict) else getattr(lm, "y", 0.0)
                    pts_p[idx] = (int(lx * p_disp.shape[1]), int(ly * p_disp.shape[0]))
                comparison_engine._draw_skeleton_lines(p_disp, pts_p, (255, 240, 0), 2)
            self.viewport.set_split_frames(u_disp, p_disp)
