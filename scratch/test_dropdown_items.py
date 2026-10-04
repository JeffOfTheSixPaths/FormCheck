"""Test verifying the exact items in both dropdowns of ComparisonScreen."""

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

    print("=== TEST 1: GUEST USER DROPDOWNS ===")
    screen_guest = ComparisonScreen(user={"id": None, "username": "Guest"})
    screen_guest.resize(1360, 840)
    screen_guest.show()
    app.processEvents()

    user_items_guest = [screen_guest.combo_user_vault.itemText(i) for i in range(screen_guest.combo_user_vault.count())]
    pro_items_guest = [screen_guest.combo_pro_vault.itemText(i) for i in range(screen_guest.combo_pro_vault.count())]

    print("\nGuest Slot 1 (YOUR ATHLETIC FORM) items:")
    for item in user_items_guest:
        print(f"  - {item}")

    print("\nGuest Slot 2 (REFERENCE BENCHMARK) items:")
    for item in pro_items_guest:
        print(f"  - {item}")

    # Verify no fake dummy pro athletes are present
    fake_names = [
        "Shohei Ohtani", "Aaron Judge", "Mookie Betts", "Nolan Arenado",
        "Yuji Nishida", "Earvin N'Gapeth", "Jenia Grebennikov", "Micah Christenson",
        "Elite Barbell Squat Mechanics", "Elite Squat Mechanics"
    ]
    for name in fake_names:
        for item in user_items_guest:
            assert name not in item, f"Fake athlete {name} should NOT be in user dropdown!"
        for item in pro_items_guest:
            assert name not in item, f"Fake athlete {name} should NOT be in pro dropdown!"

    # Verify real locally uploaded videos ARE present
    assert any("Maac" in item for item in pro_items_guest), "Real locally uploaded 'Maac' should be in pro benchmark dropdown!"
    assert any("Micahmaa31" in item for item in pro_items_guest), "Real locally uploaded 'Micahmaa31' should be in pro benchmark dropdown!"

    print("\n=== TEST 2: AUTHENTICATED ATHLETE (USER 1) DROPDOWNS ===")
    screen_auth = ComparisonScreen(user={"id": 1, "username": "jeff"})
    screen_auth.resize(1360, 840)
    screen_auth.show()
    app.processEvents()

    user_items_auth = [screen_auth.combo_user_vault.itemText(i) for i in range(screen_auth.combo_user_vault.count())]
    pro_items_auth = [screen_auth.combo_pro_vault.itemText(i) for i in range(screen_auth.combo_pro_vault.count())]

    print("\nAuthenticated User 1 Slot 1 (YOUR ATHLETIC FORM) items:")
    for item in user_items_auth:
        print(f"  - {item}")

    print("\nAuthenticated User 1 Slot 2 (REFERENCE BENCHMARK) items:")
    for item in pro_items_auth:
        print(f"  - {item}")

    assert any("volleyball setting" in item for item in user_items_auth), "User's personal drill 'volleyball setting' should be in slot 1!"

    out_dir = Path("C:/Users/vargh/.gemini/antigravity-ide/brain/50949a6f-b2af-4ddd-905a-1893c10eec1c")
    shot_path = out_dir / "comparison_dropdowns_cleaned_verified.png"
    screen_auth.grab().save(str(shot_path))
    print(f"\nSaved verified screen capture to: {shot_path}")
    print("\nAll dropdown tests passed successfully!")

if __name__ == "__main__":
    run_tests()
