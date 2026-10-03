"""FormCheck UI Theme shortcut.

Allows importing directly via `from ui.theme import THEME, UITheme, get_stylesheet`
or editing `services/theme.py`.
"""

from services.theme import (
    THEME,
    UITheme,
    PRESETS,
    ACTIVE_PRESET,
    BORDER_RADIUS,
    BORDER_RADIUS_SM,
    BORDER_RADIUS_INT,
    FONT_FAMILY,
    FONT_FAMILY_DISPLAY,
    FONT_FAMILY_TECH,
    load_application_fonts,
    build_theme,
    generate_qss,
    get_stylesheet,
)

__all__ = [
    "THEME",
    "UITheme",
    "PRESETS",
    "ACTIVE_PRESET",
    "BORDER_RADIUS",
    "BORDER_RADIUS_SM",
    "BORDER_RADIUS_INT",
    "FONT_FAMILY",
    "FONT_FAMILY_DISPLAY",
    "FONT_FAMILY_TECH",
    "load_application_fonts",
    "build_theme",
    "generate_qss",
    "get_stylesheet",
]
