"""FormCheck Desktop Application Entry Point."""

import logging
import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from services.settings import APP_NAME, APP_TITLE, STYLESHEET_PATH
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(APP_NAME)


def load_stylesheet() -> str:
    """Reads and returns the QSS stylesheet if present."""
    if os.path.exists(STYLESHEET_PATH):
        try:
            with open(STYLESHEET_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning("Could not read stylesheet: %s", e)
    return ""


def main() -> int:
    """Initializes and runs the PySide6 desktop GUI."""
    # Enable High DPI pixmaps
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_TITLE)

    # Set default modern font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply dark mode stylesheet
    qss = load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    # Display Login & Registration Dialog before launching main session
    login_dialog = LoginDialog()
    if login_dialog.exec() != LoginDialog.Accepted:
        logger.info("Login dismissed. Exiting FormCheck.")
        return 0

    user = login_dialog.authenticated_user
    logger.info("Launching main window for user: %s", user.get("username", "Guest"))

    window = MainWindow(user=user)
    window.show()

    logger.info("FormCheck desktop application started.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
