"""Upload and server storage screen for professional athlete archives and personal videos."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.camera import CameraService
from services.geometry_cache import geometry_cache
from services.pro_similarity_service import pro_similarity_service
from services.theme import THEME
from services.video_service import video_service
from ui.pro_recommendation_dialog import ProRecommendationDialog

logger = logging.getLogger(__name__)


class VideoCard(QFrame):
    """Card representing an uploaded video in the library."""

    edit_requested = Signal(str)
    compare_requested = Signal(str, str)
    delete_requested = Signal(int)

    def __init__(self, video_data: Dict[str, Any], current_user_id: Optional[int] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.video_data = video_data
        self.setObjectName("video_card")
        self.setStyleSheet(
            f"QFrame#video_card {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 10px; "
            f"}} "
            f"QFrame#video_card:hover {{ "
            f"  border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Thumbnail
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedHeight(140)
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setStyleSheet(
            f"background-color: {THEME.BG_INPUT}; border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"border: 1px solid {THEME.BORDER_DARK};"
        )

        thumb_path = video_data.get("thumbnail_path")
        if thumb_path and Path(thumb_path).exists():
            pix = QPixmap(thumb_path).scaled(240, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_thumb.setPixmap(pix)
        else:
            self.lbl_thumb.setText("ATHLETIC VIDEO CLIP")
            self.lbl_thumb.setStyleSheet(
                f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px;"
            )
        layout.addWidget(self.lbl_thumb)

        # 2. Header: Category badge & Sport
        h_badge = QHBoxLayout()
        is_pro = video_data.get("category") == "pro"
        badge_text = "PRO ATHLETE" if is_pro else "PERSONAL"
        badge_color = THEME.PRIMARY_COLOR if is_pro else THEME.COLOR_DANGER_BRIGHT

        lbl_cat = QLabel(badge_text)
        lbl_cat.setStyleSheet(
            f"color: {badge_color}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 10px; "
            f"font-weight: 800; letter-spacing: 1px; padding: 2px 6px; "
            f"background-color: {THEME.BG_INPUT}; border-radius: 3px;"
        )
        h_badge.addWidget(lbl_cat)

        lbl_sport = QLabel(video_data.get("sport", "General"))
        lbl_sport.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        h_badge.addWidget(lbl_sport)
        h_badge.addStretch()
        layout.addLayout(h_badge)

        # 3. Title
        lbl_title = QLabel(video_data.get("title", "Untitled Clip"))
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 14px; font-weight: 700;"
        )
        layout.addWidget(lbl_title)

        # 4. Telemetry info
        dur = video_data.get("duration_seconds", 0.0)
        fps = video_data.get("fps", 30.0)
        res = video_data.get("resolution", "1080p")
        lbl_info = QLabel(f"{res} @ {fps:.0f}fps  |  {dur:.1f}s")
        lbl_info.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px;"
        )
        layout.addWidget(lbl_info)

        # 5. Action Buttons
        h_btns = QHBoxLayout()
        h_btns.setSpacing(6)

        btn_edit = QPushButton("EDIT")
        btn_edit.setFixedHeight(32)
        btn_edit.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"color: {THEME.TEXT_PRIMARY}; font-size: 11px; font-weight: 700; border-radius: {THEME.BORDER_RADIUS_SM}; }}"
            f"QPushButton:hover {{ border-color: {THEME.COLOR_WARNING}; color: {THEME.COLOR_WARNING}; }}"
        )
        btn_edit.clicked.connect(lambda: self.edit_requested.emit(video_data.get("file_path", "")))
        h_btns.addWidget(btn_edit)

        btn_compare = QPushButton("COMPARE")
        btn_compare.setFixedHeight(32)
        btn_compare.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"color: {THEME.PRIMARY_COLOR}; font-size: 11px; font-weight: 700; border-radius: {THEME.BORDER_RADIUS_SM}; }}"
            f"QPushButton:hover {{ background-color: {THEME.PRIMARY_COLOR}; color: #09090b; }}"
        )
        btn_compare.clicked.connect(
            lambda: self.compare_requested.emit(video_data.get("file_path", ""), video_data.get("category", "pro"))
        )
        h_btns.addWidget(btn_compare)

        # Delete button if owned by user
        if current_user_id and video_data.get("user_id") == current_user_id:
            btn_del = QPushButton("X")
            btn_del.setFixedSize(32, 32)
            btn_del.setStyleSheet(
                f"QPushButton {{ background-color: {THEME.BG_INPUT}; border: 1px solid {THEME.BORDER_COLOR}; "
                f"color: {THEME.COLOR_DANGER_BRIGHT}; font-weight: 800; border-radius: {THEME.BORDER_RADIUS_SM}; }}"
                f"QPushButton:hover {{ background-color: {THEME.COLOR_DANGER}; color: #ffffff; }}"
            )
            btn_del.clicked.connect(lambda: self.delete_requested.emit(video_data.get("id")))
            h_btns.addWidget(btn_del)

        layout.addLayout(h_btns)


class UploadVideoModal(QDialog):
    """Modal dialog allowing authenticated users to upload videos to the server."""

    def __init__(self, user_id: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Upload Athletic Video to Server")
        self.resize(500, 480)
        self._selected_path: Optional[str] = None
        self.uploaded_record: Optional[Dict[str, Any]] = None
        self.pro_report: Optional[Any] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        lbl_head = QLabel("UPLOAD TO ATHLETIC SERVER VAULT")
        lbl_head.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 16px; font-weight: 800;"
        )
        layout.addWidget(lbl_head)

        # 1. File Selector
        lbl_f = QLabel("Video File (.mp4, .mov, .avi, .mkv):")
        lbl_f.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_f)

        h_file = QHBoxLayout()
        self.txt_path = QLineEdit()
        self.txt_path.setReadOnly(True)
        self.txt_path.setPlaceholderText("No video file selected...")
        h_file.addWidget(self.txt_path)

        btn_browse = QPushButton("BROWSE...")
        btn_browse.clicked.connect(self._on_browse)
        h_file.addWidget(btn_browse)
        layout.addLayout(h_file)

        # 2. Title Input
        lbl_t = QLabel("Video Title:")
        lbl_t.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_t)
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("e.g. Volleyball Jump Spike - Lateral Angle")
        layout.addWidget(self.txt_title)

        # 3. Sport Selector
        lbl_s = QLabel("Sport / Drill Discipline:")
        lbl_s.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_s)
        self.combo_sport = QComboBox()
        self.combo_sport.addItems(["Volleyball", "Baseball", "Squat / Strength", "Track & Field", "General Athletics"])
        layout.addWidget(self.combo_sport)

        # 4. Category (Personal by default)
        lbl_c = QLabel("Archive Category:")
        lbl_c.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_c)
        self.combo_cat = QComboBox()
        self.combo_cat.addItem("Personal Recording (Default)", "personal")
        self.combo_cat.addItem("Professional Reference (Pro Athlete)", "pro")
        self.combo_cat.addItem("Shared / Both", "both")
        layout.addWidget(self.combo_cat)

        # 5. Description
        lbl_d = QLabel("Technique Notes (Optional):")
        lbl_d.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_d)
        self.txt_desc = QTextEdit()
        self.txt_desc.setMaximumHeight(70)
        self.txt_desc.setPlaceholderText("Focus on elbow height, arm swing velocity, hip torque...")
        layout.addWidget(self.txt_desc)

        # 6. Action buttons
        h_actions = QHBoxLayout()
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.clicked.connect(self.reject)
        h_actions.addWidget(btn_cancel)

        self.btn_upload = QPushButton("UPLOAD TO SERVER")
        self.btn_upload.setObjectName("btn_start")
        self.btn_upload.clicked.connect(self._on_upload)
        h_actions.addWidget(self.btn_upload)
        layout.addLayout(h_actions)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Training Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)",
        )
        if path:
            self._selected_path = path
            self.txt_path.setText(path)
            if not self.txt_title.text():
                self.txt_title.setText(Path(path).stem.replace("_", " ").title())

    def _on_upload(self) -> None:
        if not self._selected_path:
            QMessageBox.warning(self, "Missing File", "Please choose a video file to upload.")
            return

        title = self.txt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please enter a title for the video.")
            return

        cat = self.combo_cat.currentData()
        sport = self.combo_sport.currentText()
        desc = self.txt_desc.toPlainText().strip()

        ok, msg, record = video_service.upload_video(
            source_file_path=self._selected_path,
            title=title,
            category=cat,
            sport=sport,
            user_id=self.user_id,
            description=desc,
        )

        if ok:
            dest_file = record.get("file_path") if record else self._selected_path
            self.uploaded_record = record

            # 1. Pre-compute and save geometry to server storage (instant O(1) overlay without real-time model lag)
            self.btn_upload.setEnabled(False)
            self.btn_upload.setText("PRE-COMPUTING SKELETAL GEOMETRY...")
            QApplication.processEvents()
            try:
                geometry_cache.get_or_compute_geometry(dest_file)
            except Exception as e:
                logger.error(f"Error caching geometry: {e}")

            # 2. Run AI pro athlete matchmaker to find closest pro form match
            self.btn_upload.setText("AI PRO MATCHMAKING...")
            QApplication.processEvents()
            try:
                self.pro_report = pro_similarity_service.recommend_pro_athlete(dest_file, sport=sport)
            except Exception as e:
                logger.error(f"Error calculating pro recommendation: {e}")

            best_name = self.pro_report.best_match.pro_name if (self.pro_report and self.pro_report.best_match) else None
            if best_name:
                QMessageBox.information(
                    self,
                    "Upload & Biomechanical Analysis Complete",
                    f"{msg}\n\nAI Matchmaker Result:\nOkay, you look like {best_name}!"
                )
            else:
                QMessageBox.information(self, "Upload Success", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Upload Failed", msg)


class UploadScreen(QWidget):
    """Full screen for video uploads, server storage archive, and pro/personal browsing."""

    navigate_to = Signal(str)  # 'home', 'editor', 'compare', 'drill'
    open_editor_requested = Signal(str)
    open_comparison_requested = Signal(str, str)
    switch_user_requested = Signal()

    def __init__(self, user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user or {"id": None, "username": "Guest"}
        self._init_ui()
        self.refresh_library()

    def set_user(self, user: Dict[str, Any]) -> None:
        self._user = user
        self._update_auth_ui()
        self.refresh_library()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

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

        lbl_title = QLabel("ATHLETE VIDEO ARCHIVE & SERVER VAULT")
        lbl_title.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 16px; font-weight: 800; letter-spacing: 1.2px; margin-left: 10px;"
        )
        tb_layout.addWidget(lbl_title)
        tb_layout.addStretch()

        btn_drill = QPushButton("LIVE DRILL")
        btn_drill.clicked.connect(lambda: self.navigate_to.emit("drill"))
        tb_layout.addWidget(btn_drill)

        btn_editor = QPushButton("VIDEO EDITOR")
        btn_editor.clicked.connect(lambda: self.navigate_to.emit("editor"))
        tb_layout.addWidget(btn_editor)

        btn_compare = QPushButton("PRO COMPARISON")
        btn_compare.clicked.connect(lambda: self.navigate_to.emit("compare"))
        tb_layout.addWidget(btn_compare)

        main_layout.addWidget(top_bar)

        # 2. Permission Banner & Upload Action Bar
        self.banner_frame = QFrame()
        self.banner_layout = QHBoxLayout(self.banner_frame)
        self.banner_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.addWidget(self.banner_frame)

        # 3. Categorized Library Tabs
        self.tabs = QTabWidget()
        self.tab_pro = QWidget()
        self.tab_personal = QWidget()
        self.tab_all = QWidget()

        self.tabs.addTab(self.tab_pro, "PROFESSIONAL ATHLETE ARCHIVE")
        self.tabs.addTab(self.tab_personal, "MY PERSONAL VAULT")
        self.tabs.addTab(self.tab_all, "ALL VIDEOS")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Grid containers
        self.grid_pro = self._create_scroll_grid(self.tab_pro)
        self.grid_personal = self._create_scroll_grid(self.tab_personal)
        self.grid_all = self._create_scroll_grid(self.tab_all)

        main_layout.addWidget(self.tabs, stretch=1)

        self._update_auth_ui()

    def _create_scroll_grid(self, parent_tab: QWidget) -> QGridLayout:
        tab_layout = QVBoxLayout(parent_tab)
        tab_layout.setContentsMargins(4, 8, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(14)
        grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        return grid

    def _update_auth_ui(self) -> None:
        """Configures upload action bar based on authentication status."""
        # Clear banner layout
        while self.banner_layout.count():
            item = self.banner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        is_auth = bool(self._user.get("id"))
        if is_auth:
            self.banner_frame.setStyleSheet(
                f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
                f"border-radius: {THEME.BORDER_RADIUS};"
            )
            lbl_stat = QLabel(f"AUTHENTICATED ATHLETE: {self._user.get('username', '').upper()}")
            lbl_stat.setStyleSheet(
                f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 12px; font-weight: 800;"
            )
            self.banner_layout.addWidget(lbl_stat)
            self.banner_layout.addStretch()

            btn_upload = QPushButton("+ UPLOAD ATHLETIC VIDEO TO SERVER")
            btn_upload.setStyleSheet(
                f"QPushButton {{ background-color: {THEME.PRIMARY_COLOR}; color: #09090b; "
                f"font-family: {THEME.FONT_FAMILY_DISPLAY}; font-weight: 800; font-size: 12px; "
                f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 8px 18px; min-height: 38px; }} "
                f"QPushButton:hover {{ background-color: #ffffff; }}"
            )
            btn_upload.clicked.connect(self._on_open_upload_modal)
            self.banner_layout.addWidget(btn_upload)
        else:
            self.banner_frame.setStyleSheet(
                f"background-color: rgba(253, 224, 71, 0.1); border: 1px solid {THEME.COLOR_WARNING}; "
                f"border-radius: {THEME.BORDER_RADIUS};"
            )
            lbl_warn = QLabel(
                "GUEST ACCESS: Professional athlete videos are unlocked below. Sign in to upload your personal clips to the server."
            )
            lbl_warn.setStyleSheet(f"color: {THEME.COLOR_WARNING}; font-size: 12px; font-weight: 700;")
            self.banner_layout.addWidget(lbl_warn)
            self.banner_layout.addStretch()

            btn_login = QPushButton("SIGN IN TO UPLOAD")
            btn_login.setStyleSheet(
                f"QPushButton {{ background-color: {THEME.COLOR_WARNING}; color: #09090b; "
                f"font-weight: 800; font-size: 11px; border-radius: {THEME.BORDER_RADIUS_SM}; "
                f"padding: 6px 14px; min-height: 34px; }}"
            )
            btn_login.clicked.connect(self.switch_user_requested.emit)
            self.banner_layout.addWidget(btn_login)

    def _on_open_upload_modal(self) -> None:
        user_id = self._user.get("id")
        if not user_id:
            QMessageBox.warning(self, "Access Required", "Please sign in to upload videos.")
            self.switch_user_requested.emit()
            return

        modal = UploadVideoModal(user_id=user_id, parent=self)
        if modal.exec() == QDialog.Accepted:
            self.refresh_library()
            if modal.pro_report and modal.pro_report.best_match:
                rec_dialog = ProRecommendationDialog(modal.pro_report, parent=self)
                rec_dialog.compare_requested.connect(
                    lambda u_path, p_path: self.open_comparison_requested.emit(u_path, p_path)
                )
                rec_dialog.load_pro_requested.connect(
                    lambda p_path: self.open_comparison_requested.emit(
                        modal.uploaded_record.get("file_path", "") if modal.uploaded_record else "",
                        p_path,
                    )
                )
                rec_dialog.exec()

    def _on_tab_changed(self, idx: int) -> None:
        self.refresh_library()

    def refresh_library(self) -> None:
        """Fetches videos from server storage and populates active tab grid."""
        user_id = self._user.get("id")

        # 1. Pro Videos
        pro_vids = video_service.get_library(category="pro")
        self._populate_grid(self.grid_pro, pro_vids, user_id)

        # 2. Personal Videos
        personal_vids = video_service.get_library(category="personal", user_id=user_id) if user_id else []
        self._populate_grid(self.grid_personal, personal_vids, user_id, empty_msg="No personal videos uploaded yet. Click '+ UPLOAD ATHLETIC VIDEO' above.")

        # 3. All Videos
        all_vids = video_service.get_library(category=None, user_id=user_id)
        self._populate_grid(self.grid_all, all_vids, user_id)

    def _populate_grid(self, grid: QGridLayout, videos: List[Dict[str, Any]], current_user_id: Optional[int], empty_msg: str = "No videos found.") -> None:
        # Clear existing items
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not videos:
            lbl_empty = QLabel(empty_msg)
            lbl_empty.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 13px; font-weight: 600; padding: 24px;")
            grid.addWidget(lbl_empty, 0, 0)
            return

        columns = 3
        for idx, v in enumerate(videos):
            card = VideoCard(v, current_user_id=current_user_id)
            card.edit_requested.connect(self.open_editor_requested.emit)
            card.compare_requested.connect(self.open_comparison_requested.emit)
            card.delete_requested.connect(self._on_delete_video)
            r = idx // columns
            c = idx % columns
            grid.addWidget(card, r, c)

    def _on_delete_video(self, video_id: int) -> None:
        user_id = self._user.get("id")
        reply = QMessageBox.question(
            self,
            "Delete Video",
            "Are you sure you want to delete this video clip from your vault?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from services.db import db
            db.delete_uploaded_video(video_id, user_id=user_id)
            self.refresh_library()
