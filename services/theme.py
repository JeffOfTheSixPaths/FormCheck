"""Centralized UI Theme and Styling Configuration for FormCheck.

================================================================================
HOW TO HAND-EDIT THE UI, COLOR SCHEME & TECH FONTS:
================================================================================
1. QUICK PRESET SWITCH (1 Variable):
   Set `ACTIVE_PRESET` below to one of:
   - "MIDNIGHT_BLUE"    (Deep navy blue & vibrant cyan/electric blue)
   - "DARK_MODERN"      (Default sleek GitHub/Obsidian dark theme)
   - "EMERALD_GYM"      (High-contrast fitness theme with vivid neon green)
   - "CYBERPUNK_PURPLE" (Deep violet canvas with neon purple & bright accents)
   - "SLATE_MINIMAL"    (Neutral industrial slate & cool graphite)
   - "CUSTOM"           (Use your own custom values in section 2 below)

2. HAND-EDIT INDIVIDUAL COLOR VARIABLES (Section 2):
   Edit the values in the "CUSTOM COLOR SCHEME" section below.

3. TECHY / SPACEX FONTS (Section 3):
   - `FONT_FAMILY_DISPLAY`: Headers, branding, buttons, section titles (Default: Orbitron)
   - `FONT_FAMILY_TECH`:    Gauges, rep counts, form scores, metrics (Default: Orbitron / Rajdhani)
   - `FONT_FAMILY_BODY`:    Controls, dropdowns, inputs, descriptions (Default: Rajdhani)
================================================================================
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

# ==============================================================================
# 1. THEME PRESETS (Pick a preset OR choose "CUSTOM" to use the variables below)
# ==============================================================================
ACTIVE_PRESET = "MIDNIGHT_BLUE"  # Options: "MIDNIGHT_BLUE", "DARK_MODERN", "EMERALD_GYM", "CYBERPUNK_PURPLE", "SLATE_MINIMAL", "CUSTOM"

PRESETS: Dict[str, Dict[str, str]] = {
    "MIDNIGHT_BLUE": {
        "PRIMARY_COLOR": "#38bdf8",        # Electric sky blue
        "BG_BASE": "#0a0f1d",              # Deep navy night canvas
        "BG_SURFACE": "#0f172a",           # Dark slate blue surface
        "BG_INPUT": "#1e293b",             # Input fields & secondary buttons
        "BORDER_COLOR": "#415e87",         # Crisp, high-contrast visible solid outline for all boxes
        "BORDER_LIGHT": "#60a5fa",         # Highlight accent border
        "BORDER_DARK": "#1e293b",          # Shadow outline
        "TEXT_PRIMARY": "#f8fafc",         # Bright white
        "TEXT_MUTED": "#94a3b8",           # Soft blue-grey
        "COLOR_SUCCESS": "#059669",        # Teal green
        "COLOR_SUCCESS_BRIGHT": "#10b981", # Vibrant mint
        "COLOR_WARNING": "#d97706",        # Amber
        "COLOR_DANGER": "#dc2626",         # Crimson
        "COLOR_DANGER_BRIGHT": "#ef4444",  # Coral red
    },
    "DARK_MODERN": {
        "PRIMARY_COLOR": "#58a6ff",        # Modern GitHub blue accent
        "BG_BASE": "#0d1117",              # Main window background
        "BG_SURFACE": "#161b22",           # Cards, boxes, panels, dialogs
        "BG_INPUT": "#21262d",             # Dropdowns, inputs, secondary buttons
        "BORDER_COLOR": "#3d4b5c",         # Visible solid box border
        "BORDER_LIGHT": "#58a6ff",         # Highlight accent
        "BORDER_DARK": "#21262d",          # Shadow outline
        "TEXT_PRIMARY": "#e6edf3",         # Main text
        "TEXT_MUTED": "#8b949e",           # Labels & descriptions
        "COLOR_SUCCESS": "#238636",        # Start button, positive states
        "COLOR_SUCCESS_BRIGHT": "#00d26a", # Rep counter & clean badge
        "COLOR_WARNING": "#bb8009",        # Pause button, caution
        "COLOR_DANGER": "#b62324",         # Stop button, negative states
        "COLOR_DANGER_BRIGHT": "#ff4d4f",  # Flawed reps & error badge
    },
    "EMERALD_GYM": {
        "PRIMARY_COLOR": "#10b981",        # Performance green
        "BG_BASE": "#09090b",              # Pure dark obsidian
        "BG_SURFACE": "#18181b",           # Zinc surface
        "BG_INPUT": "#27272a",             # Zinc elements
        "BORDER_COLOR": "#4b5563",         # Clear outline
        "BORDER_LIGHT": "#6ee7b7",         # Highlight accent
        "BORDER_DARK": "#27272a",          # Shadow outline
        "TEXT_PRIMARY": "#fafafa",         # Crisp white
        "TEXT_MUTED": "#a1a1aa",           # Muted grey
        "COLOR_SUCCESS": "#16a34a",        # Leaf green
        "COLOR_SUCCESS_BRIGHT": "#22c55e", # Lime green
        "COLOR_WARNING": "#eab308",        # Yellow
        "COLOR_DANGER": "#e11d48",         # Rose
        "COLOR_DANGER_BRIGHT": "#f43f5e",  # Bright rose
    },
    "CYBERPUNK_PURPLE": {
        "PRIMARY_COLOR": "#a855f7",        # Neon purple
        "BG_BASE": "#0b0714",              # Deep violet void
        "BG_SURFACE": "#150d26",           # Dark orchid surface
        "BG_INPUT": "#21153b",             # Violet input
        "BORDER_COLOR": "#583693",         # Visible purple outline
        "BORDER_LIGHT": "#c084fc",         # Highlight accent
        "BORDER_DARK": "#2b184c",          # Shadow outline
        "TEXT_PRIMARY": "#f5f3ff",         # Violet white
        "TEXT_MUTED": "#a78bfa",           # Soft lilac
        "COLOR_SUCCESS": "#06b6d4",        # Cyan
        "COLOR_SUCCESS_BRIGHT": "#22d3ee", # Bright cyan
        "COLOR_WARNING": "#f59e0b",        # Neon amber
        "COLOR_DANGER": "#f43f5e",         # Neon pink
        "COLOR_DANGER_BRIGHT": "#fb7185",  # Soft coral
    },
    "SLATE_MINIMAL": {
        "PRIMARY_COLOR": "#60a5fa",        # Cool blue
        "BG_BASE": "#18181b",              # Soft charcoal
        "BG_SURFACE": "#27272a",           # Slate panel
        "BG_INPUT": "#3f3f46",             # Elevated slate
        "BORDER_COLOR": "#52525b",         # Clean edge outline
        "BORDER_LIGHT": "#93c5fd",         # Highlight accent
        "BORDER_DARK": "#3f3f46",          # Shadow outline
        "TEXT_PRIMARY": "#f4f4f5",         # White
        "TEXT_MUTED": "#a1a1aa",           # Dimmed text
        "COLOR_SUCCESS": "#15803d",        # Forest
        "COLOR_SUCCESS_BRIGHT": "#4ade80", # Spring green
        "COLOR_WARNING": "#ca8a04",        # Warm gold
        "COLOR_DANGER": "#b91c1c",         # Dark red
        "COLOR_DANGER_BRIGHT": "#f87171",  # Light red
    },
}

# ==============================================================================
# 2. CUSTOM COLOR SCHEME (Used if ACTIVE_PRESET = "CUSTOM", or tweak directly)
# ==============================================================================
CUSTOM_PRIMARY_COLOR       = "#38bdf8"  # Accent / Highlights / Active Tabs
CUSTOM_BG_BASE             = "#0a0f1d"  # Application Window Background
CUSTOM_BG_SURFACE          = "#0f172a"  # Cards, Boxes, Panels Background
CUSTOM_BG_INPUT            = "#1e293b"  # Input Fields, Dropdowns, Idle Badges
CUSTOM_BORDER_COLOR        = "#415e87"  # Complete 4-sided Box & Card Outlines
CUSTOM_BORDER_LIGHT        = "#60a5fa"  # Highlight Edge
CUSTOM_BORDER_DARK         = "#1e293b"  # Shadow Edge
CUSTOM_TEXT_PRIMARY        = "#f8fafc"  # Primary Text
CUSTOM_TEXT_MUTED          = "#94a3b8"  # Secondary / Subtitle Text

# Status & Button Accents
CUSTOM_COLOR_SUCCESS       = "#059669"  # Start Button
CUSTOM_COLOR_SUCCESS_BRIGHT= "#10b981"  # Clean Reps & 100% Score
CUSTOM_COLOR_WARNING       = "#d97706"  # Pause Button & Medium Score
CUSTOM_COLOR_DANGER        = "#dc2626"  # Stop Button
CUSTOM_COLOR_DANGER_BRIGHT = "#ef4444"  # Flawed Reps & Low Score

# ==============================================================================
# 3. UI GEOMETRY & SHARPNESS CONFIGURATION
# ==============================================================================
# Boxes & UI elements edge radius (Sharper 6px edges)
BORDER_RADIUS              = "6px"      # Main box/card/input edge radius (6px sharp edges)
BORDER_RADIUS_SM           = "4px"      # Inner indicators / small badges
BORDER_RADIUS_INT          = 6          # Integer value for QPainter operations

# ==============================================================================
# 3. TYPOGRAPHY & STYLISTIC TECH FONTS (SpaceX / Aerospace Telemetry Style)
# ==============================================================================
# Primary Display Font for Headers, Titles, Rep Counters & Action Buttons (SpaceX Orbitron)
FONT_FAMILY_DISPLAY        = "'Orbitron', 'Bahnschrift', 'Agency FB', sans-serif"

# Technical Telemetry & Metric Gauge Font (Wide squared curves for stats & values)
FONT_FAMILY_TECH           = "'Orbitron', 'Rajdhani', 'Bahnschrift', sans-serif"

# Body & Control Font (Clean technical curves for inputs, dropdowns, labels)
FONT_FAMILY_BODY           = "'Rajdhani', 'Bahnschrift', 'Segoe UI', sans-serif"

# Main default font
FONT_FAMILY                = FONT_FAMILY_BODY
FONT_SIZE_BASE             = "13px"
FONT_SIZE_TITLE            = "18px"
FONT_SIZE_STAT             = "28px"


@dataclass
class UITheme:
    """Active Theme instance containing all styling tokens."""
    primary_color: str
    bg_base: str
    bg_surface: str
    bg_input: str
    border_color: str
    border_light: str
    border_dark: str
    text_primary: str
    text_muted: str
    color_success: str
    color_success_bright: str
    color_warning: str
    color_danger: str
    color_danger_bright: str
    border_radius: str = BORDER_RADIUS
    border_radius_sm: str = BORDER_RADIUS_SM
    border_radius_int: int = BORDER_RADIUS_INT
    font_family: str = FONT_FAMILY
    font_family_display: str = FONT_FAMILY_DISPLAY
    font_family_tech: str = FONT_FAMILY_TECH
    font_size_base: str = FONT_SIZE_BASE

    # Property aliases for uppercase access
    @property
    def PRIMARY_COLOR(self) -> str: return self.primary_color
    @property
    def BG_BASE(self) -> str: return self.bg_base
    @property
    def BG_SURFACE(self) -> str: return self.bg_surface
    @property
    def BG_INPUT(self) -> str: return self.bg_input
    @property
    def BORDER_COLOR(self) -> str: return self.border_color
    @property
    def BORDER_LIGHT(self) -> str: return self.border_light
    @property
    def BORDER_DARK(self) -> str: return self.border_dark
    @property
    def TEXT_PRIMARY(self) -> str: return self.text_primary
    @property
    def TEXT_MUTED(self) -> str: return self.text_muted
    @property
    def COLOR_SUCCESS(self) -> str: return self.color_success
    @property
    def COLOR_SUCCESS_BRIGHT(self) -> str: return self.color_success_bright
    @property
    def COLOR_WARNING(self) -> str: return self.color_warning
    @property
    def COLOR_DANGER(self) -> str: return self.color_danger
    @property
    def COLOR_DANGER_BRIGHT(self) -> str: return self.color_danger_bright
    @property
    def BORDER_RADIUS(self) -> str: return self.border_radius
    @property
    def BORDER_RADIUS_SM(self) -> str: return self.border_radius_sm
    @property
    def radius_int(self) -> int: return self.border_radius_int
    @property
    def FONT_FAMILY(self) -> str: return self.font_family
    @property
    def FONT_FAMILY_DISPLAY(self) -> str: return self.font_family_display
    @property
    def FONT_FAMILY_TECH(self) -> str: return self.font_family_tech


def load_application_fonts() -> None:
    """Loads bundled aerospace & SpaceX tech fonts (Orbitron, Rajdhani) into Qt font database."""
    try:
        from PySide6.QtGui import QFontDatabase
        fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
        if fonts_dir.exists():
            for font_file in fonts_dir.glob("*.ttf"):
                QFontDatabase.addApplicationFont(str(font_file.resolve()))
    except Exception:
        pass


def build_theme(preset_name: str = ACTIVE_PRESET) -> UITheme:
    """Builds a UITheme instance from the selected preset or custom values."""
    if preset_name in PRESETS and preset_name != "CUSTOM":
        p = PRESETS[preset_name]
        return UITheme(
            primary_color=p["PRIMARY_COLOR"],
            bg_base=p["BG_BASE"],
            bg_surface=p["BG_SURFACE"],
            bg_input=p["BG_INPUT"],
            border_color=p["BORDER_COLOR"],
            border_light=p.get("BORDER_LIGHT", "#60a5fa"),
            border_dark=p.get("BORDER_DARK", "#1e293b"),
            text_primary=p["TEXT_PRIMARY"],
            text_muted=p["TEXT_MUTED"],
            color_success=p["COLOR_SUCCESS"],
            color_success_bright=p["COLOR_SUCCESS_BRIGHT"],
            color_warning=p["COLOR_WARNING"],
            color_danger=p["COLOR_DANGER"],
            color_danger_bright=p["COLOR_DANGER_BRIGHT"],
            border_radius=BORDER_RADIUS,
            border_radius_sm=BORDER_RADIUS_SM,
            border_radius_int=BORDER_RADIUS_INT,
        )
    return UITheme(
        primary_color=CUSTOM_PRIMARY_COLOR,
        bg_base=CUSTOM_BG_BASE,
        bg_surface=CUSTOM_BG_SURFACE,
        bg_input=CUSTOM_BG_INPUT,
        border_color=CUSTOM_BORDER_COLOR,
        border_light=CUSTOM_BORDER_LIGHT,
        border_dark=CUSTOM_BORDER_DARK,
        text_primary=CUSTOM_TEXT_PRIMARY,
        text_muted=CUSTOM_TEXT_MUTED,
        color_success=CUSTOM_COLOR_SUCCESS,
        color_success_bright=CUSTOM_COLOR_SUCCESS_BRIGHT,
        color_warning=CUSTOM_COLOR_WARNING,
        color_danger=CUSTOM_COLOR_DANGER,
        color_danger_bright=CUSTOM_COLOR_DANGER_BRIGHT,
        border_radius=BORDER_RADIUS,
        border_radius_sm=BORDER_RADIUS_SM,
        border_radius_int=BORDER_RADIUS_INT,
    )


# Active global singleton theme instance
THEME = build_theme(ACTIVE_PRESET)


def generate_qss(theme: UITheme = THEME) -> str:
    """Generates a complete Qt Style Sheet (QSS) with solid continuous box outlines and sharp 6px corners."""
    return f"""/* FormCheck Theme Stylesheet - Auto-generated from services/theme.py */
