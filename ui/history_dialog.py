"""Workout History and Statistics Dialog displaying data queried from SQLite."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.db import db
from services.theme import THEME


class HistoryDialog(QDialog):
    """Dialog displaying historical workout logs and cumulative statistics for a user."""

    def __init__(self, user: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.user = user
        self.setWindowTitle(f"Workout History - {user.get('username', 'User')}")
        self.resize(720, 520)
        self.setMinimumSize(600, 400)

        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel(f"{self.user.get('username', 'USER').upper()}'S WORKOUT LOG")
        title_label.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 18px; font-weight: 800; letter-spacing: 2px;"
        )
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_data)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)

        # Cumulative Stats Cards
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(12)

        self.card_sessions = self._create_mini_card("SESSIONS", "0", THEME.TEXT_PRIMARY)
        self.card_clean = self._create_mini_card("CLEAN REPS", "0", THEME.COLOR_SUCCESS_BRIGHT)
        self.card_flawed = self._create_mini_card("FLAWED REPS", "0", THEME.COLOR_DANGER_BRIGHT)
        self.card_score = self._create_mini_card("AVG SCORE", "0%", THEME.PRIMARY_COLOR)

        self.stats_layout.addWidget(self.card_sessions)
        self.stats_layout.addWidget(self.card_clean)
        self.stats_layout.addWidget(self.card_flawed)
        self.stats_layout.addWidget(self.card_score)
        layout.addLayout(self.stats_layout)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Timestamp",
            "Exercise",
            "Clean Reps",
            "Flawed Reps",
            "Total",
            "Form Score",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME.BG_SURFACE};
                border: 1px solid {THEME.BORDER_COLOR};
                border-radius: {THEME.BORDER_RADIUS};
                gridline-color: {THEME.BG_INPUT};
                color: {THEME.TEXT_PRIMARY};
                font-family: {THEME.FONT_FAMILY_TECH};
            }}
            QHeaderView::section {{
                background-color: {THEME.BG_INPUT};
                color: {THEME.TEXT_MUTED};
                padding: 6px;
                border: 1px solid {THEME.BORDER_COLOR};
                font-family: {THEME.FONT_FAMILY_DISPLAY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(self.table)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _create_mini_card(self, title: str, value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; "
            f"border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS};"
        )
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 8, 12, 8)
        c_layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(
            f"color: {THEME.TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 1.2px;"
        )
        lbl_t.setAlignment(Qt.AlignCenter)

        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(
            f"color: {color_hex}; font-size: 22px; font-weight: 800; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; letter-spacing: 1.5px;"
        )
        lbl_v.setAlignment(Qt.AlignCenter)

        c_layout.addWidget(lbl_t)
        c_layout.addWidget(lbl_v)
        card.val_label = lbl_v  # type: ignore
        return card

    def _load_data(self) -> None:
        user_id = self.user.get("id")
        if not user_id:
            return

        # 1. Load cumulative stats from SQL
        summary = db.get_user_summary_stats(user_id)
        self.card_sessions.val_label.setText(str(summary["total_sessions"]))  # type: ignore
        self.card_clean.val_label.setText(str(summary["total_clean_reps"]))  # type: ignore
        self.card_flawed.val_label.setText(str(summary["total_flawed_reps"]))  # type: ignore
        self.card_score.val_label.setText(f"{summary['overall_avg_score']}%")  # type: ignore

        # 2. Load historical rows from SQL
        records = db.get_user_workout_history(user_id, limit=50)
        self.table.setRowCount(len(records))

        for row_idx, r in enumerate(records):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(r.get("created_at", ""))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(r.get("exercise_name", ""))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(r.get("clean_reps", 0))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(r.get("flawed_reps", 0))))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(r.get("total_reps", 0))))
            score_item = QTableWidgetItem(f"{r.get('avg_form_score', 0.0):.1f}%")
            self.table.setItem(row_idx, 5, score_item)
