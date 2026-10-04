"""Test verifying that detailed joint kinematics cards are in a collapsible dropdown closed by default."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure Qt platform is offscreen for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from services.theme import get_stylesheet, load_application_fonts
from ui.comparison_screen import ComparisonScreen

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    user_vid = "C:/Users/vargh/FormCheck/server_storage/pro/1_2140_MaaC.mp4"
    ref_vid = "C:/Users/vargh/FormCheck/server_storage/pro/1_5265_MicahMaa31.mp4"

    screen = ComparisonScreen(user={"id": 1, "username": "TestAthlete"})
    screen.resize(1360, 840)
    screen.show()
    app.processEvents()

    # Load videos so metrics are populated
    screen.load_user_video(user_vid)
    screen.load_pro_video(ref_vid)
    screen.slider.setValue(500)
    screen._render_current_frame()
    app.processEvents()

    print("=== TEST 1: DROPDOWN CLOSED BY DEFAULT ===")
    assert not screen.details_container.isVisible(), "Dropdown container should be CLOSED (hidden) by default!"
    assert "> DETAILED KINEMATICS" in screen.btn_toggle_details.text(), "Button should show expand indicator"
    print("Verified: Detailed kinematic info is CLOSED by default!")

    out_dir = Path("C:/Users/vargh/.gemini/antigravity-ide/brain/50949a6f-b2af-4ddd-905a-1893c10eec1c")
    shot_closed = out_dir / "comparison_dropdown_closed_verified.png"
    screen.grab().save(str(shot_closed))
    print(f"Saved screenshot with dropdown CLOSED to: {shot_closed}")

    print("\n=== TEST 2: TOGGLING DROPDOWN OPEN ===")
    screen.btn_toggle_details.click()
    app.processEvents()

    assert screen.details_container.isVisible(), "Dropdown container should now be OPEN (visible)!"
    assert "v DETAILED KINEMATICS" in screen.btn_toggle_details.text(), "Button should show collapse indicator"
    print("Verified: Dropdown opened on click!")

    shot_open = out_dir / "comparison_dropdown_open_verified.png"
    screen.grab().save(str(shot_open))
    print(f"Saved screenshot with dropdown OPEN to: {shot_open}")

    print("\n=== TEST 3: SEGMENT FILTERING ===")
    # Filter to arms only
    screen.combo_segment_filter.setCurrentIndex(1)  # Arms
    app.processEvents()
    assert screen.card_arms.isVisible(), "Arms card should be visible"
    assert not screen.card_legs.isVisible(), "Legs card should be hidden when filtered to arms"
    print("Verified: Filtered to Arms only!")

    # Reset filter to all
    screen.combo_segment_filter.setCurrentIndex(0)
    app.processEvents()
    assert screen.card_arms.isVisible() and screen.card_legs.isVisible(), "All cards should be visible"
    print("Verified: Reset filter to All segments!")

    # Close dropdown again
    screen.btn_toggle_details.click()
    app.processEvents()
    assert not screen.details_container.isVisible(), "Dropdown should be closed again!"
    print("Verified: Dropdown collapses back smoothly!")

    print("\nALL DROPDOWN VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
