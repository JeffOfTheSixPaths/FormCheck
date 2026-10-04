"""Automated verification script for interactive click-to-choose person tracking."""

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import QApplication

from services.geometry_cache import geometry_cache
from services.theme import THEME, get_stylesheet, load_application_fonts
from ui.person_selector_widget import PersonSelectionDialog, PersonSelectorWidget
from ui.upload_screen import UploadVideoModal


def main():
    # Run in offscreen mode
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication(sys.argv)
    load_application_fonts()
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
    app.setStyleSheet(get_stylesheet())

    test_video = str(repo_root / "server_storage" / "pro" / "1_2140_MaaC.mp4")
    assert Path(test_video).exists(), f"Test video not found: {test_video}"

    print(f"[*] Testing UploadVideoModal with: {test_video}")
    modal = UploadVideoModal(user_id=1)
    modal.show()
    app.processEvents()

    # 1. Load video into modal
    modal._selected_path = test_video
    modal.txt_path.setText(test_video)
    modal.txt_title.setText("Volleyball Spike - Track Test")
    loaded = modal.person_selector.load_video(test_video)
    assert loaded, "Failed to load video in modal.person_selector"
    app.processEvents()

    detected_count = len(modal.person_selector.canvas._detected_people)
    print(f"[+] Detected {detected_count} athletes on initial frame")
    assert detected_count >= 1, f"Expected at least 1 detected athlete, got {detected_count}"

    # 2. Check initial selection
    sel_bbox, frame_idx = modal.person_selector.get_selection()
    print(f"[+] Initial selection: frame={frame_idx}, bbox={sel_bbox}")
    assert sel_bbox is not None, "Initial bounding box should not be None"

    # 3. Simulate click on canvas
    # Find widget coordinate for the detected person
    w_rect = modal.person_selector.canvas._video_to_widget_rect(sel_bbox)
    click_pos = w_rect.center()
    print(f"[+] Simulating click on canvas at center {click_pos.x(), click_pos.y()} for bbox {sel_bbox}")

    press_event = QMouseEvent(
        QMouseEvent.MouseButtonPress,
        click_pos,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    modal.person_selector.canvas.mousePressEvent(press_event)
    app.processEvents()

    # Verify target label updated
    print(f"[+] Target title text: {modal.lbl_target_title.text()}")
    assert "LOCKED" in modal.lbl_target_title.text(), f"Expected LOCKED in target title, got {modal.lbl_target_title.text()}"
    print(f"[+] Target coords text: {modal.lbl_target_coords.text()}")

    # 4. Verify geometry caching with tracked person
    print("[*] Computing geometry for chosen person...")
    geom = geometry_cache.get_or_compute_geometry(
        test_video,
        initial_bbox=sel_bbox,
        start_frame=frame_idx,
        force_recompute=True,
    )
    assert geom is not None, "Geometry computation failed"
    assert "frames" in geom and len(geom["frames"]) > 0, "No frames in computed geometry"
    assert geom.get("tracked_bbox") == list(sel_bbox), f"Tracked bbox mismatch: {geom.get('tracked_bbox')} vs {sel_bbox}"
    print(f"[+] Successfully computed geometry with tracked bbox: {geom['tracked_bbox']} across {len(geom['frames'])} frames")

    # 5. Capture screenshot of UploadVideoModal
    out_dir = Path(r"C:\Users\vargh\.gemini\antigravity-ide\brain\50949a6f-b2af-4ddd-905a-1893c10eec1c")
    out_dir.mkdir(parents=True, exist_ok=True)
    shot_path = out_dir / "upload_modal_choose_person_verified.png"
    modal.grab().save(str(shot_path))
    print(f"[+] Saved UploadVideoModal screenshot to {shot_path}")

    # 6. Test PersonSelectionDialog
    print("[*] Testing PersonSelectionDialog...")
    dlg = PersonSelectionDialog(test_video)
    dlg.show()
    app.processEvents()
    dlg_bbox, dlg_f = dlg.get_selection()
    assert dlg_bbox is not None, "Dialog selection bbox should not be None"
    print(f"[+] PersonSelectionDialog selection: frame={dlg_f}, bbox={dlg_bbox}")
    dlg_shot = out_dir / "person_selection_dialog_verified.png"
    dlg.grab().save(str(dlg_shot))
    print(f"[+] Saved PersonSelectionDialog screenshot to {dlg_shot}")

    modal.close()
    dlg.close()
    print("[=== ALL INTERACTIVE PERSON SELECTION TESTS PASSED ===]")


if __name__ == "__main__":
    main()
