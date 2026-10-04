"""Real-time feedback, form scoring, and joint kinematic telemetry panel.

A sleek, unified HUD eliminating nested group boxes and heavy bordered data blocks.
"""

from typing import Dict, Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from exercises.base_exercise import ExerciseMetrics
from services.theme import THEME


class FeedbackPanel(QWidget):
    """Visualizes live biomechanical metrics, form scores, and coaching cues in a clean HUD."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(330)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Main HUD frame
        self.hud_frame = QFrame(self)
        self.hud_frame.setObjectName("hud_frame")
        self.hud_frame.setStyleSheet(
            f"QFrame#hud_frame {{ "
            f"background-color: {THEME.BG_SURFACE}; "
            f"border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; "
            f"}} "
            f"QLabel {{ border: none; background: transparent; }}"
        )

        layout = QVBoxLayout(self.hud_frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ----------------------------------------------------------------------
        # 1. ATHLETIC EXECUTION & PHASE HUD (Top Section)
        # ----------------------------------------------------------------------
        top_header = QHBoxLayout()
        top_header.setContentsMargins(0, 0, 0, 0)

        lbl_exec_title = QLabel("ATHLETIC EXECUTION")
        lbl_exec_title.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 1.2px;"
        )
        top_header.addWidget(lbl_exec_title)
        top_header.addStretch()

        # Modern phase pill badge (replaces bulky phase box)
        self.lbl_phase = QLabel("READY")
        self.lbl_phase.setAlignment(Qt.AlignCenter)
        self.lbl_phase.setStyleSheet(
            f"background-color: rgba(165, 243, 252, 0.10); "
            f"color: {THEME.PRIMARY_COLOR}; "
            f"font-size: 10px; font-weight: 800; letter-spacing: 1.2px; "
            f"padding: 3px 10px; border-radius: 10px; "
            f"border: 1px solid rgba(165, 243, 252, 0.25); "
            f"font-family: {THEME.FONT_FAMILY_TECH};"
        )
        top_header.addWidget(self.lbl_phase)
        layout.addLayout(top_header)

        # Score readout
        self.lbl_score = QLabel("100%")
        self.lbl_score.setAlignment(Qt.AlignLeft)
        self.lbl_score.setStyleSheet(
            f"font-size: 38px; font-weight: 800; color: {THEME.COLOR_SUCCESS_BRIGHT}; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 1px;"
        )
        layout.addWidget(self.lbl_score)

        # Ultra-thin, sleek modern progress bar
        self.bar_score = QProgressBar()
        self.bar_score.setRange(0, 100)
        self.bar_score.setValue(100)
        self.bar_score.setTextVisible(False)
        self.bar_score.setFixedHeight(6)
        self.bar_score.setStyleSheet(
            f"QProgressBar {{ "
            f"background-color: {THEME.BG_INPUT}; "
            f"border: none; "
            f"border-radius: 3px; "
            f"}} "
            f"QProgressBar::chunk {{ "
            f"background-color: {THEME.COLOR_SUCCESS_BRIGHT}; "
            f"border-radius: 3px; "
            f"}}"
        )
        layout.addWidget(self.bar_score)

        # Divider line
        layout.addWidget(self._create_divider())

        # ----------------------------------------------------------------------
        # 2. COACHING CUES SECTION
        # ----------------------------------------------------------------------
        lbl_cues_title = QLabel("COACHING CUES")
        lbl_cues_title.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 1.2px;"
        )
        layout.addWidget(lbl_cues_title)

        # Single sleek coaching banner (no box inside box)
        self.lbl_feedback = QLabel("Waiting to begin athletic movement...")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setStyleSheet(
            f"background-color: {THEME.BG_INPUT}; "
            f"color: {THEME.TEXT_PRIMARY}; "
            f"font-size: 12px; "
            f"padding: 12px 14px; "
            f"min-height: 58px; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; "
            f"border-left: 3px solid {THEME.COLOR_SUCCESS_BRIGHT}; "
            f"font-family: {THEME.FONT_FAMILY}; "
            f"letter-spacing: 0.4px; "
            f"line-height: 1.4;"
        )
        layout.addWidget(self.lbl_feedback)

        # Divider line
        layout.addWidget(self._create_divider())

        # ----------------------------------------------------------------------
        # 3. JOINT KINEMATICS SECTION
        # ----------------------------------------------------------------------
        lbl_kin_title = QLabel("JOINT KINEMATICS")
        lbl_kin_title.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 1.2px;"
        )
        layout.addWidget(lbl_kin_title)

        # Placeholder label when no telemetry is streaming
        self.lbl_kin_placeholder = QLabel("Stand in view of camera to stream telemetry")
        self.lbl_kin_placeholder.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-style: italic; padding: 6px 2px;"
        )
        layout.addWidget(self.lbl_kin_placeholder)

        # Dynamic kinematics table
        self.angles_container = QWidget()
        self.angles_layout = QVBoxLayout(self.angles_container)
        self.angles_layout.setContentsMargins(0, 0, 0, 0)
        self.angles_layout.setSpacing(6)
        self.angles_container.setVisible(False)
        layout.addWidget(self.angles_container)

        self.angle_rows: Dict[str, Tuple[QLabel, QLabel]] = {}

        layout.addStretch()
        outer_layout.addWidget(self.hud_frame)

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {THEME.BORDER_COLOR}; margin: 2px 0;")
        return line

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
            f"font-size: 38px; font-weight: 800; color: {color}; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 1px;"
        )
        self.bar_score.setStyleSheet(
            f"QProgressBar {{ background-color: {THEME.BG_INPUT}; border: none; border-radius: 3px; }} "
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )

        # 2. Update phase pill
        phase_text = metrics.phase.upper()
        self.lbl_phase.setText(phase_text)
        if "BREAK" in phase_text or "FAIL" in phase_text:
            pill_color = THEME.COLOR_DANGER_BRIGHT
            pill_bg = "rgba(252, 165, 165, 0.12)"
        elif "CLEAN" in phase_text or "GOOD" in phase_text:
            pill_color = THEME.COLOR_SUCCESS_BRIGHT
            pill_bg = "rgba(134, 239, 172, 0.12)"
        else:
            pill_color = THEME.PRIMARY_COLOR
            pill_bg = "rgba(165, 243, 252, 0.10)"

        self.lbl_phase.setStyleSheet(
            f"background-color: {pill_bg}; color: {pill_color}; "
            f"font-size: 10px; font-weight: 800; letter-spacing: 1.2px; "
            f"padding: 3px 10px; border-radius: 10px; "
            f"border: 1px solid {pill_color}40; "
            f"font-family: {THEME.FONT_FAMILY_TECH};"
        )

        # 3. Update coaching cues
        if metrics.feedback:
            primary_cue = metrics.feedback[0]
            self.lbl_feedback.setText(primary_cue)
            accent = color if "Clean" not in primary_cue else THEME.COLOR_SUCCESS_BRIGHT
            self.lbl_feedback.setStyleSheet(
                f"background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; font-size: 12px; "
                f"padding: 12px 14px; min-height: 58px; border-radius: {THEME.BORDER_RADIUS_SM}; "
                f"border-left: 3px solid {accent}; font-family: {THEME.FONT_FAMILY}; letter-spacing: 0.4px;"
            )
        else:
            self.lbl_feedback.setText("Form looks steady and controlled.")
            self.lbl_feedback.setStyleSheet(
                f"background-color: {THEME.BG_INPUT}; color: {THEME.TEXT_PRIMARY}; font-size: 12px; "
                f"padding: 12px 14px; min-height: 58px; border-radius: {THEME.BORDER_RADIUS_SM}; "
                f"border-left: 3px solid {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY}; letter-spacing: 0.4px;"
            )

        # 4. Update joint kinematics list
        if metrics.joint_angles:
            self.lbl_kin_placeholder.setVisible(False)
            self.angles_container.setVisible(True)

            for name, val in metrics.joint_angles.items():
                if name not in self.angle_rows:
                    row_widget = QWidget()
                    r_layout = QHBoxLayout(row_widget)
                    r_layout.setContentsMargins(0, 3, 0, 3)

                    lbl_name = QLabel(f"{name}")
                    lbl_name.setStyleSheet(
                        f"color: {THEME.TEXT_MUTED}; font-size: 11px; font-family: {THEME.FONT_FAMILY};"
                    )
                    lbl_val = QLabel(f"{val:.1f}°")
                    lbl_val.setStyleSheet(
                        f"color: {THEME.PRIMARY_COLOR}; font-weight: 700; font-size: 13px; "
                        f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 0.5px;"
                    )
                    r_layout.addWidget(lbl_name)
                    r_layout.addStretch()
                    r_layout.addWidget(lbl_val)

                    self.angles_layout.addWidget(row_widget)
                    self.angle_rows[name] = (lbl_name, lbl_val)
                else:
                    _, lbl_val = self.angle_rows[name]
                    lbl_val.setText(f"{val:.1f}°")
        else:
            self.lbl_kin_placeholder.setVisible(True)
            self.angles_container.setVisible(False)
