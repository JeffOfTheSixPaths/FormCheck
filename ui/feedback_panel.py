"""Real-time feedback, form scoring, and joint kinematic telemetry panel."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from exercises.base_exercise import ExerciseMetrics
from services.theme import THEME


class FeedbackPanel(QWidget):
    """Visualizes live biomechanical metrics, form scores, and coaching cues."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(300)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # 1. Form Score Group
        score_group = QGroupBox("Form Quality")
        score_layout = QVBoxLayout(score_group)
        score_layout.setSpacing(6)

        self.lbl_score = QLabel("100%")
        self.lbl_score.setAlignment(Qt.AlignCenter)
        self.lbl_score.setStyleSheet(
            f"font-size: 34px; font-weight: 800; color: {THEME.COLOR_SUCCESS_BRIGHT}; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 2px;"
        )
        score_layout.addWidget(self.lbl_score)

        self.bar_score = QProgressBar()
        self.bar_score.setRange(0, 100)
        self.bar_score.setValue(100)
        self.bar_score.setTextVisible(False)
        self.bar_score.setFixedHeight(10)
        score_layout.addWidget(self.bar_score)
        layout.addWidget(score_group)

        # 2. Phase Indicator
        phase_group = QGroupBox("Motion Phase")
        phase_layout = QVBoxLayout(phase_group)

        self.lbl_phase = QLabel("IDLE")
        self.lbl_phase.setAlignment(Qt.AlignCenter)
        self.lbl_phase.setStyleSheet(
            f"background-color: {THEME.BG_INPUT}; color: {THEME.PRIMARY_COLOR}; font-size: 13px; "
            f"font-weight: 700; letter-spacing: 2px; padding: 8px; border-radius: {THEME.BORDER_RADIUS}; "
            f"border: 1px solid {THEME.BORDER_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY};"
        )
        phase_layout.addWidget(self.lbl_phase)
        layout.addWidget(phase_group)

        # 3. Live Form Coaching Group
        fb_group = QGroupBox("Real-Time Coaching")
        self.fb_layout = QVBoxLayout(fb_group)
        self.fb_layout.setSpacing(6)

        self.lbl_feedback = QLabel("Waiting to begin movement...")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; color: {THEME.TEXT_PRIMARY}; font-size: 13px; "
            f"padding: 10px; border-radius: {THEME.BORDER_RADIUS}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-left: 4px solid {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY}; letter-spacing: 0.5px;"
        )
        self.fb_layout.addWidget(self.lbl_feedback)
        layout.addWidget(fb_group)

        # 4. Joint Telemetry Group
        angles_group = QGroupBox("Joint Kinematics")
        self.angles_layout = QGridLayout(angles_group)
        self.angles_layout.setSpacing(8)
        self.angle_labels = {}
        layout.addWidget(angles_group)

        layout.addStretch()

    def update_metrics(self, metrics: ExerciseMetrics) -> None:
        """Renders incoming metrics from the pose analyzer."""
        # 1. Update score
        score = max(0.0, min(100.0, metrics.score))
        self.lbl_score.setText(f"{int(score)}%")
        self.bar_score.setValue(int(score))

        if score >= 85:
            color = THEME.COLOR_SUCCESS_BRIGHT
        elif score >= 70:
            color = THEME.COLOR_WARNING
        else:
            color = THEME.COLOR_DANGER_BRIGHT

        self.lbl_score.setStyleSheet(
            f"font-size: 34px; font-weight: 800; color: {color}; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 2px;"
        )
        self.bar_score.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: {THEME.BORDER_RADIUS_SM}; }}"
        )

        # 2. Update phase
        self.lbl_phase.setText(metrics.phase.upper())

        # 3. Update feedback
        if metrics.feedback:
            primary_cue = metrics.feedback[0]
            self.lbl_feedback.setText(primary_cue)
            border_color = color if "Rep completed" not in primary_cue else THEME.COLOR_SUCCESS_BRIGHT
            self.lbl_feedback.setStyleSheet(
                f"background-color: {THEME.BG_SURFACE}; color: {THEME.TEXT_PRIMARY}; font-size: 13px; "
                f"padding: 10px; border-radius: {THEME.BORDER_RADIUS}; border: 1px solid {THEME.BORDER_COLOR}; "
                f"border-left: 4px solid {border_color}; font-family: {THEME.FONT_FAMILY}; letter-spacing: 0.5px;"
            )
        else:
            self.lbl_feedback.setText("Form looks steady.")

        # 4. Update joint angles
        for row, (name, val) in enumerate(metrics.joint_angles.items()):
            if name not in self.angle_labels:
                lbl_name = QLabel(f"{name}:")
                lbl_name.setStyleSheet(
                    f"color: {THEME.TEXT_MUTED}; font-size: 12px; font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 0.8px;"
                )
                lbl_val = QLabel(f"{val:.1f}°")
                lbl_val.setStyleSheet(
                    f"color: {THEME.PRIMARY_COLOR}; font-weight: bold; font-size: 13px; font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 1px;"
                )
                self.angles_layout.addWidget(lbl_name, row, 0)
                self.angles_layout.addWidget(lbl_val, row, 1)
                self.angle_labels[name] = (lbl_name, lbl_val)
            else:
                _, lbl_val = self.angle_labels[name]
                lbl_val.setText(f"{val:.1f}°")
