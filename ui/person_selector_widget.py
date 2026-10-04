"""Interactive Person Selector Widget for FormCheck.

Allows users to inspect video frames, detect multiple people in the scene, and
interactively click on a specific athlete to designate them as the target for
pose estimation and kinematic analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from person_selector import PersonSelector
from services.theme import THEME

logger = logging.getLogger(__name__)


class ClickablePersonCanvas(QWidget):
    """Interactive canvas rendering video frames with clickable athlete bounding boxes."""

    person_clicked = Signal(int, tuple)  # person_index, bbox (x, y, w, h)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(360, 240)

        self._frame_bgr: Optional[np.ndarray] = None
        self._qimage: Optional[QImage] = None
        self._detected_people: List[Tuple[Tuple[int, int, int, int], List[Any]]] = []
        self._selected_idx: int = 0
        self._hover_idx: Optional[int] = None

        # Scaling transforms
        self._render_rect = QRect()
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0

    def set_frame_and_detections(
        self,
        frame: Optional[np.ndarray],
        detections: List[Tuple[Tuple[int, int, int, int], List[Any]]],
        selected_idx: int = 0,
    ) -> None:
        """Updates the active video frame and detected athlete bounding boxes."""
        self._frame_bgr = frame
        self._detected_people = detections
        self._selected_idx = selected_idx
        self._hover_idx = None

        if frame is not None:
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            # Convert BGR to RGB for QImage
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        else:
            self._qimage = None

        self.update()

    def set_selected_index(self, idx: int) -> None:
        if 0 <= idx < len(self._detected_people):
            self._selected_idx = idx
            self.update()

    def get_selected_bbox(self) -> Optional[Tuple[int, int, int, int]]:
        if 0 <= self._selected_idx < len(self._detected_people):
            return self._detected_people[self._selected_idx][0]
        return None

    def _video_to_widget_rect(self, bbox: Tuple[int, int, int, int]) -> QRect:
        """Converts an (x, y, w, h) bbox from original video space to widget coordinates."""
        bx, by, bw, bh = bbox
        wx = int(self._render_rect.x() + bx * self._scale_x)
        wy = int(self._render_rect.y() + by * self._scale_y)
        ww = max(4, int(bw * self._scale_x))
        wh = max(4, int(bh * self._scale_y))
        return QRect(wx, wy, ww, wh)

    def _widget_to_video_coords(self, pt: QPoint) -> Optional[Tuple[int, int]]:
        """Converts a widget click point back to original video pixels."""
        if not self._render_rect.contains(pt) or self._scale_x <= 0 or self._scale_y <= 0:
            return None
        vx = int((pt.x() - self._render_rect.x()) / self._scale_x)
        vy = int((pt.y() - self._render_rect.y()) / self._scale_y)
        return vx, vy

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Background fill
        painter.fillRect(self.rect(), QColor(THEME.BG_INPUT))

        if self._qimage is None or self._frame_bgr is None:
            # Draw placeholder
            painter.setPen(QColor(THEME.TEXT_MUTED))
            painter.setFont(QFont(THEME.FONT_FAMILY_TECH, 10, QFont.Bold))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "NO VIDEO LOADED\nSelect a video clip to choose tracking target",
            )
            return

        # 2. Compute letterbox / aspect-fit rectangle
        widget_w = self.width()
        widget_h = self.height()
        img_w = self._qimage.width()
        img_h = self._qimage.height()

        ratio = min(widget_w / img_w, widget_h / img_h)
        scaled_w = int(img_w * ratio)
        scaled_h = int(img_h * ratio)
        offset_x = (widget_w - scaled_w) // 2
        offset_y = (widget_h - scaled_h) // 2

        self._render_rect = QRect(offset_x, offset_y, scaled_w, scaled_h)
        self._scale_x = scaled_w / img_w
        self._scale_y = scaled_h / img_h

        # Draw frame
        painter.drawImage(self._render_rect, self._qimage)

        # 3. Draw detected athletes
        primary_color = QColor(THEME.PRIMARY_COLOR)
        warning_color = QColor(THEME.COLOR_WARNING)
        slate_color = QColor("#64748b")
        card_bg = QColor("#09090b")

        for idx, (bbox, landmarks) in enumerate(self._detected_people):
            w_rect = self._video_to_widget_rect(bbox)
            is_selected = (idx == self._selected_idx)
            is_hover = (idx == self._hover_idx)

            if is_selected:
                # Active chosen athlete: glowing primary outline and tint
                box_color = primary_color
                fill_color = QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 40)
                pen_width = 3
            elif is_hover:
                box_color = warning_color
                fill_color = QColor(warning_color.red(), warning_color.green(), warning_color.blue(), 25)
                pen_width = 2
            else:
                box_color = slate_color
                fill_color = QColor(0, 0, 0, 0)
                pen_width = 1

            # Bounding box & tint
            if fill_color.alpha() > 0:
                painter.fillRect(w_rect, fill_color)

            painter.setPen(QPen(box_color, pen_width))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(w_rect)

            # Draw tactical corner accents on selected athlete
            if is_selected:
                corner_len = min(16, w_rect.width() // 4, w_rect.height() // 4)
                painter.setPen(QPen(primary_color, 4))
                # Top-left
                painter.drawLine(w_rect.left(), w_rect.top(), w_rect.left() + corner_len, w_rect.top())
                painter.drawLine(w_rect.left(), w_rect.top(), w_rect.left(), w_rect.top() + corner_len)
                # Top-right
                painter.drawLine(w_rect.right(), w_rect.top(), w_rect.right() - corner_len, w_rect.top())
                painter.drawLine(w_rect.right(), w_rect.top(), w_rect.right(), w_rect.top() + corner_len)
                # Bottom-left
                painter.drawLine(w_rect.left(), w_rect.bottom(), w_rect.left() + corner_len, w_rect.bottom())
                painter.drawLine(w_rect.left(), w_rect.bottom(), w_rect.left(), w_rect.bottom() - corner_len)
                # Bottom-right
                painter.drawLine(w_rect.right(), w_rect.bottom(), w_rect.right() - corner_len, w_rect.bottom())
                painter.drawLine(w_rect.right(), w_rect.bottom(), w_rect.right(), w_rect.bottom() - corner_len)

            # Draw tag badge above the head
            if is_selected:
                tag_text = f"[ TRACKING: ATHLETE #{idx + 1} ]"
                bg_tag = primary_color
                text_tag = card_bg
            elif is_hover:
                tag_text = f"[ ATHLETE #{idx + 1} - CLICK TO TRACK ]"
                bg_tag = warning_color
                text_tag = card_bg
            else:
                tag_text = f"[ ATHLETE #{idx + 1} ]"
                bg_tag = QColor("#1e293b")
                text_tag = QColor("#cbd5e1")

            font = QFont(THEME.FONT_FAMILY_TECH, 9, QFont.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(tag_text) + 12
            th = fm.height() + 4

            tag_x = max(w_rect.left(), self._render_rect.left())
            tag_y = max(w_rect.top() - th - 3, self._render_rect.top() + 4)
            tag_rect = QRect(tag_x, tag_y, tw, th)

            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_tag)
            painter.drawRoundedRect(tag_rect, 3, 3)

            painter.setPen(text_tag)
            painter.drawText(tag_rect, Qt.AlignCenter, tag_text)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        video_coords = self._widget_to_video_coords(event.pos())
        old_hover = self._hover_idx
        self._hover_idx = None

        if video_coords is not None and self._detected_people:
            vx, vy = video_coords
            for idx, (bbox, _) in enumerate(self._detected_people):
                bx, by, bw, bh = bbox
                if bx <= vx <= bx + bw and by <= vy <= by + bh:
                    self._hover_idx = idx
                    break

        if self._hover_idx is not None:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        if old_hover != self._hover_idx:
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return

        video_coords = self._widget_to_video_coords(event.pos())
        if video_coords is None or not self._detected_people:
            return

        vx, vy = video_coords
        clicked_idx = None

        # 1. Exact box check
        for idx, (bbox, _) in enumerate(self._detected_people):
            bx, by, bw, bh = bbox
            if bx <= vx <= bx + bw and by <= vy <= by + bh:
                clicked_idx = idx
                break

        # 2. Fallback: nearest person if clicked within proximity
        if clicked_idx is None:
            best_dist = float("inf")
            for idx, (bbox, _) in enumerate(self._detected_people):
                bx, by, bw, bh = bbox
                cx = bx + bw / 2.0
                cy = by + bh / 2.0
                dist = np.hypot(vx - cx, vy - cy)
                if dist < best_dist:
                    best_dist = dist
                    clicked_idx = idx

            # Allow selection if reasonably close
            max_dist = max(self._qimage.width(), self._qimage.height()) * 0.35
            if best_dist > max_dist:
                clicked_idx = None

        if clicked_idx is not None and 0 <= clicked_idx < len(self._detected_people):
            self._selected_idx = clicked_idx
            bbox = self._detected_people[clicked_idx][0]
            self.update()
            self.person_clicked.emit(clicked_idx, bbox)


class PersonSelectorWidget(QFrame):
    """Complete person selection module containing canvas, scrub slider, and athlete pills."""

    person_selected = Signal(int, tuple, int)  # person_idx, bbox (x, y, w, h), frame_idx

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("person_selector_widget")
        self.setStyleSheet(
            f"QFrame#person_selector_widget {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"}}"
        )

        self._video_path: Optional[str] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._total_frames: int = 0
        self._fps: float = 30.0
        self._current_frame_idx: int = 0
        self._selected_idx: int = 0
        self._selected_bbox: Optional[Tuple[int, int, int, int]] = None
        self._detection_cache: Dict[int, List[Tuple[Tuple[int, int, int, int], List[Any]]]] = {}

        self._selector = PersonSelector()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header info
        h_info = QHBoxLayout()
        lbl_head = QLabel("CHOOSE ATHLETE TO TRACK")
        lbl_head.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px;"
        )
        h_info.addWidget(lbl_head)
        h_info.addStretch()

        self.lbl_detected_count = QLabel("No video loaded")
        self.lbl_detected_count.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700;")
        h_info.addWidget(self.lbl_detected_count)
        layout.addLayout(h_info)

        # Interactive Canvas
        self.canvas = ClickablePersonCanvas(self)
        self.canvas.person_clicked.connect(self._on_canvas_person_clicked)
        layout.addWidget(self.canvas, stretch=1)

        # Athlete Quick Select Buttons in Horizontal Scroll Area
        self.athletes_scroll = QScrollArea()
        self.athletes_scroll.setWidgetResizable(True)
        self.athletes_scroll.setFixedHeight(44)
        self.athletes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.athletes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.athletes_scroll.setFrameShape(QFrame.NoFrame)
        self.athletes_scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }} "
            f"QScrollBar:horizontal {{ height: 4px; background: {THEME.BG_INPUT}; border-radius: 2px; }} "
            f"QScrollBar::handle:horizontal {{ background: {THEME.BORDER_LIGHT}; border-radius: 2px; }}"
        )
        self.athletes_container = QWidget()
        self.athletes_container.setStyleSheet("background: transparent;")
        self.h_athletes = QHBoxLayout(self.athletes_container)
        self.h_athletes.setContentsMargins(0, 4, 0, 4)
        self.h_athletes.setSpacing(6)
        self.athletes_scroll.setWidget(self.athletes_container)
        layout.addWidget(self.athletes_scroll)

        # Scrubber / Frame Navigation
        h_scrub = QHBoxLayout()
        h_scrub.setSpacing(8)

        self.btn_prev = QPushButton("PREV")
        self.btn_prev.setFixedSize(76, 28)
        self.btn_prev.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
            f"font-size: 11px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; border-color: {THEME.PRIMARY_COLOR}; }}"
        )
        self.btn_prev.clicked.connect(self._on_prev_frame)
        h_scrub.addWidget(self.btn_prev)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ height: 4px; background: {THEME.BG_INPUT}; border-radius: 2px; }} "
            f"QSlider::sub-page:horizontal {{ background: {THEME.PRIMARY_COLOR}; border-radius: 2px; }} "
            f"QSlider::handle:horizontal {{ background: #ffffff; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }}"
        )
        self.slider.valueChanged.connect(self._on_slider_changed)
        h_scrub.addWidget(self.slider, stretch=1)

        self.btn_next = QPushButton("NEXT")
        self.btn_next.setFixedSize(76, 28)
        self.btn_next.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
            f"font-size: 11px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; border-color: {THEME.PRIMARY_COLOR}; }}"
        )
        self.btn_next.clicked.connect(self._on_next_frame)
        h_scrub.addWidget(self.btn_next)

        self.lbl_frame_info = QLabel("Frame: 0 / 0 (0.0s)")
        self.lbl_frame_info.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 10px; min-width: 120px;"
        )
        self.lbl_frame_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h_scrub.addWidget(self.lbl_frame_info)
        layout.addLayout(h_scrub)

        # Status & Instructions
        self.lbl_status = QLabel("Click on the athlete you want to analyze in the video.")
        self.lbl_status.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 11px; padding: 4px 6px; background-color: {THEME.BG_INPUT}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; border: 1px solid {THEME.BORDER_COLOR};"
        )
        layout.addWidget(self.lbl_status)

    def load_video(self, video_path: str) -> bool:
        """Loads a video clip and detects athletes on the first populated frame."""
        if not video_path or not Path(video_path).exists():
            return False

        if self._cap:
            self._cap.release()

        self._video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            logger.error("Failed to open video in PersonSelectorWidget: %s", video_path)
            return False

        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 30.0)
        self.slider.setRange(0, max(0, self._total_frames - 1))

        # Clear cache for newly loaded video
        self._detection_cache.clear()

        # Scan candidate frames across the video to find the frame with the maximum visible athletes
        best_frame_idx = 0
        best_detections = []

        scan_indices = [0, 2, 4, 6, 8, 12, 16, 20]
        for f_idx in scan_indices:
            if f_idx >= self._total_frames:
                break
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = self._cap.read()
            if ret and frame is not None:
                det = self._selector.detect_people_in_frame(frame)
                self._detection_cache[f_idx] = det
                if len(det) > len(best_detections):
                    best_frame_idx = f_idx
                    best_detections = det

        self._current_frame_idx = best_frame_idx
        self.slider.blockSignals(True)
        self.slider.setValue(best_frame_idx)
        self.slider.blockSignals(False)

        self._render_frame(best_frame_idx, cached_detections=best_detections if best_detections else None)
        return True

    def _render_frame(self, frame_idx: int, cached_detections: Optional[List] = None) -> None:
        """Reads frame, runs detection if needed, and updates canvas and controls."""
        if not self._cap or not self._cap.isOpened():
            return

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return

        if cached_detections is not None:
            detections = cached_detections
            self._detection_cache[frame_idx] = detections
        elif frame_idx in self._detection_cache:
            detections = self._detection_cache[frame_idx]
        else:
            detections = self._selector.detect_people_in_frame(frame)
            self._detection_cache[frame_idx] = detections

        # Update frame info
        sec = frame_idx / self._fps if self._fps > 0 else 0.0
        self.lbl_frame_info.setText(f"Frame: {frame_idx + 1} / {self._total_frames} ({sec:.1f}s)")

        # Ensure selected index is valid
        if detections:
            if self._selected_idx >= len(detections):
                self._selected_idx = 0
            self._selected_bbox = detections[self._selected_idx][0]
        else:
            self._selected_bbox = None

        self.canvas.set_frame_and_detections(frame, detections, selected_idx=self._selected_idx)
        self._update_pills(detections)

        # Status text
        n = len(detections)
        if n == 0:
            self.lbl_detected_count.setText("0 ATHLETES DETECTED")
            self.lbl_detected_count.setStyleSheet(f"color: {THEME.COLOR_WARNING}; font-weight: 700; font-size: 10px;")
            self.lbl_status.setText("No athletes detected on this frame. Scrub to a frame where your athlete is visible.")
            self.lbl_status.setStyleSheet(
                f"color: {THEME.COLOR_WARNING}; font-size: 11px; padding: 4px 6px; background-color: {THEME.BG_INPUT}; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; border: 1px solid {THEME.COLOR_WARNING};"
            )
        elif n == 1:
            self.lbl_detected_count.setText("1 ATHLETE DETECTED")
            self.lbl_detected_count.setStyleSheet(f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-weight: 700; font-size: 10px;")
            self.lbl_status.setText("Athlete 1 selected. Ready to track and analyze.")
            self.lbl_status.setStyleSheet(
                f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-size: 11px; padding: 4px 6px; background-color: {THEME.BG_INPUT}; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; border: 1px solid {THEME.BORDER_COLOR};"
            )
        else:
            self.lbl_detected_count.setText(f"{n} ATHLETES DETECTED")
            self.lbl_detected_count.setStyleSheet(f"color: {THEME.PRIMARY_COLOR}; font-weight: 700; font-size: 10px;")
            self.lbl_status.setText(f"Tracking Athlete #{self._selected_idx + 1}. Click any person in the video to change target.")
            self.lbl_status.setStyleSheet(
                f"color: {THEME.PRIMARY_COLOR}; font-size: 11px; padding: 4px 6px; background-color: {THEME.BG_INPUT}; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; border: 1px solid {THEME.PRIMARY_COLOR};"
            )

        if self._selected_bbox is not None:
            self.person_selected.emit(self._selected_idx, self._selected_bbox, self._current_frame_idx)

    def _update_pills(self, detections: List) -> None:
        """Populates quick selection buttons underneath canvas."""
        # Clear existing buttons
        while self.h_athletes.count():
            item = self.h_athletes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not detections:
            return

        lbl_quick = QLabel("TARGET:")
        lbl_quick.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 800;")
        self.h_athletes.addWidget(lbl_quick)

        for idx in range(len(detections)):
            is_active = (idx == self._selected_idx)
            btn = QPushButton(f"[LOCKED] ATHLETE {idx + 1}" if is_active else f"ATHLETE {idx + 1}")
            btn.setFixedHeight(28)
            if is_active:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {THEME.PRIMARY_COLOR}; color: #09090b; "
                    f"font-size: 10px; font-weight: 800; border-radius: {THEME.BORDER_RADIUS_SM}; padding: 0 10px; border: none; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_SECONDARY}; "
                    f"font-size: 10px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
                    f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 0 10px; }} "
                    f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; color: {THEME.TEXT_PRIMARY}; }}"
                )
            btn.clicked.connect(lambda checked=False, target_idx=idx: self._select_person_by_idx(target_idx))
            self.h_athletes.addWidget(btn)

        self.h_athletes.addStretch()

    def _select_person_by_idx(self, idx: int) -> None:
        self._selected_idx = idx
        self.canvas.set_selected_index(idx)
        bbox = self.canvas.get_selected_bbox()
        if bbox is not None:
            self._selected_bbox = bbox
            self.person_selected.emit(self._selected_idx, bbox, self._current_frame_idx)
        # Refresh pills styling and status using cached detections
        cached = self._detection_cache.get(self._current_frame_idx)
        self._render_frame(self._current_frame_idx, cached_detections=cached)

    def _on_canvas_person_clicked(self, idx: int, bbox: tuple) -> None:
        self._selected_idx = idx
        self._selected_bbox = bbox
        self.person_selected.emit(idx, bbox, self._current_frame_idx)
        cached = self._detection_cache.get(self._current_frame_idx)
        self._render_frame(self._current_frame_idx, cached_detections=cached)

    def _on_slider_changed(self, val: int) -> None:
        self._current_frame_idx = val
        self._render_frame(val)

    def _on_prev_frame(self) -> None:
        if self._current_frame_idx > 0:
            self._current_frame_idx -= 1
            self.slider.setValue(self._current_frame_idx)

    def _on_next_frame(self) -> None:
        if self._current_frame_idx < self._total_frames - 1:
            self._current_frame_idx += 1
            self.slider.setValue(self._current_frame_idx)

    def get_selection(self) -> Tuple[Optional[Tuple[int, int, int, int]], int]:
        """Returns (selected_bbox, selected_frame_idx)."""
        return self._selected_bbox, self._current_frame_idx

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None
        super().close()


class PersonSelectionDialog(QDialog):
    """Standalone dialog to choose which person to track in a video clip."""

    def __init__(self, video_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Tracked Athlete - FormCheck")
        self.resize(800, 580)
        self.setStyleSheet(f"background-color: {THEME.BG_BASE}; color: {THEME.TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.selector_widget = PersonSelectorWidget(self)
        layout.addWidget(self.selector_widget, stretch=1)

        h_btns = QHBoxLayout()
        h_btns.addStretch()

        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; "
            f"font-size: 11px; font-weight: 700; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 8px 18px; }} "
            f"QPushButton:hover {{ background-color: {THEME.BORDER_LIGHT}; }}"
        )
        btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(btn_cancel)

        self.btn_confirm = QPushButton("CONFIRM TARGET ATHLETE")
        self.btn_confirm.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.PRIMARY_COLOR}; color: #09090b; "
            f"font-size: 11px; font-weight: 800; border-radius: {THEME.BORDER_RADIUS_SM}; padding: 8px 22px; }} "
            f"QPushButton:hover {{ background-color: #ffffff; }}"
        )
        self.btn_confirm.clicked.connect(self.accept)
        h_btns.addWidget(self.btn_confirm)
        layout.addLayout(h_btns)

        self.selector_widget.load_video(video_path)

    def get_selection(self) -> Tuple[Optional[Tuple[int, int, int, int]], int]:
        return self.selector_widget.get_selection()

    def closeEvent(self, event) -> None:
        self.selector_widget.close()
        super().closeEvent(event)

