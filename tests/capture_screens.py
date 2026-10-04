"""Captures high-resolution visual screenshots of all FormCheck application screens:
1. Home Dashboard Screen
2. Upload & Server Vault Screen
3. Video Trim & Crop Editor Studio Screen
4. Pro Athlete Comparison Screen (with dual skeletal overlay and segment variances)
"""

import os
import sys
from pathlib import Path

# Headless offscreen rendering
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from services.theme import load_application_fonts, get_stylesheet
from services.video_service import video_service
from ui.main_window import MainWindow

ARTIFACTS_DIR = Path(r"C:\Users\vargh\.gemini\antigravity-ide\brain\50949a6f-b2af-4ddd-905a-1893c10eec1c")

def capture_all():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    window = MainWindow(user={"id": 1, "username": "varghese", "full_name": "Varghese Athlete"})
    window.resize(1280, 800)
    window.show()
    app.processEvents()

    # 1. Capture Home Screen
    window.set_active_screen(MainWindow.SCREEN_HOME)
    app.processEvents()
    pix_home = window.grab()
    home_path = ARTIFACTS_DIR / "screen_home_dashboard.png"
    pix_home.save(str(home_path))
    print(f"Captured Home Screen: {home_path}")

    # 2. Capture Upload Screen
    window.set_active_screen(MainWindow.SCREEN_UPLOAD)
    app.processEvents()
    pix_upload = window.grab()
    upload_path = ARTIFACTS_DIR / "screen_upload_vault.png"
    pix_upload.save(str(upload_path))
    print(f"Captured Upload Screen: {upload_path}")

    # 3. Capture Video Editor Screen
    pro_vids = video_service.get_pro_videos()
    sample_vid = pro_vids[0]["file_path"] if pro_vids else ""
    window.set_active_screen(MainWindow.SCREEN_EDITOR)
    if sample_vid:
        window.editor_screen.load_video(sample_vid)
    app.processEvents()
    pix_editor = window.grab()
    editor_path = ARTIFACTS_DIR / "screen_video_editor.png"
    pix_editor.save(str(editor_path))
    print(f"Captured Video Editor Screen: {editor_path}")

    # 4. Capture Pro Comparison Screen
    window.set_active_screen(MainWindow.SCREEN_COMPARE)
    if len(pro_vids) >= 2:
        window.comparison_screen.load_user_video(pro_vids[0]["file_path"])
        window.comparison_screen.load_pro_video(pro_vids[1]["file_path"])
    app.processEvents()
    pix_compare = window.grab()
    compare_path = ARTIFACTS_DIR / "screen_pro_comparison.png"
    pix_compare.save(str(compare_path))
    print(f"Captured Comparison Screen: {compare_path}")

    window.close()
    print("All screen screenshots captured successfully!")

if __name__ == "__main__":
    capture_all()
