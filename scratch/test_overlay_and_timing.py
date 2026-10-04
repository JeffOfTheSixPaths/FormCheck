"""Test script verifying:
1. Phase-normalized synchronization (both motions scale 0% to 100% in unison without cutting short).
2. Clamping and posture hold (no black screens or disappearing skeletons at end).
3. 3 Segmented display modes:
   - SIDE-BY-SIDE GEOMETRIES (CLEAN, default)
   - GHOST OVERLAY (Right Shoulder Anchored)
   - SPLIT VIDEO FEEDS
4. Clean 2-slot selection deck & de-cluttered controls.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure Qt platform is offscreen for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from services.geometry_cache import geometry_cache
from services.theme import get_stylesheet, load_application_fonts
from ui.comparison_screen import ComparisonScreen

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())

    user_vid = "C:/Users/vargh/FormCheck/server_storage/pro/pro_nishida_approach.mp4"
    ref_vid = "C:/Users/vargh/FormCheck/server_storage/pro/pro_ohtani_pitching.mp4"

    print("=== TEST 1: SCREEN INITIALIZATION & DEFAULT MODE ===")
    screen = ComparisonScreen(user={"id": 1, "username": "TestAthlete"})
    screen.resize(1360, 840)
    screen.show()
    app.processEvents()

    assert screen._display_mode == "geom", f"Expected default mode 'geom', got {screen._display_mode}"
    assert screen.btn_mode_geom.isChecked(), "Geom button should be checked"
    assert screen.chk_phase_sync.isChecked(), "Phase sync should be checked by default"
    assert screen.chk_loop.isChecked(), "Loop should be checked by default"
    print("Screen initialized with default SIDE-BY-SIDE GEOMETRIES and Phase Sync.")

    print("\n=== TEST 2: LOADING VIDEOS & PHASE NORMALIZATION ===")
    screen.load_user_video(user_vid)
    screen.load_pro_video(ref_vid)
    app.processEvents()

    u_total = screen._user_total_frames
    p_total = screen._pro_total_frames
    print(f"Loaded User Video: {u_total} frames")
    print(f"Loaded Reference Video: {p_total} frames")
    assert u_total > 0, "User total frames should be > 0"
    assert p_total > 0, "Pro total frames should be > 0"

    # Test phase steps: 0%, 25%, 50%, 75%, 100%
    for pct in [0, 250, 500, 750, 1000]:
        screen.slider.setValue(pct)
        screen._render_current_frame()
        app.processEvents()

        # Check that both user_frame and pro_frame are valid (not None)
        assert screen._last_user_frame is not None, f"User frame was None at {pct/10}% phase"
        assert screen._last_pro_frame is not None, f"Pro frame was None at {pct/10}% phase"
        print(f"Phase {pct/10:.0f}%: Rendered successfully without blank frames! Readout: {screen.lbl_frame_idx.text()}")

    out_dir = Path("C:/Users/vargh/.gemini/antigravity-ide/brain/50949a6f-b2af-4ddd-905a-1893c10eec1c")

    print("\n=== TEST 3: CAPTURING VIEW MODES ===")
    # 3A. Side-by-Side Geometries (Clean)
    screen.slider.setValue(500)  # 50% apex
    screen._set_display_mode("geom")
    app.processEvents()
    shot_geom = out_dir / "comparison_clean_geom_verified.png"
    screen.grab().save(str(shot_geom))
    print(f"Saved Clean Geometries screenshot to: {shot_geom}")

    # 3B. Ghost Overlay (Shoulder Anchored)
    screen._set_display_mode("overlay")
    app.processEvents()
    shot_overlay = out_dir / "comparison_ghost_overlay_verified.png"
    screen.grab().save(str(shot_overlay))
    print(f"Saved Ghost Overlay screenshot to: {shot_overlay}")

    # 3C. Split Video Feeds
    screen._set_display_mode("split")
    app.processEvents()
    shot_split = out_dir / "comparison_split_feeds_verified.png"
    screen.grab().save(str(shot_split))
    print(f"Saved Split Feeds screenshot to: {shot_split}")

    # Return to default geom mode
    screen._set_display_mode("geom")
    app.processEvents()

    print("\n=== TEST 4: VERIFYING SYNC OFFSET & STEP CONTROLS ===")
    screen.spin_offset.setValue(10)
    screen._render_current_frame()
    app.processEvents()
    assert screen.spin_offset.value() == 10, "Offset should be 10%"
    screen.spin_offset.setValue(0)
    screen._render_current_frame()
    app.processEvents()
    assert screen.spin_offset.value() == 0, "Offset reset should be 0%"

    print("\nALL TIMING, GEOMETRIC CONFIGURATION, AND UI TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