/* Clear solid 4-sided outlines with sharp {theme.border_radius} corners */

QWidget {{
    background-color: {theme.bg_base};
    color: {theme.text_primary};
    font-family: {theme.font_family};
    font-size: {theme.font_size_base};
    letter-spacing: 0.5px;
}}

/* ==========================================================================
   Group Boxes / Containers (Continuous 4-sided Outlines)
   ========================================================================== */
QGroupBox {{
    background-color: {theme.bg_surface};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius};
    margin-top: 24px;
    padding: 16px 12px 12px 12px;
    font-family: {theme.font_family_display};
    font-weight: 700;
    letter-spacing: 1.5px;
    color: {theme.primary_color};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    left: 12px;
    top: 2px;
    background-color: {theme.bg_input};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius_sm};
    color: {theme.primary_color};
    font-family: {theme.font_family_display};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}

/* ==========================================================================
   Combo Boxes (Continuous 4-sided Outlines)
   ========================================================================== */
QComboBox {{
    background-color: {theme.bg_input};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius};
    padding: 8px 12px;
    min-height: 28px;
    color: {theme.text_primary};
    font-family: {theme.font_family};
    font-weight: 600;
    letter-spacing: 0.8px;
}}

QComboBox:hover {{
    border: 1px solid {theme.primary_color};
    background-color: {theme.bg_surface};
}}

