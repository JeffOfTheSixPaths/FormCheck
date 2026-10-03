"""Camera viewport widget rendering video stream and pose overlay."""

from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class CameraView(QWidget):
    """Widget displaying the live camera feed with aspect ratio preservation."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 320)

        self._current_pixmap: Optional[QPixmap] = None
        self._fps: float = 0.0
        self._is_active: bool = False
        self._placeholder_text: str = "Camera Inactive\nClick 'Start Session' to begin"

    def set_frame(self, q_img: QImage, fps: float) -> None:
        """Updates the viewport with a new video frame."""
        self._current_pixmap = QPixmap.fromImage(q_img)
        self._fps = fps
        self._is_active = True
        self.update()

    def set_inactive(self, message: Optional[str] = None) -> None:
        """Sets the viewport to inactive placeholder state."""
        self._current_pixmap = None
        self._is_active = False
        if message:
            self._placeholder_text = message
        self.update()

    def paintEvent(self, event) -> None:
        """Paints the frame scaled to fit with aspect ratio preserved, plus HUD overlays."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#0d1117"))

        if self._is_active and self._current_pixmap and not self._current_pixmap.isNull():
            # Scale pixmap maintaining aspect ratio
            scaled_pixmap = self._current_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            # Center the pixmap
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)

            # Draw HUD badge (FPS)
            fps_text = f"FPS: {self._fps:.1f}"
            font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(font)

            # Badge background
            badge_rect = painter.fontMetrics().boundingRect(fps_text)
            badge_rect.adjust(-8, -4, 8, 4)
            badge_rect.moveTo(x + 16, y + 16)

            painter.setBrush(QColor(0, 0, 0, 160))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(badge_rect, 6, 6)

            # Badge text
            painter.setPen(QColor("#00d26a"))
            painter.drawText(badge_rect, Qt.AlignCenter, fps_text)

        else:
            # Draw placeholder message
            painter.setPen(QColor("#8b949e"))
            font = QFont("Segoe UI", 14, QFont.Medium)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder_text)
