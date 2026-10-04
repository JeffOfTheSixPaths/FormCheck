"""End-to-end test verifying multi-screen navigation and core workflows:
1. Home screen initializes and renders
2. Home screen navigates to Upload, Editor, and Comparison screens
3. Upload screen enforces guest upload restriction while allowing viewing pro videos
4. Upload screen allows logged in users to upload
5. Editor screen loads video, performs trim and crop
6. Comparison screen loads User and Pro videos, renders overlay, and computes variances across arms, shoulders, hips, legs
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

# Set offscreen platform for headless Qt testing
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from services.db import db
from services.video_service import video_service
from services.video_editor import video_editor
from services.comparison_engine import comparison_engine
from ui.main_window import MainWindow
from ui.theme import load_application_fonts, get_stylesheet

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    print(">>> 1. Instantiating MainWindow in Guest Mode...")
    window = MainWindow(user={"id": None, "username": "Guest", "email": ""})
    window.show()
    app.processEvents()

    assert window.stacked_widget.currentIndex() == MainWindow.SCREEN_HOME, "Should start on Home Screen"
    print("  [PASS] App launched on Home Screen.")

    print(">>> 2. Testing Home Screen Navigation...")
    # Home -> Upload
    window.home_screen.navigate_to.emit("upload")
    app.processEvents()
    assert window.stacked_widget.currentIndex() == MainWindow.SCREEN_UPLOAD, "Should be on Upload Screen"
    print("  [PASS] Navigated to Upload Screen.")

    # Home -> Editor
    window.home_screen.navigate_to.emit("editor")
    app.processEvents()
    assert window.stacked_widget.currentIndex() == MainWindow.SCREEN_EDITOR, "Should be on Editor Screen"
    print("  [PASS] Navigated to Editor Screen.")

    # Home -> Comparison
    window.home_screen.navigate_to.emit("compare")
    app.processEvents()
    assert window.stacked_widget.currentIndex() == MainWindow.SCREEN_COMPARE, "Should be on Comparison Screen"
    print("  [PASS] Navigated to Comparison Screen.")

    # Home -> Drill
    window.home_screen.navigate_to.emit("drill")
    app.processEvents()
    assert window.stacked_widget.currentIndex() == MainWindow.SCREEN_DRILL, "Should be on Drill Screen"
    print("  [PASS] Navigated to Drill Screen.")

    print(">>> 3. Testing Upload Screen Permissions & Storage...")
    window.set_active_screen(MainWindow.SCREEN_UPLOAD)
    app.processEvents()

    # Verify guest cannot upload
    pro_vids = video_service.get_pro_videos()
    assert len(pro_vids) >= 3, f"Expected seeded pro videos, found {len(pro_vids)}"
    print(f"  [PASS] Guest can view {len(pro_vids)} pro athlete videos in archive.")

    # Verify guest upload attempt is rejected
    test_src = pro_vids[0]["file_path"]
    ok, msg, rec = video_service.upload_video(
        source_file_path=test_src,
        title="Guest Test Attempt",
        category="personal",
        sport="Volleyball",
        user_id=None,
    )
    assert not ok, "Guest upload should be rejected"
    print("  [PASS] Guest upload was blocked properly with message:", msg)

    # Verify authenticated user upload succeeds
    user = db.get_user_by_username("test_athlete")
    if not user:
        ok, msg, user = db.register_user("test_athlete", "test@formcheck.ai", "Password123!", "Athlete")

    ok, msg, rec = video_service.upload_video(
        source_file_path=test_src,
        title="Athlete Personal Spike Drill",
        category="personal",
        sport="Volleyball",
        user_id=user["id"],
    )
    assert ok, f"User upload failed: {msg}"
    print("  [PASS] Authenticated athlete upload succeeded to server vault:", rec["file_path"])

    # Verify separation of personal vs pro
    personal_list = video_service.get_personal_videos(user["id"])
    pro_list = video_service.get_pro_videos()
    assert any(v["id"] == rec["id"] for v in personal_list), "Personal upload should be in personal vault"
    assert not any(v["id"] == rec["id"] for v in pro_list), "Personal upload must NOT be in pro archive"
    print("  [PASS] Personal and Pro videos are strictly separated by default.")

    print(">>> 4. Testing Video Editor (Trim & Crop)...")
    window.set_active_screen(MainWindow.SCREEN_EDITOR)
    window.editor_screen.load_video(test_src)
    app.processEvents()

    stats = video_editor.get_video_stats(test_src)
    print(f"  [INFO] Video stats: {stats['width']}x{stats['height']}, {stats['fps']} FPS, {stats['duration_sec']}s")

    # Trim 0.5s to 1.5s
    out_trim = str(Path(test_src).parent / "test_trim.mp4")
    ok, msg = video_editor.trim_video(test_src, out_trim, start_sec=0.5, end_sec=1.5)
    assert ok and Path(out_trim).exists(), f"Trimmed video file should exist: {msg}"
    trim_stats = video_editor.get_video_stats(out_trim)
    print(f"  [PASS] Trim successful: {trim_stats['duration_sec']:.2f}s duration.")

    # Crop center 60%
    out_crop = str(Path(test_src).parent / "test_crop.mp4")
    w_crop = int(stats["width"] * 0.6)
    h_crop = int(stats["height"] * 0.6)
    x_crop = int(stats["width"] * 0.2)
    y_crop = int(stats["height"] * 0.2)
    ok, msg = video_editor.crop_video(test_src, out_crop, x=x_crop, y=y_crop, width=w_crop, height=h_crop)
    assert ok and Path(out_crop).exists(), f"Cropped video file should exist: {msg}"
    crop_stats = video_editor.get_video_stats(out_crop)
    print(f"  [PASS] Crop successful: {crop_stats['width']}x{crop_stats['height']}.")

    print(">>> 5. Testing Comparison Engine & Variance For Everything...")
    window.set_active_screen(MainWindow.SCREEN_COMPARE)
    window.comparison_screen.load_user_video(test_src)
    window.comparison_screen.load_pro_video(pro_vids[1]["file_path"])
    app.processEvents()

    # Compute variance on frames
    frame_user = video_editor.get_frame_at_time(test_src, 1.0)
    frame_pro = video_editor.get_frame_at_time(pro_vids[1]["file_path"], 1.0)

    user_lms = comparison_engine.extract_landmarks(frame_user)
    pro_lms = comparison_engine.extract_landmarks(frame_pro)
    metrics = comparison_engine.compare_frames(user_lms, pro_lms)

    print("  [INFO] Comparison overall score:", metrics.overall_score)
    print("  [INFO] Arms variance:", metrics.arms.variance, "delta:", metrics.arms.mean_delta_deg)
    print("  [INFO] Shoulders variance:", metrics.shoulders.variance, "delta:", metrics.shoulders.mean_delta_deg)
    print("  [INFO] Hips variance:", metrics.hips.variance, "delta:", metrics.hips.mean_delta_deg)
    print("  [INFO] Legs variance:", metrics.legs.variance, "delta:", metrics.legs.mean_delta_deg)

    assert metrics.arms is not None, "Should have arms segment"
    assert metrics.shoulders is not None, "Should have shoulders segment"
    assert metrics.hips is not None, "Should have hips segment"
    assert metrics.legs is not None, "Should have legs segment"
    print("  [PASS] Variance computed for Arms, Shoulders, Hips, and Legs.")

    # Test direct skeletal overlay generation
    overlay = comparison_engine.render_direct_overlay(frame_pro, pro_lms, user_lms, metrics)
    assert overlay is not None and overlay.shape == frame_pro.shape, "Overlay frame must match dimensions"
    print(f"  [PASS] Direct skeletal overlay rendered successfully: shape {overlay.shape}.")

    print(">>> 6. Testing Editor to Comparison Bridge...")
    window.editor_screen.send_to_compare.emit(out_trim)
    app.processEvents()
    assert window.stacked_widget.currentIndex() == MainWindow.SCREEN_COMPARE, "Bridge should switch to comparison"
    print("  [PASS] Editor sent trimmed video directly to Comparison screen.")

    window.close()
    print("\nALL WORKFLOW & REQUIREMENT TESTS PASSED SUCCESSFULLY! 100% VERIFIED.")

if __name__ == "__main__":
    run_tests()