QComboBox:focus {{
    border: 1.5px solid {theme.primary_color};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {theme.bg_surface};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius_sm};
    selection-background-color: {theme.primary_color};
    selection-color: #ffffff;
    color: {theme.text_primary};
    padding: 4px;
    outline: none;
    font-family: {theme.font_family};
}}

/* ==========================================================================
   Buttons (Solid Clean Outlines)
   ========================================================================== */
QPushButton {{
    background-color: {theme.bg_input};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius};
    padding: 8px 16px;
    min-height: 28px;
    color: {theme.text_primary};
    font-family: {theme.font_family_display};
    font-weight: 700;
    letter-spacing: 1.2px;
}}

QPushButton:hover {{
    background-color: {theme.border_color};
    border: 1px solid {theme.primary_color};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {theme.bg_surface};
    border: 1px solid {theme.border_color};
}}

QPushButton:disabled {{
    background-color: {theme.bg_surface};
    border: 1px solid {theme.border_dark};
    color: {theme.text_muted};
}}

/* Start Button: Accent Action Outline */
QPushButton#btn_start {{
    background-color: {theme.color_success};
    border: 1px solid {theme.color_success_bright};
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
    border-radius: {theme.border_radius};
    min-height: 28px;
}}

QPushButton#btn_start:hover {{
    background-color: {theme.color_success_bright};
    border: 1px solid #ffffff;
}}

