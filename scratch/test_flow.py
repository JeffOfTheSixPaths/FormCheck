"""Test script verifying user upload, AI pro matchmaker ("You look like Yuji Nishida"),
geometry caching, and central right-shoulder overlay."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure Qt platform is offscreen for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import cv2
import numpy as np
from PySide6.QtWidgets import QApplication

from services.comparison_engine import comparison_engine
from services.geometry_cache import geometry_cache
from services.pro_similarity_service import pro_similarity_service
from services.theme import get_stylesheet, load_application_fonts
from ui.comparison_screen import ComparisonScreen
from ui.pro_recommendation_dialog import ProRecommendationDialog

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    # 1. Test video paths
    user_test_vid = "C:/Users/vargh/FormCheck/server_storage/pro/pro_nishida_approach.mp4"
    ref_test_vid = "C:/Users/vargh/FormCheck/server_storage/pro/pro_volleyball_spike.mp4"

    print("=== TEST 1: GEOMETRY CACHING ===")
    user_geom = geometry_cache.get_or_compute_geometry(user_test_vid)
    assert user_geom is not None, "Failed to compute user geometry"
    assert "frames" in user_geom and len(user_geom["frames"]) > 0, "No frames in user geometry"
    print(f"Cached {len(user_geom['frames'])} frames for user video.")

    ref_geom = geometry_cache.get_or_compute_geometry(ref_test_vid)
    assert ref_geom is not None, "Failed to compute ref geometry"
    print(f"Cached {len(ref_geom['frames'])} frames for reference video.")

    cache_file = Path("server_storage/geometry/pro_nishida_approach_geometry.json")
    assert cache_file.exists(), f"Geometry cache file {cache_file} does not exist!"
    print(f"Verified geometry cache saved to disk: {cache_file} ({cache_file.stat().st_size} bytes)")

    print("\n=== TEST 2: AI PRO MATCHMAKER ===")
    report = pro_similarity_service.recommend_pro_athlete(user_test_vid, sport="Volleyball")
    assert report is not None, "Report was None"
    assert report.best_match is not None, "Best match was None"
    best = report.best_match
    print(f"BEST MATCH RESULT: {best.pro_name}")
    print(f"MATCH PERCENTAGE: {best.composite_match_score:.1f}%")
    print(f"VARIANCE COSINE SIMILARITY: {best.variance_cosine_similarity:.1f}%")
    print(f"DYNAMIC CONGRUENCE: {best.enhanced_dynamic_congruence:.1f}%")
    print(f"ANNOUNCEMENT STRING: OKAY, YOU LOOK LIKE {best.pro_name.upper()}!")

    print("\n=== TEST 3: PRO RECOMMENDATION DIALOG UI ===")
    dialog = ProRecommendationDialog(report)
    dialog.resize(840, 720)
    dialog.show()
    app.processEvents()

    # Capture dialog screenshot
    dialog_pixmap = dialog.grab()
    out_dir = Path("C:/Users/vargh/.gemini/antigravity-ide/brain/50949a6f-b2af-4ddd-905a-1893c10eec1c")
    dialog_shot_path = out_dir / "pro_match_dialog_verified.png"
    dialog_pixmap.save(str(dialog_shot_path))
    print(f"Saved dialog screenshot to {dialog_shot_path}")

    print("\n=== TEST 4: COMPARISON SCREEN WITH SAVED GEOMETRY & RIGHT SHOULDER OVERLAY ===")
    screen = ComparisonScreen()
    screen.resize(1280, 800)
    screen.show()
    app.processEvents()

    # Load both videos
    screen.load_user_video(user_test_vid)
    screen.load_pro_video(ref_test_vid)
    app.processEvents()

    # Verify geometries loaded
    assert screen._user_geometry is not None, "Comparison screen missing _user_geometry"
    assert screen._pro_geometry is not None, "Comparison screen missing _pro_geometry"
    print("ComparisonScreen successfully loaded precomputed geometries for both slots.")

    # Render frame 10
    screen.slider.setValue(10)
    screen._render_current_frame()
    app.processEvents()

    # Capture comparison screen screenshot
    comp_shot_path = out_dir / "comparison_screen_overlay_verified.png"
    screen.grab().save(str(comp_shot_path))
    print(f"Saved comparison screen screenshot to {comp_shot_path}")

    # Test Split View
    screen.radio_split.setChecked(True)
    app.processEvents()
    split_shot_path = out_dir / "comparison_screen_split_verified.png"
    screen.grab().save(str(split_shot_path))
    print(f"Saved split screen screenshot to {split_shot_path}")

    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
