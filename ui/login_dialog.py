"""Modern Login and Registration Dialog for FormCheck Desktop."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.db import db
from services.settings import APP_NAME, APP_TITLE
from services.theme import THEME

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """Sleek authentication modal supporting login, account creation, and guest mode."""

    login_successful = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} Pro - Athlete Sign In")
        self.resize(560, 740)
        self.setMinimumSize(520, 700)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.authenticated_user: Optional[Dict[str, Any]] = None
        self.is_guest: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 30, 36, 30)
        root_layout.setSpacing(18)

        # 1. Branding Header
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(8)

        title_label = QLabel("FORMCHECK PRO")
        title_label.setStyleSheet(
            f"color: {THEME.TEXT_PRIMARY}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 28px; font-weight: 800; letter-spacing: 3px;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("PRO ATHLETE BIOMECHANICS & KINEMATICS SYSTEM")
        subtitle_label.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 700; letter-spacing: 2px;"
        )
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)

        root_layout.addLayout(header_layout)

        # 2. Tab Widget for Login / Register
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_login_tab(), "ATHLETE SIGN IN")
        self.tabs.addTab(self._build_register_tab(), "REGISTER ATHLETE")
        root_layout.addWidget(self.tabs)

        # 3. Guest Mode / Skip Footer
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignCenter)
        footer_layout.setContentsMargins(0, 8, 0, 4)

        guest_btn = QPushButton("Continue as Guest Athlete (Telemetry Only)")
        guest_btn.setObjectName("btn_link")
        guest_btn.setCursor(Qt.PointingHandCursor)
        guest_btn.clicked.connect(self._on_guest_login)
        footer_layout.addWidget(guest_btn)

        root_layout.addLayout(footer_layout)

    # --------------------------------------------------------------------------
    # Tab Builders
    # --------------------------------------------------------------------------

    def _build_login_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Error / Notification Banner
        self.login_banner = QLabel()
        self.login_banner.setWordWrap(True)
        self.login_banner.setVisible(False)
        layout.addWidget(self.login_banner)

        # Identifier (Username or Email)
        id_label = QLabel("Athlete Username or Email")
        id_label.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-weight: 600; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(id_label)

        self.login_id_input = QLineEdit()
        self.login_id_input.setPlaceholderText("Enter athlete username or email")
        self.login_id_input.setMinimumHeight(44)
        self.login_id_input.returnPressed.connect(self._on_submit_login)
        layout.addWidget(self.login_id_input)

        # Password
        pw_label = QLabel("Athlete Password")
        pw_label.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-weight: 600; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(pw_label)

        self.login_pw_input = QLineEdit()
        self.login_pw_input.setEchoMode(QLineEdit.Password)
        self.login_pw_input.setPlaceholderText("Enter your password")
        self.login_pw_input.setMinimumHeight(44)
        self.login_pw_input.returnPressed.connect(self._on_submit_login)
        layout.addWidget(self.login_pw_input)

        # Options Row: Show password & Remember me
        options_layout = QHBoxLayout()
        self.login_show_pw = QCheckBox("Show password")
        self.login_show_pw.toggled.connect(
            lambda checked: self.login_pw_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        options_layout.addWidget(self.login_show_pw)

        self.login_remember_me = QCheckBox("Remember me")
        self.login_remember_me.setChecked(True)
        options_layout.addStretch()
        options_layout.addWidget(self.login_remember_me)
        layout.addLayout(options_layout)

        layout.addSpacing(10)

        # Submit Button
        self.login_submit_btn = QPushButton("SIGN IN")
        self.login_submit_btn.setObjectName("btn_primary")
        self.login_submit_btn.setMinimumHeight(48)
        self.login_submit_btn.setCursor(Qt.PointingHandCursor)
        self.login_submit_btn.clicked.connect(self._on_submit_login)
        layout.addWidget(self.login_submit_btn)

        layout.addStretch()
        return widget

    def _build_register_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Error / Notification Banner
        self.register_banner = QLabel()
        self.register_banner.setWordWrap(True)
        self.register_banner.setVisible(False)
        layout.addWidget(self.register_banner)

        # Username
        u_label = QLabel("Athlete Username *")
        u_label.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-weight: 600; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(u_label)

        self.reg_username_input = QLineEdit()
        self.reg_username_input.setPlaceholderText("e.g. pro_athlete")
        self.reg_username_input.setMinimumHeight(44)
        layout.addWidget(self.reg_username_input)

        # Email
        e_label = QLabel("Email Address *")
        e_label.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-weight: 600; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(e_label)

        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("e.g. athlete@sports.com")
        self.reg_email_input.setMinimumHeight(44)
        layout.addWidget(self.reg_email_input)

        # Full Name (Optional)
        n_label = QLabel("Full Name (Optional)")
        n_label.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-weight: 500; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(n_label)

        self.reg_name_input = QLineEdit()
        self.reg_name_input.setPlaceholderText("e.g. Jordan Smith")
        self.reg_name_input.setMinimumHeight(44)
        layout.addWidget(self.reg_name_input)

        # Password
        p_label = QLabel("Password (min 6 characters) *")
        p_label.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-weight: 600; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(p_label)

        self.reg_pw_input = QLineEdit()
        self.reg_pw_input.setEchoMode(QLineEdit.Password)
        self.reg_pw_input.setPlaceholderText("Create a secure password")
        self.reg_pw_input.setMinimumHeight(44)
        layout.addWidget(self.reg_pw_input)

        # Confirm Password
        cp_label = QLabel("Confirm Password *")
        cp_label.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-weight: 600; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 12px; letter-spacing: 0.8px;")
        layout.addWidget(cp_label)

        self.reg_cpw_input = QLineEdit()
        self.reg_cpw_input.setEchoMode(QLineEdit.Password)
        self.reg_cpw_input.setPlaceholderText("Re-enter your password")
        self.reg_cpw_input.setMinimumHeight(44)
        self.reg_cpw_input.returnPressed.connect(self._on_submit_register)
        layout.addWidget(self.reg_cpw_input)

        layout.addSpacing(8)

        # Submit Button
        self.reg_submit_btn = QPushButton("REGISTER ATHLETE")
        self.reg_submit_btn.setObjectName("btn_primary")
        self.reg_submit_btn.setMinimumHeight(48)
        self.reg_submit_btn.setCursor(Qt.PointingHandCursor)
        self.reg_submit_btn.clicked.connect(self._on_submit_register)
        layout.addWidget(self.reg_submit_btn)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    # --------------------------------------------------------------------------
    # Handlers & Validation
    # --------------------------------------------------------------------------

    def _show_banner(self, banner: QLabel, message: str, is_error: bool = True) -> None:
        banner.setObjectName("error_banner" if is_error else "success_banner")
        prefix = "Error: " if is_error else "Success: "
        banner.setText(f"{prefix}{message}")
        banner.style().unpolish(banner)
        banner.style().polish(banner)
        banner.setVisible(True)

    def _on_submit_login(self) -> None:
        identifier = self.login_id_input.text().strip()
        password = self.login_pw_input.text()

        if not identifier or not password:
            self._show_banner(self.login_banner, "Please fill in all fields.")
            return

        self.login_submit_btn.setEnabled(False)
        self.login_submit_btn.setText("Authenticating...")

        success, message, user = db.authenticate_user(identifier, password)

        self.login_submit_btn.setEnabled(True)
        self.login_submit_btn.setText("Sign In")

        if success and user:
            self._show_banner(self.login_banner, message, is_error=False)
            self.authenticated_user = user
            self.is_guest = False
            self.login_successful.emit(user)
            self.accept()
        else:
            self._show_banner(self.login_banner, message, is_error=True)

    def _on_submit_register(self) -> None:
        username = self.reg_username_input.text().strip()
        email = self.reg_email_input.text().strip()
        full_name = self.reg_name_input.text().strip()
        pw = self.reg_pw_input.text()
        cpw = self.reg_cpw_input.text()

        if not username or not email or not pw or not cpw:
            self._show_banner(self.register_banner, "All required fields (*) must be filled.")
            return

        if pw != cpw:
            self._show_banner(self.register_banner, "Passwords do not match.")
            return

        self.reg_submit_btn.setEnabled(False)
        self.reg_submit_btn.setText("Creating Account...")

        success, message, user = db.register_user(
            username=username,
            email=email,
            password=pw,
            full_name=full_name,
        )

        self.reg_submit_btn.setEnabled(True)
        self.reg_submit_btn.setText("Create Account")

        if success and user:
            self._show_banner(self.register_banner, "Account created! Logging in...", is_error=False)
            self.authenticated_user = user
            self.is_guest = False
            self.login_successful.emit(user)
            self.accept()
        else:
            self._show_banner(self.register_banner, message, is_error=True)

    def _on_guest_login(self) -> None:
        """Allows testing without creating or signing into an account."""
        self.authenticated_user = {
            "id": None,
            "username": "Guest",
            "email": "",
            "full_name": "Guest User",
        }
        self.is_guest = True
        self.accept()