QPushButton#btn_start:pressed {{
    background-color: #064e3b;
    border: 1px solid {theme.color_success};
}}

/* Pause Button */
QPushButton#btn_pause {{
    background-color: {theme.color_warning};
    border: 1px solid #fbbf24;
    color: #ffffff;
    font-weight: 600;
    border-radius: {theme.border_radius};
}}

QPushButton#btn_pause:hover {{
    border: 1px solid #ffffff;
}}

QPushButton#btn_pause:pressed {{
    background-color: #78350f;
}}

/* Stop Button */
QPushButton#btn_stop {{
    background-color: {theme.color_danger};
    border: 1px solid {theme.color_danger_bright};
    color: #ffffff;
    font-weight: 600;
    border-radius: {theme.border_radius};
}}

QPushButton#btn_stop:hover {{
    border: 1px solid #ffffff;
}}

QPushButton#btn_stop:pressed {{
    background-color: #7f1d1d;
}}

/* Reset Button */
QPushButton#btn_reset {{
    background-color: {theme.bg_input};
    border: 1px solid {theme.border_color};
    color: {theme.text_muted};
    border-radius: {theme.border_radius};
}}

QPushButton#btn_reset:hover {{
    color: {theme.text_primary};
    border: 1px solid {theme.text_muted};
}}

