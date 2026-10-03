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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.db import db
from services.settings import APP_NAME, APP_TITLE

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """Sleek authentication modal supporting login, account creation, and guest mode."""

    login_successful = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Sign In")
        self.setFixedSize(460, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.authenticated_user: Optional[Dict[str, Any]] = None
        self.is_guest: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(32, 28, 32, 28)
        root_layout.setSpacing(16)

        # 1. Branding Header
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(4)

        icon_label = QLabel("🏋️‍♂️")
        icon_font = QFont("Segoe UI Emoji", 34)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon_label)

        title_label = QLabel(APP_NAME)
        title_font = QFont("Segoe UI", 20, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #58a6ff;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("Real-Time AI Form Analyzer & Rep Tracker")
        subtitle_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)

        root_layout.addLayout(header_layout)

        # 2. Tab Widget for Login / Register
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_login_tab(), "Sign In")
        self.tabs.addTab(self._build_register_tab(), "Create Account")
        root_layout.addWidget(self.tabs)

        # 3. Guest Mode / Skip Footer
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignCenter)

        guest_btn = QPushButton("Continue as Guest (No Cloud/SQL Tracking)")
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
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)

        # Error / Notification Banner
        self.login_banner = QLabel()
        self.login_banner.setWordWrap(True)
        self.login_banner.setVisible(False)
        layout.addWidget(self.login_banner)

        # Identifier (Username or Email)
        id_label = QLabel("Username or Email")
        id_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        layout.addWidget(id_label)

        self.login_id_input = QLineEdit()
        self.login_id_input.setPlaceholderText("Enter your username or email")
        self.login_id_input.returnPressed.connect(self._on_submit_login)
        layout.addWidget(self.login_id_input)

        # Password
        pw_label = QLabel("Password")
        pw_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        layout.addWidget(pw_label)

        self.login_pw_input = QLineEdit()
        self.login_pw_input.setEchoMode(QLineEdit.Password)
        self.login_pw_input.setPlaceholderText("Enter your password")
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

        layout.addSpacing(6)

        # Submit Button
        self.login_submit_btn = QPushButton("Sign In")
        self.login_submit_btn.setObjectName("btn_primary")
        self.login_submit_btn.setCursor(Qt.PointingHandCursor)
        self.login_submit_btn.clicked.connect(self._on_submit_login)
        layout.addWidget(self.login_submit_btn)

        layout.addStretch()
        return widget

    def _build_register_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Error / Notification Banner
        self.register_banner = QLabel()
        self.register_banner.setWordWrap(True)
        self.register_banner.setVisible(False)
        layout.addWidget(self.register_banner)

        # Username
        u_label = QLabel("Username *")
        u_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        layout.addWidget(u_label)

        self.reg_username_input = QLineEdit()
        self.reg_username_input.setPlaceholderText("e.g. alex_fitness")
        layout.addWidget(self.reg_username_input)

        # Email
        e_label = QLabel("Email Address *")
        e_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        layout.addWidget(e_label)

        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("e.g. alex@example.com")
        layout.addWidget(self.reg_email_input)

        # Full Name (Optional)
        n_label = QLabel("Full Name (Optional)")
        n_label.setStyleSheet("color: #8b949e; font-weight: 500;")
        layout.addWidget(n_label)

        self.reg_name_input = QLineEdit()
        self.reg_name_input.setPlaceholderText("e.g. Alex Johnson")
        layout.addWidget(self.reg_name_input)

        # Password
        p_label = QLabel("Password (min 6 characters) *")
        p_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        layout.addWidget(p_label)

        self.reg_pw_input = QLineEdit()
        self.reg_pw_input.setEchoMode(QLineEdit.Password)
        self.reg_pw_input.setPlaceholderText("Create a secure password")
        layout.addWidget(self.reg_pw_input)

        # Confirm Password
        cp_label = QLabel("Confirm Password *")
        cp_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        layout.addWidget(cp_label)

        self.reg_cpw_input = QLineEdit()
        self.reg_cpw_input.setEchoMode(QLineEdit.Password)
        self.reg_cpw_input.setPlaceholderText("Re-enter your password")
        self.reg_cpw_input.returnPressed.connect(self._on_submit_register)
        layout.addWidget(self.reg_cpw_input)

        layout.addSpacing(4)

        # Submit Button
        self.reg_submit_btn = QPushButton("Create Account")
        self.reg_submit_btn.setObjectName("btn_primary")
        self.reg_submit_btn.setCursor(Qt.PointingHandCursor)
        self.reg_submit_btn.clicked.connect(self._on_submit_register)
        layout.addWidget(self.reg_submit_btn)

        layout.addStretch()
        return widget

    # --------------------------------------------------------------------------
    # Handlers & Validation
    # --------------------------------------------------------------------------

    def _show_banner(self, banner: QLabel, message: str, is_error: bool = True) -> None:
        banner.setObjectName("error_banner" if is_error else "success_banner")
        banner.setText(f"{'⚠️ ' if is_error else '✅ '}{message}")
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
