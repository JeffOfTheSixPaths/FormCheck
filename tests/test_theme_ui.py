"""Unit tests for FormCheck UI theming, sharp 6px borders, and color scheme customization."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.theme import (
    THEME,
    PRESETS,
    ACTIVE_PRESET,
    BORDER_RADIUS,
    BORDER_RADIUS_SM,
    BORDER_RADIUS_INT,
    build_theme,
    generate_qss,
    get_stylesheet,
)


def test_theme_sharp_borders():
    """Verify that all box and container border radii default to sharp 6px edges."""
    assert BORDER_RADIUS == "6px", f"Expected BORDER_RADIUS to be '6px', got {BORDER_RADIUS}"
    assert BORDER_RADIUS_INT == 6
    assert THEME.border_radius == "6px"

    qss = generate_qss()
    # Check that QGroupBox, QComboBox, QLineEdit, QTabWidget::pane have 6px
    assert "QGroupBox {" in qss
    assert "border-radius: 6px;" in qss
    assert "QTabWidget::pane {" in qss
    assert "QLineEdit {" in qss
    assert "QComboBox {" in qss


def test_theme_presets():
    """Verify that presets can be switched and contain all required minimal tokens."""
    required_tokens = [
        "PRIMARY_COLOR",
        "BG_BASE",
        "BG_SURFACE",
        "BG_INPUT",
        "BORDER_COLOR",
        "TEXT_PRIMARY",
        "TEXT_MUTED",
    ]

    for name, palette in PRESETS.items():
        for token in required_tokens:
            assert token in palette, f"Preset {name} is missing token {token}"
            assert palette[token].startswith("#"), f"Token {token} in {name} is not a valid hex color"

        # Build theme from preset
        theme = build_theme(name)
        assert theme.border_radius == "6px"
        qss = generate_qss(theme)
        assert palette["BG_BASE"] in qss
        assert palette["PRIMARY_COLOR"] in qss


def test_stylesheet_generation_and_sync():
    """Verify get_stylesheet generates valid QSS and syncs to assets/styles.qss."""
    qss = get_stylesheet(sync_file=True)
    assert len(qss) > 1000
    assert "border-radius: 6px" in qss

    assets_qss = Path(__file__).resolve().parent.parent / "assets" / "styles.qss"
    assert assets_qss.exists(), "assets/styles.qss was not synced"
    content = assets_qss.read_text(encoding="utf-8")
    assert "border-radius: 6px" in content


def test_custom_theme():
    """Verify custom theme builds properly with custom user overrides."""
    custom_theme = build_theme("CUSTOM")
    assert custom_theme.border_radius == "6px"
    qss = generate_qss(custom_theme)
def test_bevel_styling():
    """Verify that beveled border highlights and shadows are present in theme and QSS."""
    theme = build_theme(ACTIVE_PRESET)
    assert hasattr(theme, "border_light")
    assert hasattr(theme, "border_dark")
    assert theme.border_light.startswith("#")
    assert theme.border_dark.startswith("#")

    qss = generate_qss(theme)
    assert "border-top: 1px solid" in qss
    assert "border-bottom: 2px solid" in qss or "border-bottom: 3px solid" in qss


def test_tech_fonts():
    """Verify that SpaceX tech fonts (Orbitron & Rajdhani) are present in theme and QSS."""
    theme = build_theme(ACTIVE_PRESET)
    assert hasattr(theme, "font_family_display")
    assert hasattr(theme, "font_family_tech")
    assert "Orbitron" in theme.font_family_display
    assert "Rajdhani" in theme.font_family_tech

    qss = generate_qss(theme)
    assert "Orbitron" in qss
    assert "letter-spacing:" in qss


if __name__ == "__main__":
    test_theme_sharp_borders()
    test_theme_presets()
    test_stylesheet_generation_and_sync()
    test_custom_theme()
    test_bevel_styling()
    test_tech_fonts()
    print("ALL THEME & UI TESTS PASSED SUCCESSFULLY!")
