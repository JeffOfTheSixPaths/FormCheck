"""Session statistics and repetition results panel."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from exercises.base_exercise import ExerciseMetrics
from services.theme import THEME


class ResultsPanel(QWidget):
    """Summarizes repetitions, success rate, and workout session results."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(126)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(16)

        # 1. Total Reps Box
        self.card_total = self._create_stat_card("TOTAL REPS", "0", THEME.TEXT_PRIMARY)
        layout.addWidget(self.card_total)

        # 2. Perfect Reps Box
        self.card_good = self._create_stat_card("CLEAN REPS", "0", THEME.COLOR_SUCCESS_BRIGHT)
        layout.addWidget(self.card_good)

        # 3. Flawed Reps Box
        self.card_bad = self._create_stat_card("FLAWED REPS", "0", THEME.COLOR_DANGER_BRIGHT)
        layout.addWidget(self.card_bad)

        # 4. Form Accuracy Box
        self.card_accuracy = self._create_stat_card("SUCCESS RATE", "100%", THEME.PRIMARY_COLOR)
        layout.addWidget(self.card_accuracy)

    def _create_stat_card(self, title: str, initial_value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; "
            f"border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS};"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 8, 16, 8)
        card_layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            f"font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 1.5px;"
        )
        lbl_title.setAlignment(Qt.AlignCenter)

        lbl_val = QLabel(initial_value)
        lbl_val.setStyleSheet(
            f"color: {color_hex}; font-size: 28px; font-weight: 800; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 2px;"
        )
        lbl_val.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_val)

        # Store reference on card
        card.val_label = lbl_val  # type: ignore
        return card

    def update_metrics(self, metrics: ExerciseMetrics) -> None:
        """Updates the statistics cards from live exercise metrics."""
        self.card_total.val_label.setText(str(metrics.rep_count))  # type: ignore
        self.card_good.val_label.setText(str(metrics.good_reps))  # type: ignore
        self.card_bad.val_label.setText(str(metrics.bad_reps))  # type: ignore

        if metrics.rep_count > 0:
            pct = int((metrics.good_reps / metrics.rep_count) * 100)
            self.card_accuracy.val_label.setText(f"{pct}%")  # type: ignore
        else:
            self.card_accuracy.val_label.setText("100%")  # type: ignore

    def get_stats(self) -> dict:
        """Returns the current repetition counts and accuracy percentage."""
        try:
            total = int(self.card_total.val_label.text())  # type: ignore
            good = int(self.card_good.val_label.text())  # type: ignore
            bad = int(self.card_bad.val_label.text())  # type: ignore
            accuracy_str = self.card_accuracy.val_label.text().replace("%", "")  # type: ignore
            accuracy = float(accuracy_str) if accuracy_str else 100.0
            return {
                "total_reps": total,
                "clean_reps": good,
                "flawed_reps": bad,
                "accuracy": accuracy,
            }
        except Exception:
            return {"total_reps": 0, "clean_reps": 0, "flawed_reps": 0, "accuracy": 100.0}

    def reset_stats(self) -> None:
        """Resets all metrics displayed."""
        self.card_total.val_label.setText("0")  # type: ignore
        self.card_good.val_label.setText("0")  # type: ignore
        self.card_bad.val_label.setText("0")  # type: ignore
        self.card_accuracy.val_label.setText("100%")  # type: ignore
