"""Captures screenshots of the updated Live Drill UI:
1. Full Live Drill screen showing new sleek Results ribbon and Feedback HUD
2. Close-up of new Results telemetry ribbon (replacing Screenshot 1's 4 bulky boxes)
3. Close-up of new Feedback HUD panel (replacing Screenshot 2's nested group boxes)
4. Close-up of Athletic Drill panel with the new Volleyball & Baseball movement options (Screenshot 3)
5. Dropdown list showing all Volleyball and Baseball options
"""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from services.theme import load_application_fonts, get_stylesheet
from ui.main_window import MainWindow

ARTIFACTS_DIR = Path(r"C:\Users\vargh\.gemini\antigravity-ide\brain\50949a6f-b2af-4ddd-905a-1893c10eec1c")


def capture_updated():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    window = MainWindow(user={"id": 1, "username": "varghese", "full_name": "Varghese Athlete"})
    window.resize(1300, 820)
    window.show()
    app.processEvents()

    # Navigate to Live Drill Tracker
    window.set_active_screen(MainWindow.SCREEN_DRILL)
    app.processEvents()

    # 1. Full Live Drill Screen
    pix_drill = window.grab()
    drill_path = ARTIFACTS_DIR / "screen_drill_updated.png"
    pix_drill.save(str(drill_path))
    print(f"Captured Full Drill Screen: {drill_path}")

    # 2. Results Ribbon Close-up (Replacing Screenshot 1)
    pix_results = window.results_panel.grab()
    results_path = ARTIFACTS_DIR / "screen_results_ribbon_clean.png"
    pix_results.save(str(results_path))
    print(f"Captured Clean Results Ribbon: {results_path}")

    # 3. Feedback HUD Close-up (Replacing Screenshot 2)
    pix_feedback = window.feedback_panel.grab()
    fb_path = ARTIFACTS_DIR / "screen_feedback_hud_clean.png"
    pix_feedback.save(str(fb_path))
    print(f"Captured Clean Feedback HUD: {fb_path}")

    # 4. Exercise Panel with Volleyball & Baseball selected (Replacing Screenshot 3)
    pix_exercise = window.exercise_panel.grab()
    ex_path = ARTIFACTS_DIR / "screen_exercise_panel_athletic.png"
    pix_exercise.save(str(ex_path))
    print(f"Captured Athletic Exercise Panel: {ex_path}")

    # 5. Open combo popup
    try:
        combo = window.exercise_panel.combo_exercise
        combo.showPopup()
        app.processEvents()
        view = combo.view()
        if view and view.window():
            pix_popup = view.window().grab()
            pix_popup.save(str(ARTIFACTS_DIR / "screen_dropdown_expanded.png"))
            print("Captured Dropdown Expanded Popup.")
    except Exception as e:
        print("Popup grab error:", e)

    window.close()
    print("All captures completed successfully!")


if __name__ == "__main__":
    capture_updated()