/* Primary Dialog Button */
QPushButton#btn_primary {{
    background-color: {theme.color_success};
    border: 1px solid {theme.color_success_bright};
    color: #ffffff;
    font-family: {theme.font_family_display};
    font-size: 14px;
    letter-spacing: 1.5px;
    padding: 10px 20px;
    border-radius: {theme.border_radius};
    font-weight: 800;
    min-height: 24px;
}}

QPushButton#btn_primary:hover {{
    background-color: {theme.color_success_bright};
    border: 1px solid #ffffff;
}}

QPushButton#btn_primary:pressed {{
    background-color: #064e3b;
}}

QPushButton#btn_link {{
    background-color: transparent;
    border: none;
    color: {theme.primary_color};
    text-decoration: underline;
    padding: 6px;
    font-family: {theme.font_family_tech};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.8px;
}}

QPushButton#btn_link:hover {{
    color: {theme.border_light};
}}

/* ==========================================================================
   Progress Bar
   ========================================================================== */
QProgressBar {{
    background-color: {theme.bg_input};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius_sm};
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {theme.color_success_bright};
    border-radius: {theme.border_radius_sm};
}}

/* ==========================================================================
   Status Bar
   ========================================================================== */
QStatusBar {{
    background-color: {theme.bg_surface};
    color: {theme.text_muted};
    border-top: 1px solid {theme.border_color};
    padding: 4px;
    font-family: {theme.font_family_tech};
    font-size: 12px;
    letter-spacing: 0.8px;
}}

