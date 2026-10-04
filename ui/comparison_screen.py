"""Comparison screen providing dual video loading (local/vault), synchronized biomechanical
geometry visualization, direct skeleton overlay, and variance analysis across Arms, Shoulders, Hips, and Legs."""

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
    QCheckBox,
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
    """Viewport rendering side-by-side biomechanical geometries, direct ghost overlay, or split video feeds."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(600, 360)

        self._mode: str = "geom"  # "geom", "overlay", or "split"
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

        if self._mode in ("geom", "overlay"):
            if self._overlay_pixmap and not self._overlay_pixmap.isNull():
                scaled = self._overlay_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ox = (self.width() - scaled.width()) // 2
                oy = (self.height() - scaled.height()) // 2
                painter.drawPixmap(ox, oy, scaled)
            else:
                msg = "SELECT VIDEOS TO VIEW BIOMECHANICAL GEOMETRY" if self._mode == "geom" else "SELECT VIDEOS TO RUN SKELETAL OVERLAY"
                self._draw_placeholder(painter, msg)

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
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, text)


class SegmentVarianceCard(QFrame):
    """Displays calculated kinematic variance and angular error for a specific body segment."""

    def __init__(self, segment_title: str, accent_color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("seg_card")
        self.setMinimumHeight(76)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"QFrame#seg_card {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 6px 8px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(3)

        # Header
        h_head = QHBoxLayout()
        lbl_name = QLabel(segment_title.upper())
        lbl_name.setStyleSheet(
            f"color: {accent_color}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px;"
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

        self.lbl_delta = QLabel("Delta: 0.0 deg")
        self.lbl_delta.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        h_stats.addWidget(self.lbl_delta)
        layout.addLayout(h_stats)

        # Progress bar
        self.bar = QProgressBar()
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background-color: {THEME.BG_INPUT}; border-radius: 3px; border: none; }} "
            f"QProgressBar::chunk {{ background-color: {accent_color}; border-radius: 3px; }}"
        )
        layout.addWidget(self.bar)

        # Joint detail text
        self.lbl_detail = QLabel("Analyzing joint kinematics...")
        self.lbl_detail.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(self.lbl_detail)

    def update_metrics(self, var_val: float, delta_val: float, score: float, details_text: str) -> None:
        self.lbl_score.setText(f"{score:.0f}%")
        self.lbl_var.setText(f"Var: {var_val:.2f}")
        self.lbl_delta.setText(f"Delta: {delta_val:.1f} deg")
        self.bar.setValue(int(score))
        self.lbl_detail.setText(details_text)


class ComparisonScreen(QWidget):
    """Screen for loading User vs Reference videos, running clean side-by-side geometric comparison,
    ghost skeletal overlay, and analyzing variance across Arms, Shoulders, Hips, and Legs."""

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

        self._last_user_frame: Optional[np.ndarray] = None
        self._last_pro_frame: Optional[np.ndarray] = None

        self._display_mode: str = "geom"  # "geom" (default), "overlay", or "split"
        self._is_playing: bool = False
        self._mirror_user: bool = False
        self._mirror_pro: bool = False

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
        self._last_user_frame = None

        # Retrieve or pre-compute saved geometry for video
        self._user_geometry = geometry_cache.get_or_compute_geometry(file_path)
        if self._user_geometry and self._user_geometry.get("total_frames"):
            self._user_total_frames = max(self._user_total_frames, self._user_geometry["total_frames"])

        self.lbl_user_loaded.setText(f"Ready: {Path(file_path).name} ({self._user_total_frames} frames)")
        self.lbl_user_loaded.setStyleSheet(f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-size: 11px; font-weight: 600;")

        # Sync combo if present
        for i in range(self.combo_user_vault.count()):
            if self.combo_user_vault.itemData(i) == file_path:
                self.combo_user_vault.blockSignals(True)
                self.combo_user_vault.setCurrentIndex(i)
                self.combo_user_vault.blockSignals(False)
                break

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
        self._last_pro_frame = None

        # Retrieve or pre-compute saved geometry for reference video
        self._pro_geometry = geometry_cache.get_or_compute_geometry(file_path)
        if self._pro_geometry and self._pro_geometry.get("total_frames"):
            self._pro_total_frames = max(self._pro_total_frames, self._pro_geometry["total_frames"])

        self.lbl_pro_loaded.setText(f"Ready: {Path(file_path).name} ({self._pro_total_frames} frames)")
        self.lbl_pro_loaded.setStyleSheet(f"color: {THEME.PRIMARY_COLOR}; font-size: 11px; font-weight: 600;")

        # Sync combo if present
        for i in range(self.combo_pro_vault.count()):
            if self.combo_pro_vault.itemData(i) == file_path:
                self.combo_pro_vault.blockSignals(True)
                self.combo_pro_vault.setCurrentIndex(i)
                self.combo_pro_vault.blockSignals(False)
                break

        self._render_current_frame()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 10, 18, 14)
        main_layout.setSpacing(12)

        # 1. Sleek 2-Card Video Selection Deck (User Form on Left | AI Match Center | Pro Reference on Right)
        selection_deck = QFrame()
        selection_deck.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 8px 12px;"
        )
        deck_layout = QHBoxLayout(selection_deck)
        deck_layout.setSpacing(12)
        deck_layout.setContentsMargins(8, 6, 8, 6)

        # Slot 1: User Form Card
        v_user = QVBoxLayout()
        v_user.setSpacing(4)
        h_u_hdr = QHBoxLayout()
        lbl_u_title = QLabel("1. YOUR ATHLETIC FORM")
        lbl_u_title.setStyleSheet(
            f"color: {THEME.COLOR_DANGER_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.6px;"
        )
        h_u_hdr.addWidget(lbl_u_title)
        h_u_hdr.addStretch()

        btn_u_local = QPushButton("+ BROWSE LOCAL")
        btn_u_local.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
            f"font-size: 10px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 3px 8px; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; border-color: {THEME.COLOR_DANGER_BRIGHT}; }}"
        )
        btn_u_local.clicked.connect(self._on_browse_user_local)
        h_u_hdr.addWidget(btn_u_local)

        btn_u_target = QPushButton("CHOOSE ATHLETE")
        btn_u_target.setToolTip("Click on which person to track in this video")
        btn_u_target.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.PRIMARY_COLOR}; "
            f"font-size: 10px; font-weight: 700; border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 3px 8px; }} "
            f"QPushButton:hover {{ background-color: {THEME.PRIMARY_COLOR}; color: #09090b; }}"
        )
        btn_u_target.clicked.connect(self._on_choose_user_athlete)
        h_u_hdr.addWidget(btn_u_target)

        self.btn_u_mirror = QPushButton("MIRROR")
        self.btn_u_mirror.setCheckable(True)
        self.btn_u_mirror.setToolTip("Mirror user video horizontally to match pro facing direction")
        self.btn_u_mirror.clicked.connect(self._on_toggle_user_mirror)
        self._update_mirror_btn_style(self.btn_u_mirror, False, THEME.COLOR_DANGER_BRIGHT)
        h_u_hdr.addWidget(self.btn_u_mirror)

        v_user.addLayout(h_u_hdr)

        self.combo_user_vault = QComboBox()
        self.combo_user_vault.setMinimumHeight(30)
        self.combo_user_vault.addItem("-- Select Your Video --", "")
        self.combo_user_vault.currentIndexChanged.connect(self._on_user_vault_selected)
        v_user.addWidget(self.combo_user_vault)

        self.lbl_user_loaded = QLabel("No video selected")
        self.lbl_user_loaded.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px;")
        v_user.addWidget(self.lbl_user_loaded)
        deck_layout.addLayout(v_user, stretch=5)

        # Center: AI Matchmaker Button
        v_div1 = QFrame()
        v_div1.setFrameShape(QFrame.VLine)
        v_div1.setStyleSheet(f"color: {THEME.BORDER_COLOR};")
        deck_layout.addWidget(v_div1)

        v_ai_match = QVBoxLayout()
        v_ai_match.setAlignment(Qt.AlignCenter)
        v_ai_match.setSpacing(3)

        self.btn_find_pro = QPushButton("AI PRO MATCH")
        self.btn_find_pro.setToolTip("Compare your appendage angular variances against professional athlete database to find your closest match.")
        self.btn_find_pro.setMinimumHeight(34)
        self.btn_find_pro.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.COLOR_WARNING}; color: #09090b; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 6px 14px; border: none; }} "
            f"QPushButton:hover {{ background-color: {THEME.COLOR_SUCCESS_BRIGHT}; }}"
        )
        self.btn_find_pro.clicked.connect(self._on_find_closest_pro)
        v_ai_match.addWidget(self.btn_find_pro)

        lbl_ai_sub = QLabel("Auto-Detect Closest Pro Form")
        lbl_ai_sub.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 9px;")
        lbl_ai_sub.setAlignment(Qt.AlignCenter)
        v_ai_match.addWidget(lbl_ai_sub)
        deck_layout.addLayout(v_ai_match, stretch=0)

        v_div2 = QFrame()
        v_div2.setFrameShape(QFrame.VLine)
        v_div2.setStyleSheet(f"color: {THEME.BORDER_COLOR};")
        deck_layout.addWidget(v_div2)

        # Slot 2: Reference Benchmark Card
        v_pro = QVBoxLayout()
        v_pro.setSpacing(4)
        h_p_hdr = QHBoxLayout()
        lbl_p_title = QLabel("2. REFERENCE BENCHMARK")
        lbl_p_title.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.6px;"
        )
        h_p_hdr.addWidget(lbl_p_title)
        h_p_hdr.addStretch()

        btn_p_local = QPushButton("+ BROWSE LOCAL")
        btn_p_local.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
            f"font-size: 10px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 3px 8px; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; border-color: {THEME.PRIMARY_COLOR}; }}"
        )
        btn_p_local.clicked.connect(self._on_browse_pro_local)
        h_p_hdr.addWidget(btn_p_local)

        self.btn_p_mirror = QPushButton("MIRROR")
        self.btn_p_mirror.setCheckable(True)
        self.btn_p_mirror.setToolTip("Mirror reference video horizontally to match your facing direction")
        self.btn_p_mirror.clicked.connect(self._on_toggle_pro_mirror)
        self._update_mirror_btn_style(self.btn_p_mirror, False, THEME.PRIMARY_COLOR)
        h_p_hdr.addWidget(self.btn_p_mirror)

        v_pro.addLayout(h_p_hdr)

        self.combo_pro_vault = QComboBox()
        self.combo_pro_vault.setMinimumHeight(30)
        self.combo_pro_vault.addItem("-- Select Reference Benchmark --", "")
        self.combo_pro_vault.currentIndexChanged.connect(self._on_pro_vault_selected)
        v_pro.addWidget(self.combo_pro_vault)

        self.lbl_pro_loaded = QLabel("No reference selected")
        self.lbl_pro_loaded.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px;")
        v_pro.addWidget(self.lbl_pro_loaded)
        deck_layout.addLayout(v_pro, stretch=5)

        main_layout.addWidget(selection_deck)

        # 3. Main Horizontal Center Area (Left Viewport & Controls | Right Telemetry)
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(14)

        # Left Column: Mode Segmented Switcher + Viewport + Scrubber
        v_vp = QVBoxLayout()
        v_vp.setContentsMargins(0, 0, 0, 0)
        v_vp.setSpacing(8)

        # 3A. Viewport Mode Switcher (Clean Segmented Buttons)
        h_modes = QHBoxLayout()
        h_modes.setSpacing(8)
        lbl_vmode = QLabel("VIEW:")
        lbl_vmode.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        h_modes.addWidget(lbl_vmode)

        self.btn_mode_geom = QPushButton("SIDE-BY-SIDE GEOMETRIES (CLEAN)")
        self.btn_mode_overlay = QPushButton("GHOST OVERLAY (SHOULDER ANCHORED)")
        self.btn_mode_split = QPushButton("SPLIT VIDEO FEEDS")

        for b in [self.btn_mode_geom, self.btn_mode_overlay, self.btn_mode_split]:
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setFixedHeight(30)

        self.btn_mode_geom.setChecked(True)
        self.btn_mode_geom.clicked.connect(lambda: self._set_display_mode("geom"))
        self.btn_mode_overlay.clicked.connect(lambda: self._set_display_mode("overlay"))
        self.btn_mode_split.clicked.connect(lambda: self._set_display_mode("split"))

        self._update_mode_button_styles()

        h_modes.addWidget(self.btn_mode_geom)
        h_modes.addWidget(self.btn_mode_overlay)
        h_modes.addWidget(self.btn_mode_split)
        h_modes.addStretch()
        v_vp.addLayout(h_modes)

        # 3B. Viewport
        self.viewport = ComparisonViewport(self)
        v_vp.addWidget(self.viewport, stretch=1)

        # 3C. Scrubber & Transport Box (Phase-Normalized Timing Fix)
        trans_frame = QFrame()
        trans_frame.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 8px 12px;"
        )
        tf_layout = QVBoxLayout(trans_frame)
        tf_layout.setSpacing(6)

        # Top row: Transport buttons + Sync mode + Offset
        h_trans_top = QHBoxLayout()
        h_trans_top.setSpacing(8)

        self.btn_play = QPushButton("PLAY")
        self.btn_play.setFixedWidth(68)
        self.btn_play.clicked.connect(self._toggle_play)
        h_trans_top.addWidget(self.btn_play)

        btn_step_b = QPushButton("<<")
        btn_step_b.setFixedWidth(34)
        btn_step_b.setToolTip("Step backward")
        btn_step_b.clicked.connect(lambda: self._step_frame(-1))
        h_trans_top.addWidget(btn_step_b)

        btn_step_f = QPushButton(">>")
        btn_step_f.setFixedWidth(34)
        btn_step_f.setToolTip("Step forward")
        btn_step_f.clicked.connect(lambda: self._step_frame(1))
        h_trans_top.addWidget(btn_step_f)

        self.chk_loop = QCheckBox("Loop Motion")
        self.chk_loop.setChecked(True)
        self.chk_loop.setStyleSheet(f"color: {THEME.TEXT_SECONDARY}; font-size: 11px;")
        h_trans_top.addWidget(self.chk_loop)

        self.chk_phase_sync = QCheckBox("Phase Sync (Proportional)")
        self.chk_phase_sync.setChecked(True)
        self.chk_phase_sync.setToolTip("When enabled, scales both motions from 0% to 100% so peak impact/apex matches perfectly regardless of clip length.")
        self.chk_phase_sync.setStyleSheet(f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-size: 11px; font-weight: 600;")
        self.chk_phase_sync.toggled.connect(self._render_current_frame)
        h_trans_top.addWidget(self.chk_phase_sync)

        self.chk_mirror_user = QCheckBox("Mirror User")
        self.chk_mirror_user.setToolTip("Mirror user video horizontally")
        self.chk_mirror_user.setStyleSheet(f"color: {THEME.COLOR_DANGER_BRIGHT}; font-size: 11px; font-weight: 600;")
        self.chk_mirror_user.toggled.connect(self._on_chk_user_mirror_toggled)
        h_trans_top.addWidget(self.chk_mirror_user)

        self.chk_mirror_pro = QCheckBox("Mirror Pro")
        self.chk_mirror_pro.setToolTip("Mirror reference pro video horizontally")
        self.chk_mirror_pro.setStyleSheet(f"color: {THEME.PRIMARY_COLOR}; font-size: 11px; font-weight: 600;")
        self.chk_mirror_pro.toggled.connect(self._on_chk_pro_mirror_toggled)
        h_trans_top.addWidget(self.chk_mirror_pro)

        h_trans_top.addStretch()

        lbl_offset = QLabel("Sync Offset:")
        lbl_offset.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        h_trans_top.addWidget(lbl_offset)

        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(-30, 30)
        self.spin_offset.setValue(0)
        self.spin_offset.setSuffix("%")
        self.spin_offset.setToolTip("Adjust phase offset if user movement starts earlier or later")
        self.spin_offset.valueChanged.connect(self._render_current_frame)
        h_trans_top.addWidget(self.spin_offset)

        btn_reset_sync = QPushButton("RESET")
        btn_reset_sync.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_SECONDARY}; "
            f"font-size: 10px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 3px 8px; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; color: {THEME.TEXT_PRIMARY}; }}"
        )
        btn_reset_sync.clicked.connect(lambda: self.spin_offset.setValue(0))
        h_trans_top.addWidget(btn_reset_sync)

        tf_layout.addLayout(h_trans_top)

        # Bottom row: Phase Slider & Progress Readout
        h_slider = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        h_slider.addWidget(self.slider, stretch=1)

        self.lbl_frame_idx = QLabel("PHASE: 0%  |  User: --  |  Ref: --")
        self.lbl_frame_idx.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 700;"
        )
        h_slider.addWidget(self.lbl_frame_idx)
        tf_layout.addLayout(h_slider)

        v_vp.addWidget(trans_frame)
        center_layout.addLayout(v_vp, stretch=1)

        # Right Column: Telemetry & Variance Dashboard
        telemetry_widget = QWidget()
        telem_layout = QVBoxLayout(telemetry_widget)
        telem_layout.setContentsMargins(2, 0, 2, 0)
        telem_layout.setSpacing(8)

        # Overall Form Match Score Box
        score_box = QFrame()
        score_box.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 10px;"
        )
        sb_layout = QVBoxLayout(score_box)
        sb_layout.setSpacing(2)
        sb_layout.setAlignment(Qt.AlignCenter)

        lbl_match_title = QLabel("OVERALL FORM MATCH")
        lbl_match_title.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        sb_layout.addWidget(lbl_match_title)

        self.lbl_overall_score = QLabel("100%")
        self.lbl_overall_score.setStyleSheet(
            f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 32px; font-weight: 800;"
        )
        sb_layout.addWidget(self.lbl_overall_score)
        telem_layout.addWidget(score_box)

        # Coaching Cue Box (Placed immediately below Overall Form Match)
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

        self.lbl_coaching_cue = QLabel("Select user and reference videos to inspect kinematic alignment.")
        self.lbl_coaching_cue.setWordWrap(True)
        self.lbl_coaching_cue.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-size: 11px; font-weight: 600; line-height: 1.3;"
        )
        cb_layout.addWidget(self.lbl_coaching_cue)
        telem_layout.addWidget(cue_box)

        # Collapsible Dropdown Section for Detailed Segment Kinematics (Closed by default!)
        self.dropdown_frame = QFrame()
        self.dropdown_frame.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 6px;"
        )
        df_layout = QVBoxLayout(self.dropdown_frame)
        df_layout.setContentsMargins(6, 6, 6, 6)
        df_layout.setSpacing(6)

        # Dropdown Header Button
        self.btn_toggle_details = QPushButton("> DETAILED KINEMATICS [EXPAND]")
        self.btn_toggle_details.setToolTip("Click to expand/collapse variance and joint angles for Arms, Shoulders, Hips, and Legs")
        self.btn_toggle_details.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_details.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; "
            f"border: 1px solid {THEME.BORDER_COLOR}; border-radius: {THEME.BORDER_RADIUS_SM}; padding: 8px 12px; text-align: left; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; border-color: {THEME.PRIMARY_COLOR}; }}"
        )
        self.btn_toggle_details.clicked.connect(self._toggle_details_dropdown)
        df_layout.addWidget(self.btn_toggle_details)

        # Collapsible container - CLOSED BY DEFAULT
        self.details_container = QWidget()
        dc_layout = QVBoxLayout(self.details_container)
        dc_layout.setContentsMargins(0, 4, 0, 0)
        dc_layout.setSpacing(6)

        # Filter row inside dropdown
        h_filter = QHBoxLayout()
        lbl_filt = QLabel("SEGMENT FILTER:")
        lbl_filt.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700;")
        h_filter.addWidget(lbl_filt)

        self.combo_segment_filter = QComboBox()
        self.combo_segment_filter.addItem("All Segments (4 Regions)", "all")
        self.combo_segment_filter.addItem("Arms & Elbows", "arms")
        self.combo_segment_filter.addItem("Shoulder Tilt & Arm Axis", "shoulders")
        self.combo_segment_filter.addItem("Hip Flexion & Core Hinge", "hips")
        self.combo_segment_filter.addItem("Knee Flexion & Stance", "legs")
        self.combo_segment_filter.currentIndexChanged.connect(self._on_segment_filter_changed)
        h_filter.addWidget(self.combo_segment_filter, stretch=1)
        dc_layout.addLayout(h_filter)

        # Segment 1: Arms Variance
        self.card_arms = SegmentVarianceCard("Arms & Elbow Angles", THEME.COLOR_SUCCESS_BRIGHT)
        dc_layout.addWidget(self.card_arms)

        # Segment 2: Shoulders Variance
        self.card_shoulders = SegmentVarianceCard("Shoulder Tilt & Arm Axis", THEME.PRIMARY_COLOR)
        dc_layout.addWidget(self.card_shoulders)

        # Segment 3: Hips Variance
        self.card_hips = SegmentVarianceCard("Hip Flexion & Core Hinge", THEME.COLOR_WARNING)
        dc_layout.addWidget(self.card_hips)

        # Segment 4: Legs Variance
        self.card_legs = SegmentVarianceCard("Knee Flexion & Stance Width", THEME.COLOR_DANGER_BRIGHT)
        dc_layout.addWidget(self.card_legs)

        # Explicitly set CLOSED by default
        self.details_container.setVisible(False)
        df_layout.addWidget(self.details_container)

        telem_layout.addWidget(self.dropdown_frame)
        telem_layout.addStretch()

        telem_scroll = QScrollArea()
        telem_scroll.setWidgetResizable(True)
        telem_scroll.setFixedWidth(385)
        telem_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        telem_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        telem_scroll.setWidget(telemetry_widget)
        center_layout.addWidget(telem_scroll)
        main_layout.addWidget(center_widget, stretch=1)

        self._populate_vault_dropdowns()

    def _toggle_details_dropdown(self) -> None:
        """Toggles visibility of the detailed segment kinematics dropdown container."""
        is_open = not self.details_container.isVisible()
        self.details_container.setVisible(is_open)
        if is_open:
            self.btn_toggle_details.setText("v DETAILED KINEMATICS [COLLAPSE]")
            self.btn_toggle_details.setStyleSheet(
                f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.PRIMARY_COLOR}; "
                f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; "
                f"border: 1px solid {THEME.PRIMARY_COLOR}; border-radius: {THEME.BORDER_RADIUS_SM}; padding: 8px 12px; text-align: left; }} "
                f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; }}"
            )
        else:
            self.btn_toggle_details.setText("> DETAILED KINEMATICS [EXPAND]")
            self.btn_toggle_details.setStyleSheet(
                f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
                f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; "
                f"border: 1px solid {THEME.BORDER_COLOR}; border-radius: {THEME.BORDER_RADIUS_SM}; padding: 8px 12px; text-align: left; }} "
                f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; border-color: {THEME.PRIMARY_COLOR}; }}"
            )

    def _on_segment_filter_changed(self, idx: int) -> None:
        """Filters which segment cards are shown inside the expanded dropdown."""
        val = self.combo_segment_filter.currentData()
        if val == "all":
            self.card_arms.setVisible(True)
            self.card_shoulders.setVisible(True)
            self.card_hips.setVisible(True)
            self.card_legs.setVisible(True)
        else:
            self.card_arms.setVisible(val == "arms")
            self.card_shoulders.setVisible(val == "shoulders")
            self.card_hips.setVisible(val == "hips")
            self.card_legs.setVisible(val == "legs")

    def _set_display_mode(self, mode: str) -> None:
        self._display_mode = mode
        self.viewport.set_display_mode(mode)
        self._update_mode_button_styles()
        self._render_current_frame()

    def _update_mode_button_styles(self) -> None:
        active_style = (
            f"QPushButton {{ background-color: {THEME.PRIMARY_COLOR}; color: #09090b; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 5px 12px; border: none; }}"
        )
        inactive_style = (
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_SECONDARY}; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 700; "
            f"border: 1px solid {THEME.BORDER_COLOR}; border-radius: {THEME.BORDER_RADIUS_SM}; padding: 5px 12px; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; color: {THEME.TEXT_PRIMARY}; }}"
        )
        self.btn_mode_geom.setStyleSheet(active_style if self._display_mode == "geom" else inactive_style)
        self.btn_mode_overlay.setStyleSheet(active_style if self._display_mode == "overlay" else inactive_style)
        self.btn_mode_split.setStyleSheet(active_style if self._display_mode == "split" else inactive_style)

    def _update_mirror_btn_style(self, btn: QPushButton, is_mirrored: bool, active_color: str) -> None:
        """Updates styling and label for mirror toggle buttons."""
        if is_mirrored:
            btn.setText("MIRRORED")
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {active_color}; color: #09090b; "
                f"font-size: 10px; font-weight: 800; letter-spacing: 0.6px; border: 1px solid {active_color}; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 3px 8px; }} "
                f"QPushButton:hover {{ opacity: 0.9; }}"
            )
        else:
            btn.setText("MIRROR")
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_SECONDARY}; "
                f"font-size: 10px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 3px 8px; }} "
                f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; color: {THEME.TEXT_PRIMARY}; border-color: {active_color}; }}"
            )

    def _on_toggle_user_mirror(self) -> None:
        self._mirror_user = self.btn_u_mirror.isChecked()
        self.chk_mirror_user.blockSignals(True)
        self.chk_mirror_user.setChecked(self._mirror_user)
        self.chk_mirror_user.blockSignals(False)
        self._update_mirror_btn_style(self.btn_u_mirror, self._mirror_user, THEME.COLOR_DANGER_BRIGHT)
        self._render_current_frame()

    def _on_toggle_pro_mirror(self) -> None:
        self._mirror_pro = self.btn_p_mirror.isChecked()
        self.chk_mirror_pro.blockSignals(True)
        self.chk_mirror_pro.setChecked(self._mirror_pro)
        self.chk_mirror_pro.blockSignals(False)
        self._update_mirror_btn_style(self.btn_p_mirror, self._mirror_pro, THEME.PRIMARY_COLOR)
        self._render_current_frame()

    def _on_chk_user_mirror_toggled(self, checked: bool) -> None:
        self._mirror_user = checked
        self.btn_u_mirror.blockSignals(True)
        self.btn_u_mirror.setChecked(checked)
        self.btn_u_mirror.blockSignals(False)
        self._update_mirror_btn_style(self.btn_u_mirror, self._mirror_user, THEME.COLOR_DANGER_BRIGHT)
        self._render_current_frame()

    def _on_chk_pro_mirror_toggled(self, checked: bool) -> None:
        self._mirror_pro = checked
        self.btn_p_mirror.blockSignals(True)
        self.btn_p_mirror.setChecked(checked)
        self.btn_p_mirror.blockSignals(False)
        self._update_mirror_btn_style(self.btn_p_mirror, self._mirror_pro, THEME.PRIMARY_COLOR)
        self._render_current_frame()

    def _populate_vault_dropdowns(self) -> None:
        """Populates vault dropdowns for User and Pro selections separately."""
        # 1. User dropdown: personal user uploads followed by uploaded vault references
        self.combo_user_vault.blockSignals(True)
        self.combo_user_vault.clear()
        self.combo_user_vault.addItem("-- Select Your Video --", "")

        user_id = self._user.get("id")
        if user_id:
            user_personal = video_service.get_library(category="personal", user_id=user_id)
            for v in user_personal:
                self.combo_user_vault.addItem(f"[MY DRILL] {v.get('title')} ({v.get('sport')})", v.get("file_path"))

        vault_vids = video_service.get_library(category="pro")
        for v in vault_vids:
            self.combo_user_vault.addItem(f"[VAULT] {v.get('title')} ({v.get('sport')})", v.get("file_path"))
        self.combo_user_vault.blockSignals(False)

        # 2. Reference pro dropdown: only genuine uploaded athlete reference benchmarks
        self.combo_pro_vault.blockSignals(True)
        self.combo_pro_vault.clear()
        self.combo_pro_vault.addItem("-- Select Reference Benchmark --", "")
        for v in vault_vids:
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

    def _on_choose_user_athlete(self) -> None:
        if not self._user_path or not Path(self._user_path).exists():
            QMessageBox.warning(self, "No Video Loaded", "Please select or browse a user video first.")
            return
        from ui.person_selector_widget import PersonSelectionDialog
        dlg = PersonSelectionDialog(self._user_path, parent=self)
        if dlg.exec() == QDialog.Accepted:
            bbox, start_frame = dlg.get_selection()
            if bbox:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    self._user_geometry = geometry_cache.get_or_compute_geometry(
                        self._user_path,
                        initial_bbox=bbox,
                        start_frame=start_frame,
                        force_recompute=True,
                    )
                    self.lbl_user_loaded.setText(f"Tracked: Athlete (F{start_frame+1}) - {Path(self._user_path).name}")
                    self._render_current_frame()
                finally:
                    QApplication.restoreOverrideCursor()

    def _on_browse_pro_local(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select Pro Athlete Reference", "", "Video Files (*.mp4 *.mov *.avi *.mkv)")
        if p:
            self.load_pro_video(p)

    def _on_pro_vault_selected(self, idx: int) -> None:
        p = self.combo_pro_vault.currentData()
        if p:
            self.load_pro_video(p)

    def _on_find_closest_pro(self) -> None:
        """Runs appendage angle variance vector cosine similarity & waveform alignment to find closest pro athlete."""
        if not self._user_path or not Path(self._user_path).exists():
            reply = QMessageBox.question(
                self,
                "Select User Video",
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

    def _toggle_play(self) -> None:
        self._is_playing = not self._is_playing
        self.btn_play.setText("PAUSE" if self._is_playing else "PLAY")
        if self._is_playing:
            self._timer.start(40)  # ~25 fps
        else:
            self._timer.stop()

    def _on_play_step(self) -> None:
        curr = self.slider.value()
        eff_f = max(self._user_total_frames, self._pro_total_frames, 40)
        step = max(3, int(1000 / eff_f))
        next_val = curr + step
        if next_val >= 1000:
            if self.chk_loop.isChecked():
                next_val = 0
            else:
                next_val = 1000
                self._toggle_play()
                return
        self.slider.setValue(next_val)
        self._render_current_frame()

    def _step_frame(self, step_dir: int) -> None:
        eff_f = max(self._user_total_frames, self._pro_total_frames, 40)
        step = max(3, int(1000 / eff_f)) * step_dir
        curr = self.slider.value()
        clamped = max(0, min(1000, curr + step))
        self.slider.setValue(clamped)
        self._render_current_frame()

    def _on_slider_moved(self, val: int) -> None:
        self._render_current_frame()

    def _render_current_frame(self) -> None:
        val = self.slider.value()
        phase_pct = val / 1000.0  # Normalized progress 0.0 to 1.0

        is_phase_sync = self.chk_phase_sync.isChecked()
        offset_val = self.spin_offset.value()

        if is_phase_sync:
            # Phase-normalized calculation: both videos reach 50% apex together
            p_offset = offset_val / 100.0
            u_phase = max(0.0, min(1.0, phase_pct + p_offset))
            p_phase = phase_pct

            user_idx = int(round(u_phase * (self._user_total_frames - 1))) if self._user_total_frames > 0 else 0
            pro_idx = int(round(p_phase * (self._pro_total_frames - 1))) if self._pro_total_frames > 0 else 0
        else:
            # Raw frame calculation
            max_f = max(1, max(self._user_total_frames, self._pro_total_frames))
            base_f = int(round(phase_pct * (max_f - 1)))
            user_idx = max(0, min(self._user_total_frames - 1, base_f + offset_val)) if self._user_total_frames > 0 else 0
            pro_idx = max(0, min(self._pro_total_frames - 1, base_f)) if self._pro_total_frames > 0 else 0

        # Clamp indices so neither video ever ends early or goes out of bounds
        if self._user_total_frames > 0:
            user_idx = max(0, min(self._user_total_frames - 1, user_idx))
        if self._pro_total_frames > 0:
            pro_idx = max(0, min(self._pro_total_frames - 1, pro_idx))

        # Update telemetry readout
        u_str = f"F{user_idx+1}/{self._user_total_frames}" if self._user_total_frames > 0 else "--"
        p_str = f"F{pro_idx+1}/{self._pro_total_frames}" if self._pro_total_frames > 0 else "--"
        self.lbl_frame_idx.setText(f"PHASE: {int(phase_pct * 100)}%  |  User: {u_str}  |  Ref: {p_str}")

        # Fetch frames safely with hold buffering to avoid black screens
        user_frame = None
        pro_frame = None

        if self._user_cap and self._user_cap.isOpened():
            self._user_cap.set(cv2.CAP_PROP_POS_FRAMES, user_idx)
            s_u, f_u = self._user_cap.read()
            if s_u and f_u is not None:
                self._last_user_frame = f_u
                user_frame = f_u.copy()
            elif self._last_user_frame is not None:
                user_frame = self._last_user_frame.copy()

        if self._pro_cap and self._pro_cap.isOpened():
            self._pro_cap.set(cv2.CAP_PROP_POS_FRAMES, pro_idx)
            s_p, f_p = self._pro_cap.read()
            if s_p and f_p is not None:
                self._last_pro_frame = f_p
                pro_frame = f_p.copy()
            elif self._last_pro_frame is not None:
                pro_frame = self._last_pro_frame.copy()

        # Retrieve pre-computed skeletal geometry saved on video (no real-time model inference lag)
        user_lm = None
        user_angles = {}
        if self._user_geometry and "frames" in self._user_geometry:
            uf = self._user_geometry["frames"]
            if uf:
                clamped_u = max(0, min(len(uf) - 1, user_idx))
                user_lm = uf[clamped_u].get("landmarks")
                user_angles = uf[clamped_u].get("angles", {})
        elif user_frame is not None:
            user_lm = comparison_engine.extract_landmarks(user_frame)
            user_angles = comparison_engine.calculate_angles(user_lm) if user_lm else {}

        pro_lm = None
        pro_angles = {}
        if self._pro_geometry and "frames" in self._pro_geometry:
            pf = self._pro_geometry["frames"]
            if pf:
                clamped_p = max(0, min(len(pf) - 1, pro_idx))
                pro_lm = pf[clamped_p].get("landmarks")
                pro_angles = pf[clamped_p].get("angles", {})
        elif pro_frame is not None:
            pro_lm = comparison_engine.extract_landmarks(pro_frame)
            pro_angles = comparison_engine.calculate_angles(pro_lm) if pro_lm else {}

        # Apply horizontal mirroring if enabled
        if self._mirror_user:
            if user_frame is not None:
                user_frame = cv2.flip(user_frame, 1)
            if user_lm is not None:
                user_lm = comparison_engine.mirror_landmarks(user_lm)

        if self._mirror_pro:
            if pro_frame is not None:
                pro_frame = cv2.flip(pro_frame, 1)
            if pro_lm is not None:
                pro_lm = comparison_engine.mirror_landmarks(pro_lm)

        if user_lm and not user_angles:
            user_angles = comparison_engine.calculate_angles(user_lm)
        if pro_lm and not pro_angles:
            pro_angles = comparison_engine.calculate_angles(pro_lm)

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
            f"L Elbow: {metrics.arms.joint_details.get('left_elbow', {}).get('delta', 0)} deg | R Elbow: {metrics.arms.joint_details.get('right_elbow', {}).get('delta', 0)} deg"
        )
        self.card_shoulders.update_metrics(
            metrics.shoulders.variance, metrics.shoulders.mean_delta_deg, metrics.shoulders.match_percentage,
            f"Shoulder Tilt: {metrics.shoulders.joint_details.get('shoulder_tilt', {}).get('user', 0)} deg vs {metrics.shoulders.joint_details.get('shoulder_tilt', {}).get('pro', 0)} deg"
        )
        self.card_hips.update_metrics(
            metrics.hips.variance, metrics.hips.mean_delta_deg, metrics.hips.match_percentage,
            f"Hip Flexion Delta: {metrics.hips.joint_details.get('left_hip', {}).get('delta', 0)} deg | Trunk: {metrics.hips.joint_details.get('trunk_lean', {}).get('user', 0)} deg"
        )
        self.card_legs.update_metrics(
            metrics.legs.variance, metrics.legs.mean_delta_deg, metrics.legs.match_percentage,
            f"L Knee: {metrics.legs.joint_details.get('left_knee', {}).get('delta', 0)} deg | R Knee: {metrics.legs.joint_details.get('right_knee', {}).get('delta', 0)} deg"
        )

        self.lbl_coaching_cue.setText(metrics.primary_coaching_cue)

        # Dynamic badges indicating mirrored status
        u_label_text = "YOUR ATHLETIC FORM [MIRRORED]" if self._mirror_user else "YOUR ATHLETIC FORM"
        p_label_text = "REFERENCE BENCHMARK [MIRRORED]" if self._mirror_pro else "REFERENCE BENCHMARK"

        # Render Viewport based on chosen Mode
        if self._display_mode == "geom":
            # 1. Clean Side-by-Side Geometries (Default: dedicated dual stage, zero video collision)
            geom_canvas = comparison_engine.render_geometric_side_by_side(
                user_landmarks=user_lm,
                pro_landmarks=pro_lm,
                user_angles=user_angles,
                pro_angles=pro_angles,
                metrics=metrics,
                width=1280,
                height=720,
                user_label="YOUR ATHLETIC GEOMETRY [MIRRORED]" if self._mirror_user else "YOUR ATHLETIC GEOMETRY",
                pro_label="REFERENCE BENCHMARK [MIRRORED]" if self._mirror_pro else "REFERENCE BENCHMARK",
                phase_pct=phase_pct,
            )
            self.viewport.set_overlay_frame(geom_canvas)

        elif self._display_mode == "overlay":
            # 2. Direct Camera Overlay anchored Right Shoulder to Right Shoulder
            base = pro_frame if pro_frame is not None else user_frame
            if base is not None:
                overlay_canvas = comparison_engine.render_direct_overlay(
                    base, pro_lm, user_lm, metrics,
                    pro_label=p_label_text,
                    user_label=u_label_text
                )
                self.viewport.set_overlay_frame(overlay_canvas)
            else:
                placeholder = np.full((720, 1280, 3), (18, 14, 13), dtype=np.uint8)
                self.viewport.set_overlay_frame(placeholder)

        elif self._display_mode == "split":
            # 3. Side-by-Side Synchronized Video Feeds
            u_disp = user_frame.copy() if user_frame is not None else None
            p_disp = pro_frame.copy() if pro_frame is not None else None

            if u_disp is not None:
                if user_lm:
                    pts_u = {}
                    for idx, lm in enumerate(user_lm):
                        lx = lm["x"] if isinstance(lm, dict) else getattr(lm, "x", 0.0)
                        ly = lm["y"] if isinstance(lm, dict) else getattr(lm, "y", 0.0)
                        pts_u[idx] = (int(lx * u_disp.shape[1]), int(ly * u_disp.shape[0]))
                    comparison_engine._draw_skeleton_lines(u_disp, pts_u, (94, 63, 244), 3)
                    for pt in pts_u.values():
                        cv2.circle(u_disp, pt, 4, (94, 63, 244), -1, cv2.LINE_AA)

                # Top-left badge on user video
                badge_w = 260 if "MIRRORED" not in u_label_text else 330
                cv2.rectangle(u_disp, (16, 16), (16 + badge_w, 48), (9, 9, 11), -1)
                cv2.rectangle(u_disp, (16, 16), (16 + badge_w, 48), (50, 50, 56), 1)
                cv2.putText(u_disp, u_label_text, (26, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (94, 63, 244), 1, cv2.LINE_AA)

            if p_disp is not None:
                if pro_lm:
                    pts_p = {}
                    for idx, lm in enumerate(pro_lm):
                        lx = lm["x"] if isinstance(lm, dict) else getattr(lm, "x", 0.0)
                        ly = lm["y"] if isinstance(lm, dict) else getattr(lm, "y", 0.0)
                        pts_p[idx] = (int(lx * p_disp.shape[1]), int(ly * p_disp.shape[0]))
                    comparison_engine._draw_skeleton_lines(p_disp, pts_p, (255, 240, 0), 3)
                    for pt in pts_p.values():
                        cv2.circle(p_disp, pt, 4, (255, 240, 0), -1, cv2.LINE_AA)

                # Top-left badge on pro video
                badge_w = 260 if "MIRRORED" not in p_label_text else 340
                cv2.rectangle(p_disp, (16, 16), (16 + badge_w, 48), (9, 9, 11), -1)
                cv2.rectangle(p_disp, (16, 16), (16 + badge_w, 48), (50, 50, 56), 1)
                cv2.putText(p_disp, p_label_text, (26, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 240, 0), 1, cv2.LINE_AA)

            self.viewport.set_split_frames(u_disp, p_disp)
