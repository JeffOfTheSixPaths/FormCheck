"""Pro Athlete Recommendation and Kinematic Similarity Dialog.

Displays ranked professional athlete matches using appendage angle variance cosine similarity
and enhanced dynamic trajectory congruence, complete with technical breakdowns and direct overlay loading.
"""

from typing import Any, Callable, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from services.pro_similarity_service import ProMatchResult, ProRecommendationReport
from services.theme import THEME


class ProRecommendationDialog(QDialog):
    """High-tech modal dialog presenting the closest professional athlete form recommendations."""

    load_pro_requested = Signal(str)  # Emits pro video file_path
    compare_requested = Signal(str, str)  # Emits (user_video_path, pro_video_path)

    def __init__(
        self,
        report: ProRecommendationReport,
        on_load_pro: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.report = report
        self.on_load_pro = on_load_pro
        if on_load_pro:
            self.load_pro_requested.connect(on_load_pro)

        self.setWindowTitle(f"FormCheck // Pro Athlete Form Recommendation [{report.sport.upper()}]")
        self.resize(840, 720)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(18, 16, 18, 16)
        outer_layout.setSpacing(12)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 12px 16px;"
        )
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(4)

        top_row = QHBoxLayout()
        lbl_brand = QLabel("FORMCHECK AI // PRO ATHLETE MATCHMAKER")
        lbl_brand.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 13px; font-weight: 800; letter-spacing: 1.5px;"
        )
        top_row.addWidget(lbl_brand)
        top_row.addStretch()

        badge_sport = QLabel(self.report.sport.upper())
        badge_sport.setStyleSheet(
            f"background-color: rgba(165, 243, 252, 0.12); color: {THEME.PRIMARY_COLOR}; "
            f"border: 1px solid {THEME.PRIMARY_COLOR}; border-radius: 10px; padding: 2px 10px; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 10px; font-weight: 800;"
        )
        top_row.addWidget(badge_sport)
        h_layout.addLayout(top_row)

        lbl_sub = QLabel("Calculated from 16 connected appendage angle variances, kinetic vectors, and dynamic phase correlation.")
        lbl_sub.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px;")
        h_layout.addWidget(lbl_sub)
        outer_layout.addWidget(header)

        # Scroll Area for Report Details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(4, 4, 4, 4)
        c_layout.setSpacing(14)

        # 2. Hero Card: #1 Best Match Pro
        best = self.report.best_match
        hero = QFrame()
        hero.setStyleSheet(
            f"background-color: {THEME.BG_SURFACE}; border: 1.5px solid {THEME.PRIMARY_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 16px;"
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setSpacing(12)

        # Announcement Banner: "OKAY, YOU LOOK LIKE [PRO NAME]!"
        announcement_box = QFrame()
        announcement_box.setStyleSheet(
            f"background-color: rgba(165, 243, 252, 0.10); border: 1.5px solid {THEME.PRIMARY_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS}; padding: 14px 18px;"
        )
        a_layout = QVBoxLayout(announcement_box)
        a_layout.setSpacing(4)
        lbl_say = QLabel(f"OKAY, YOU LOOK LIKE {best.pro_name.upper()}!")
        lbl_say.setStyleSheet(
            f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; "
            f"font-size: 20px; font-weight: 900; letter-spacing: 1px;"
        )
        a_layout.addWidget(lbl_say)
        lbl_sub_say = QLabel(
            f"FormCheck AI analyzed your kinetic sequencing and joint angle variances. Your movement signature has an overall {best.composite_match_score:.1f}% match with {best.pro_name}."
        )
        lbl_sub_say.setWordWrap(True)
        lbl_sub_say.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")
        a_layout.addWidget(lbl_sub_say)
        hero_layout.addWidget(announcement_box)

        h_title_row = QHBoxLayout()
        tag = QLabel("CLOSEST PROFESSIONAL MATCH")
        tag.setStyleSheet(
            f"color: {THEME.COLOR_WARNING}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 11px; font-weight: 800; letter-spacing: 1.2px;"
        )
        h_title_row.addWidget(tag)
        h_title_row.addStretch()

        lbl_pct = QLabel(f"{best.composite_match_score:.1f}% MATCH")
        lbl_pct.setStyleSheet(
            f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; "
            f"font-size: 22px; font-weight: 900; letter-spacing: 1px;"
        )
        h_title_row.addWidget(lbl_pct)
        hero_layout.addLayout(h_title_row)

        lbl_pro_name = QLabel(best.pro_title)
        lbl_pro_name.setWordWrap(True)
        lbl_pro_name.setStyleSheet(
            f"color: #ffffff; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 16px; font-weight: 800;"
        )
        hero_layout.addWidget(lbl_pro_name)

        # Triple Metric Stat Strip
        stat_strip = QFrame()
        stat_strip.setStyleSheet(
            f"background-color: {THEME.BG_INPUT}; border-radius: 6px; padding: 10px;"
        )
        ss_layout = QHBoxLayout(stat_strip)
        ss_layout.setContentsMargins(8, 4, 8, 4)

        # Metric 1: Cosine Similarity of Angle Variances
        c1 = self._create_metric_col("VARIANCE COSINE SIMILARITY", f"{best.variance_cosine_similarity:.1f}%", THEME.PRIMARY_COLOR)
        ss_layout.addWidget(c1, stretch=1)

        div1 = QFrame()
        div1.setFixedWidth(1)
        div1.setStyleSheet(f"background-color: {THEME.BORDER_COLOR};")
        ss_layout.addWidget(div1)

        # Metric 2: Enhanced Dynamic Congruence
        c2 = self._create_metric_col("DYNAMIC KINEMATIC CONGRUENCE", f"{best.enhanced_dynamic_congruence:.1f}%", THEME.COLOR_SUCCESS_BRIGHT)
        ss_layout.addWidget(c2, stretch=1)

        div2 = QFrame()
        div2.setFixedWidth(1)
        div2.setStyleSheet(f"background-color: {THEME.BORDER_COLOR};")
        ss_layout.addWidget(div2)

        # Metric 3: Kinetic Sequencing Score
        c3 = self._create_metric_col("KINETIC CHAIN TIMING", f"{best.kinetic_sequencing_score:.1f}%", THEME.COLOR_WARNING)
        ss_layout.addWidget(c3, stretch=1)

        hero_layout.addWidget(stat_strip)

        # Biomechanical Summary
        lbl_desc = QLabel(best.biomechanical_summary)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-size: 12px; line-height: 1.4;")
        hero_layout.addWidget(lbl_desc)

        # Segment Breakdown Row (Arms, Shoulders, Core/Hips, Legs)
        if best.segment_matches:
            seg_row = QHBoxLayout()
            seg_row.setSpacing(8)
            for seg_name, score in best.segment_matches.items():
                box = QFrame()
                box.setStyleSheet(f"background-color: {THEME.BG_BASE}; border: 1px solid {THEME.BORDER_COLOR}; border-radius: 4px; padding: 6px 10px;")
                b_layout = QVBoxLayout(box)
                b_layout.setContentsMargins(0, 0, 0, 0)
                b_layout.setSpacing(2)
                l_sname = QLabel(seg_name.upper())
                l_sname.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 9px; font-weight: 700; font-family: {THEME.FONT_FAMILY_DISPLAY};")
                l_sval = QLabel(f"{score:.0f}%")
                l_sval.setStyleSheet(f"color: {THEME.PRIMARY_COLOR}; font-size: 14px; font-weight: 800; font-family: {THEME.FONT_FAMILY_TECH};")
                b_layout.addWidget(l_sname)
                b_layout.addWidget(l_sval)
                seg_row.addWidget(box)
            hero_layout.addLayout(seg_row)

        # Coaching Actionable Tips
        tips_box = QFrame()
        tips_box.setStyleSheet(
            f"background-color: {THEME.BG_INPUT}; border-left: 3px solid {THEME.COLOR_SUCCESS_BRIGHT}; "
            f"border-radius: 4px; padding: 10px 12px;"
        )
        tb_layout = QVBoxLayout(tips_box)
        tb_layout.setSpacing(4)
        lbl_t_header = QLabel("COACHING RECOMMENDATIONS TO ELEVATE YOUR FORM:")
        lbl_t_header.setStyleSheet(f"color: {THEME.COLOR_SUCCESS_BRIGHT}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 11px; font-weight: 800;")
        tb_layout.addWidget(lbl_t_header)

        for tip in best.coaching_tips:
            lbl_tip = QLabel(f"• {tip}")
            lbl_tip.setWordWrap(True)
            lbl_tip.setStyleSheet(f"color: {THEME.TEXT_PRIMARY}; font-size: 11px;")
            tb_layout.addWidget(lbl_tip)

        hero_layout.addWidget(tips_box)

        # Load Directly Into Comparison Button
        btn_overlay_best = QPushButton(f"COMPARE WITH {best.pro_name.upper()}")
        btn_overlay_best.setMinimumHeight(44)
        btn_overlay_best.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.COLOR_SUCCESS}; color: #ffffff; "
            f"font-family: {THEME.FONT_FAMILY_TECH}; font-size: 12px; font-weight: 800; letter-spacing: 1px; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; border: none; }} "
            f"QPushButton:hover {{ background-color: {THEME.COLOR_SUCCESS_BRIGHT}; color: #09090b; }}"
        )
        btn_overlay_best.clicked.connect(lambda: self._select_pro(best.video_path))
        hero_layout.addWidget(btn_overlay_best)

        c_layout.addWidget(hero)

        # 3. Other Ranked Pro Contenders Table
        if len(self.report.all_ranked_matches) > 1:
            lbl_other = QLabel("ALL RANKED PROFESSIONAL CONTENDERS:")
            lbl_other.setStyleSheet(
                f"color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-top: 6px;"
            )
            c_layout.addWidget(lbl_other)

            for pro_item in self.report.all_ranked_matches[1:]:
                row = QFrame()
                row.setStyleSheet(
                    f"background-color: {THEME.BG_SURFACE}; border: 1px solid {THEME.BORDER_COLOR}; "
                    f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 10px 14px;"
                )
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(4, 2, 4, 2)

                col_info = QVBoxLayout()
                p_name = QLabel(pro_item.pro_title)
                p_name.setStyleSheet(f"color: #ffffff; font-weight: 700; font-size: 13px;")
                p_sport = QLabel(f"Sport: {pro_item.sport}  |  Variance CosSim: {pro_item.variance_cosine_similarity:.1f}%  |  Dynamic: {pro_item.enhanced_dynamic_congruence:.1f}%")
                p_sport.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px;")
                col_info.addWidget(p_name)
                col_info.addWidget(p_sport)
                r_layout.addLayout(col_info, stretch=1)

                lbl_r_score = QLabel(f"{pro_item.composite_match_score:.1f}%")
                lbl_r_score.setStyleSheet(
                    f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_TECH}; font-size: 18px; font-weight: 800; margin-right: 12px;"
                )
                r_layout.addWidget(lbl_r_score)

                btn_compare_this = QPushButton("COMPARE")
                btn_compare_this.setFixedHeight(34)
                btn_compare_this.setStyleSheet(
                    f"QPushButton {{ background-color: {THEME.BG_INPUT}; border: 1px solid {THEME.BORDER_COLOR}; "
                    f"color: {THEME.TEXT_PRIMARY}; font-family: {THEME.FONT_FAMILY_TECH}; font-weight: 700; font-size: 11px; padding: 4px 12px; }} "
                    f"QPushButton:hover {{ border-color: {THEME.PRIMARY_COLOR}; color: {THEME.PRIMARY_COLOR}; }}"
                )
                btn_compare_this.clicked.connect(lambda checked=False, p=pro_item.video_path: self._select_pro(p))
                r_layout.addWidget(btn_compare_this)

                c_layout.addWidget(row)

        # 4. Scientific Methodology & "Better Way" Explanation
        method_box = QFrame()
        method_box.setStyleSheet(
            f"background-color: {THEME.BG_BASE}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; padding: 12px;"
        )
        m_layout = QVBoxLayout(method_box)
        m_layout.setSpacing(6)

        lbl_m_title = QLabel("BIOMECHANICAL SIMILARITY METHODOLOGY & THE ENHANCED CRITERIA:")
        lbl_m_title.setStyleSheet(f"color: {THEME.PRIMARY_COLOR}; font-family: {THEME.FONT_FAMILY_DISPLAY}; font-size: 11px; font-weight: 700;")
        m_layout.addWidget(lbl_m_title)

        lbl_m_desc = QLabel(self.report.scientific_methodology)
        lbl_m_desc.setWordWrap(True)
        lbl_m_desc.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 11px; line-height: 1.4;")
        m_layout.addWidget(lbl_m_desc)
        c_layout.addWidget(method_box)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll, stretch=1)

        # Bottom Close Button
        btn_close = QPushButton("DISMISS")
        btn_close.setFixedHeight(40)
        btn_close.setStyleSheet(
            f"QPushButton {{ background-color: {THEME.BG_INPUT}; border: 1px solid {THEME.BORDER_COLOR}; "
            f"border-radius: {THEME.BORDER_RADIUS_SM}; color: {THEME.TEXT_MUTED}; font-family: {THEME.FONT_FAMILY_TECH}; font-weight: 700; }} "
            f"QPushButton:hover {{ border-color: {THEME.BORDER_LIGHT}; color: #ffffff; }}"
        )
        btn_close.clicked.connect(self.accept)
        outer_layout.addWidget(btn_close)

    def _create_metric_col(self, title: str, value: str, color_hex: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(2, 2, 2, 2)
        l.setSpacing(2)
        l.setAlignment(Qt.AlignCenter)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"color: {THEME.TEXT_MUTED}; font-size: 9px; font-weight: 700; font-family: {THEME.FONT_FAMILY_DISPLAY}; letter-spacing: 0.8px;")
        lbl_t.setAlignment(Qt.AlignCenter)

        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color: {color_hex}; font-size: 20px; font-weight: 800; font-family: {THEME.FONT_FAMILY_TECH};")
        lbl_v.setAlignment(Qt.AlignCenter)

        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return w

    def _select_pro(self, pro_video_path: str) -> None:
        """Selects pro video and triggers loading into comparison viewport."""
        self.load_pro_requested.emit(pro_video_path)
        user_path = getattr(self.report, "user_video_path", "")
        if user_path:
            self.compare_requested.emit(user_path, pro_video_path)
        self.accept()
