"""Home dashboard screen with primary athletic workflow navigation cards."""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.theme import THEME


class NavCard(QFrame):
    """Interactive navigation card for launching athletic workflows."""

    clicked = Signal()

    def __init__(
        self,
        badge_text: str,
        title: str,
        subtitle: str,
        action_label: str,
        accent_color: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("nav_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(140)

        self.setStyleSheet(
            f"QFrame#nav_card {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 12px; "
            f"}} "
            f"QFrame#nav_card:hover {{ "
            f"  border: 1.5px solid {accent_color}; "
            f"  background-color: {THEME.BG_INPUT}; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Top Badge
        lbl_badge = QLabel(badge_text.upper())
        lbl_badge.setStyleSheet(
            f"color: {accent_color}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        layout.addWidget(lbl_badge)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 15px; font-weight: 800; letter-spacing: 0.8px;"
        )
        layout.addWidget(lbl_title)

        # Subtitle
        lbl_desc = QLabel(subtitle)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_BODY}; "
            f"font-size: 12px; font-weight: 500; line-height: 1.3;"
        )
        layout.addWidget(lbl_desc)

        layout.addStretch()

        # Action Button
        btn = QPushButton(action_label)
        btn.setStyleSheet(
            f"QPushButton {{ "
            f"  background-color: {THEME.BG_INPUT}; "
            f"  border: 1px solid {accent_color}; "
            f"  border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"  color: {THEME.TEXT_PRIMARY}; "
            f"  font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"  font-size: 11px; font-weight: 700; letter-spacing: 0.8px; "
            f"  min-height: 34px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"  background-color: {accent_color}; "
            f"  color: #09090b; "
            f"}}"
        )
        btn.clicked.connect(self.clicked.emit)
        layout.addWidget(btn)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HomeScreen(QWidget):
    """Home dashboard presenting top-level athletic modules."""

    navigate_to = Signal(str)  # 'drill', 'upload', 'editor', 'compare'
    switch_user_requested = Signal()

    def __init__(self, user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user or {"id": None, "username": "Guest", "full_name": "Guest Athlete"}
        self._init_ui()

    def set_user(self, user: Dict[str, Any]) -> None:
        self._user = user
        self._update_header_user()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(10)

        # 1. Top Header Banner
        header = QFrame()
        header.setStyleSheet(
            f"QFrame {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 10px 16px; "
            f"}}"
        )
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 6, 8, 6)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        lbl_app = QLabel("FORMCHECK AI  //  ATHLETIC BIOMECHANICS & KINEMATICS")
        lbl_app.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 800; letter-spacing: 1.2px;"
        )
        v_head.addWidget(lbl_app)

        lbl_slogan = QLabel("PRO ATHLETE BENCHMARKING & FORM IMPROVEMENT SUITE")
        lbl_slogan.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 16px; font-weight: 800; letter-spacing: 1px;"
        )
        v_head.addWidget(lbl_slogan)
        h_layout.addLayout(v_head, stretch=1)

        # User Status & Switch button
        v_user = QVBoxLayout()
        v_user.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        v_user.setSpacing(6)

        self.lbl_user_status = QLabel()
        self._update_header_user()
        v_user.addWidget(self.lbl_user_status)

        btn_account = QPushButton("ACCOUNT / SIGN IN")
        btn_account.setStyleSheet(
            f"QPushButton {{ "
            f"  background-color: {THEME.BG_INPUT}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"  color: {THEME.TEXT_MUTED}; "
            f"  font-family: {THEME.FONT_FAMILY_TECH}; "
            f"  font-size: 11px; font-weight: 700; letter-spacing: 1px; "
            f"  padding: 6px 14px; min-height: 32px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"  border: 1px solid {THEME.PRIMARY_COLOR}; "
            f"  color: {THEME.TEXT_PRIMARY}; "
            f"}}"
        )
        btn_account.clicked.connect(self.switch_user_requested.emit)
        v_user.addWidget(btn_account)
        h_layout.addLayout(v_user)

        main_layout.addWidget(header)

        # 2. Main Workflow Grid (4 Big Action Cards)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 8, 0, 8)
        grid.setSpacing(18)

        # Card 1: Live Sensor / Camera Tracking
        card_drill = NavCard(
            badge_text="Module 01 // Real-Time",
            title="LIVE RECORDER",
            subtitle="Calibrate your webcam or optical sensor for real-time recording.",
            action_label="LAUNCH RECORDING SESSION",
            accent_color=THEME.COLOR_SUCCESS_BRIGHT,
        )
        card_drill.clicked.connect(lambda: self.navigate_to.emit("drill"))
        grid.addWidget(card_drill, 0, 0)

        # Card 2: Upload Screen / Server Vault
        card_upload = NavCard(
            badge_text="Module 02 // Cloud Archive",
            title="ATHLETE VAULT & VIDEO UPLOAD",
            subtitle="Explore professional athlete libraries or securely upload your personal training clips to the server for cloud analysis.",
            action_label="OPEN VIDEO VAULT",
            accent_color=THEME.PRIMARY_COLOR,
        )
        card_upload.clicked.connect(lambda: self.navigate_to.emit("upload"))
        grid.addWidget(card_upload, 0, 1)

        # Card 3: Biomechanical Video Editor
        card_editor = NavCard(
            badge_text="Module 03 // Precision Studio",
            title="VIDEO TRIM & CROP STUDIO",
            subtitle="Isolate key athletic movement windows with frame-accurate trimming and crop camera angles for focused joint trajectory tracking.",
            action_label="OPEN VIDEO EDITOR",
            accent_color=THEME.COLOR_WARNING,
        )
        card_editor.clicked.connect(lambda: self.navigate_to.emit("editor"))
        grid.addWidget(card_editor, 1, 0)

        # Card 4: Pro Athlete Comparison & Overlay
        card_compare = NavCard(
            badge_text="Module 04 // Kinetic Overlay",
            title="PRO ATHLETE FORM COMPARISON",
            subtitle="Directly overlay your skeletal movement onto pro athletes. Compute precise kinematic variance across arms, shoulders, hips, and legs.",
            action_label="LAUNCH COMPARISON",
            accent_color=THEME.COLOR_DANGER_BRIGHT,
        )
        card_compare.clicked.connect(lambda: self.navigate_to.emit("compare"))
        grid.addWidget(card_compare, 1, 1)

        main_layout.addWidget(grid_widget, stretch=1)

        # 3. Bottom Quick Telemetry Bar
        footer = QFrame()
        footer.setStyleSheet(
            f"QFrame {{ "
            f"  background-color: {THEME.BG_SURFACE}; "
            f"  border: 1px solid {THEME.BORDER_COLOR}; "
            f"  border-radius: {THEME.BORDER_RADIUS}; "
            f"  padding: 10px 16px; "
            f"}}"
        )
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(6, 4, 6, 4)

        lbl_foot_left = QLabel("SYSTEM STATUS: ONLINE // POSE KINEMATICS ENGINE READY // SQLITE VAULT ACTIVE")
        lbl_foot_left.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 700; letter-spacing: 0.8px;"
        )
        f_layout.addWidget(lbl_foot_left)
        f_layout.addStretch()

        lbl_foot_right = QLabel("VERSION 2.4 PRO ATHLETE BUILD")
        lbl_foot_right.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 700; letter-spacing: 0.8px;"
        )
        f_layout.addWidget(lbl_foot_right)
        main_layout.addWidget(footer)

    def _update_header_user(self) -> None:
        user_id = self._user.get("id")
        username = self._user.get("username", "Guest")
        if user_id:
            txt = f"ATHLETE PROFILE: {username.upper()} [ACTIVE]"
            color = THEME.COLOR_SUCCESS_BRIGHT
        else:
            txt = "ACCOUNT: GUEST [LIMITED ACCESS]"
            color = THEME.COLOR_WARNING

        self.lbl_user_status.setText(txt)
        self.lbl_user_status.setStyleSheet(
            f"color: {color}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 12px; font-weight: 800; letter-spacing: 1px;"
        )
