"""Session statistics and repetition results panel.

A sleek, unified horizontal telemetry dock replacing bulky individual card blocks
with clean continuous metric readouts and minimalist vertical hairline dividers.
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from exercises.base_exercise import ExerciseMetrics
from services.theme import THEME


class ResultsPanel(QWidget):
    """Summarizes repetitions, clean execution, form breaks, and accuracy in a clean telemetry ribbon."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(76)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Single continuous sleek telemetry bar (no chunky isolated box blocks)
        self.ribbon = QFrame(self)
        self.ribbon.setObjectName("results_ribbon")
        self.ribbon.setStyleSheet(
            f"QFrame#results_ribbon {{ "
            f"background-color: {THEME.BG_SURFACE}; "
            f"border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; "
            f"}} "
            f"QLabel {{ border: none; background: transparent; }}"
        )

        ribbon_layout = QHBoxLayout(self.ribbon)
        ribbon_layout.setContentsMargins(16, 8, 16, 8)
        ribbon_layout.setSpacing(0)

        # Metric 1: Total Reps
        col_total, self.lbl_val_total = self._create_stat_column("ATHLETE REPS", "0", THEME.TEXT_PRIMARY, "#ffffff")
        ribbon_layout.addWidget(col_total, stretch=1)
        ribbon_layout.addWidget(self._create_divider())

        # Metric 2: Clean Reps
        col_good, self.lbl_val_good = self._create_stat_column("CLEAN REPS", "0", THEME.COLOR_SUCCESS_BRIGHT, THEME.COLOR_SUCCESS_BRIGHT)
        ribbon_layout.addWidget(col_good, stretch=1)
        ribbon_layout.addWidget(self._create_divider())

        # Metric 3: Form Breaks
        col_bad, self.lbl_val_bad = self._create_stat_column("FORM BREAKS", "0", THEME.COLOR_DANGER_BRIGHT, THEME.COLOR_DANGER_BRIGHT)
        ribbon_layout.addWidget(col_bad, stretch=1)
        ribbon_layout.addWidget(self._create_divider())

        # Metric 4: Form Accuracy
        col_accuracy, self.lbl_val_accuracy = self._create_stat_column("FORM ACCURACY", "100%", THEME.PRIMARY_COLOR, THEME.PRIMARY_COLOR)
        ribbon_layout.addWidget(col_accuracy, stretch=1)

        outer_layout.addWidget(self.ribbon)

    def _create_divider(self) -> QFrame:
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background-color: {THEME.BORDER_COLOR}; margin: 8px 12px;")
        return divider

    def _create_stat_column(self, title: str, initial_value: str, val_color: str, dot_color: str) -> tuple[QWidget, QLabel]:
        col = QWidget()
        col_layout = QVBoxLayout(col)
        col_layout.setContentsMargins(4, 2, 4, 2)
        col_layout.setSpacing(2)
        col_layout.setAlignment(Qt.AlignCenter)

        # Header row: Accent dot + title
        header_widget = QWidget()
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(6)
        h_layout.setAlignment(Qt.AlignCenter)

        dot = QFrame()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 3px; border: none;")
        h_layout.addWidget(dot)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 1.2px;"
        )
        h_layout.addWidget(lbl_title)
        col_layout.addWidget(header_widget)

        # Value label
        lbl_val = QLabel(initial_value)
        lbl_val.setStyleSheet(
            f"color: {val_color}; font-size: 26px; font-weight: 800; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 1px;"
        )
        lbl_val.setAlignment(Qt.AlignCenter)
        col_layout.addWidget(lbl_val)

        return col, lbl_val

    def update_metrics(self, metrics: ExerciseMetrics) -> None:
        """Updates the statistics cards from live exercise metrics."""
        self.lbl_val_total.setText(str(metrics.rep_count))
        self.lbl_val_good.setText(str(metrics.good_reps))
        self.lbl_val_bad.setText(str(metrics.bad_reps))

        if metrics.rep_count > 0:
            pct = int((metrics.good_reps / metrics.rep_count) * 100)
            self.lbl_val_accuracy.setText(f"{pct}%")
        else:
            self.lbl_val_accuracy.setText("100%")

    def get_stats(self) -> dict:
        """Returns the current repetition counts and accuracy percentage."""
        try:
            total = int(self.lbl_val_total.text())
            good = int(self.lbl_val_good.text())
            bad = int(self.lbl_val_bad.text())
            accuracy_str = self.lbl_val_accuracy.text().replace("%", "")
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
        self.lbl_val_total.setText("0")
        self.lbl_val_good.setText("0")
        self.lbl_val_bad.setText("0")
        self.lbl_val_accuracy.setText("100%")
