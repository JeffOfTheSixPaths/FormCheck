"""Test capturing MainWindow with Pro Comparison screen active, showing the clean top bar without redundancy."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure Qt platform is offscreen for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from services.theme import get_stylesheet, load_application_fonts
from ui.main_window import MainWindow

def test_main_window_comparison():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    win = MainWindow(user={"id": 1, "username": "Guest"})
    win.resize(1360, 840)
    win.show()
    app.processEvents()

    # Switch to Comparison Screen (screen index 4)
    win.set_active_screen(MainWindow.SCREEN_COMPARE)
    app.processEvents()

    # Load comparison clips
    user_vid = "C:/Users/vargh/FormCheck/server_storage/pro/1_2140_MaaC.mp4"
    ref_vid = "C:/Users/vargh/FormCheck/server_storage/pro/1_5265_MicahMaa31.mp4"
    win.comparison_screen.load_user_video(user_vid)
    win.comparison_screen.load_pro_video(ref_vid)
    win.comparison_screen.slider.setValue(500)
    win.comparison_screen._render_current_frame()
    app.processEvents()

    out_dir = Path("C:/Users/vargh/.gemini/antigravity-ide/brain/50949a6f-b2af-4ddd-905a-1893c10eec1c")
    shot_path = out_dir / "main_window_comparison_clean_verified.png"
    win.grab().save(str(shot_path))
    print(f"Saved full MainWindow comparison screenshot to: {shot_path}")

if __name__ == "__main__":
    test_main_window_comparison()