/* ==========================================================================
   Text Inputs (Visible 4-Sided Outlines)
   ========================================================================== */
QLineEdit {{
    background-color: {theme.bg_surface};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius};
    padding: 8px 12px;
    min-height: 28px;
    color: {theme.text_primary};
    font-family: {theme.font_family};
    font-size: 13px;
    letter-spacing: 0.5px;
    selection-background-color: {theme.primary_color};
}}

QLineEdit:hover {{
    border: 1px solid {theme.primary_color};
}}

QLineEdit:focus {{
    border: 1.5px solid {theme.primary_color};
    background-color: {theme.bg_base};
}}

QLineEdit:disabled {{
    background-color: {theme.bg_input};
    color: {theme.text_muted};
    border-color: {theme.border_dark};
}}

/* ==========================================================================
   Tabs (Clean Connected Outlines)
   ========================================================================== */
QTabWidget::pane {{
    border: 1px solid {theme.border_color};
    background-color: {theme.bg_surface};
    border-radius: {theme.border_radius};
    top: 0px;
}}

QTabBar::tab {{
    background-color: {theme.bg_base};
    color: {theme.text_muted};
    border: 1px solid {theme.border_color};
    border-bottom: none;
    border-top-left-radius: {theme.border_radius};
    border-top-right-radius: {theme.border_radius};
    padding: 8px 20px;
    margin-right: 4px;
    font-family: {theme.font_family_display};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}

QTabBar::tab:selected {{
    background-color: {theme.bg_surface};
    color: {theme.primary_color};
    border: 1px solid {theme.border_color};
    border-bottom: 2px solid {theme.primary_color};
}}

QTabBar::tab:hover:!selected {{
    background-color: {theme.bg_input};
    color: {theme.text_primary};
}}

/* ==========================================================================
   Checkboxes
   ========================================================================== */
QCheckBox {{
    color: {theme.text_muted};
    font-family: {theme.font_family};
    spacing: 8px;
}}

QCheckBox:hover {{
    color: {theme.text_primary};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: {theme.border_radius_sm};
    border: 1px solid {theme.border_color};
    background-color: {theme.bg_surface};
}}

QCheckBox::indicator:hover {{
    border-color: {theme.primary_color};
}}

QCheckBox::indicator:checked {{
    background-color: {theme.primary_color};
    border-color: {theme.primary_color};
}}

/* ==========================================================================
   Dialogs & Tables
   ========================================================================== */
QDialog {{
    background-color: {theme.bg_base};
}}

QTableWidget {{
    background-color: {theme.bg_surface};
    border: 1px solid {theme.border_color};
    border-radius: {theme.border_radius};
    gridline-color: {theme.bg_input};
    color: {theme.text_primary};
    font-family: {theme.font_family};
}}

QHeaderView::section {{
    background-color: {theme.bg_input};
    color: {theme.text_muted};
    padding: 6px;
    border: 1px solid {theme.border_color};
    font-family: {theme.font_family_display};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
}}

/* Notification Banners */
QLabel#error_banner {{
    background-color: rgba(220, 38, 38, 0.15);
    border: 1px solid {theme.color_danger_bright};
    border-radius: {theme.border_radius};
    color: {theme.color_danger_bright};
    padding: 10px 14px;
    font-weight: 600;
}}

QLabel#success_banner {{
    background-color: rgba(5, 150, 105, 0.15);
    border: 1px solid {theme.color_success_bright};
    border-radius: {theme.border_radius};
    color: {theme.color_success_bright};
    padding: 10px 14px;
    font-weight: 600;
}}

QScrollBar:vertical {{
    background-color: {theme.bg_base};
    width: 10px;
    margin: 2px 2px 2px 2px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {theme.border_color};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {theme.primary_color};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


def get_stylesheet(theme: UITheme = THEME, sync_file: bool = True) -> str:
    """Returns the compiled QSS stylesheet and optionally synchronizes assets/styles.qss."""
    qss = generate_qss(theme)
    if sync_file:
        try:
            base_dir = Path(__file__).resolve().parent.parent
            assets_dir = base_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            qss_path = assets_dir / "styles.qss"
            with open(qss_path, "w", encoding="utf-8") as f:
                f.write(qss)
        except Exception:
            pass
    return qss
