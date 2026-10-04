"""
Automated test verifying multi-person detection, selection, and tracking on 2956-2978.mp4.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import cv2
import numpy as np
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from ui.upload_screen import UploadVideoModal
from ui.person_selector_widget import PersonSelectionDialog, PersonSelectorWidget
from services.geometry_cache import geometry_cache
from person_selector import PersonSelector

def test_multi_person_detection():
    app = QApplication.instance() or QApplication(sys.argv)

    test_video = "server_storage/pro/3_11421_2956-2978.mp4"
    if not Path(test_video).exists():
        print(f"[!] Test video not found: {test_video}")
        return

    print("=" * 60)
    print("[1] Testing raw PersonSelector detection on 2956-2978.mp4...")
    selector = PersonSelector()
    cap = cv2.VideoCapture(test_video)
    ret, frame0 = cap.read()
    assert ret, "Failed to read frame 0"
    
    dets = selector.detect_people_in_frame(frame0)
    print(f"[+] Frame 0 detections: {len(dets)} athletes found")
    for i, (bbox, lms) in enumerate(dets):
        print(f"    Athlete #{i+1}: bbox={bbox}, landmarks_count={len(lms)}")
    assert len(dets) >= 4, f"Expected >= 4 athletes on frame 0, got {len(dets)}"

    # Test scan on frame 2 and frame 20
    cap.set(cv2.CAP_PROP_POS_FRAMES, 2)
    _, frame2 = cap.read()
    dets2 = selector.detect_people_in_frame(frame2)
    print(f"[+] Frame 2 detections: {len(dets2)} athletes found")
    assert len(dets2) >= 4, f"Expected >= 4 athletes on frame 2, got {len(dets2)}"

    cap.set(cv2.CAP_PROP_POS_FRAMES, 20)
    _, frame20 = cap.read()
    dets20 = selector.detect_people_in_frame(frame20)
    print(f"[+] Frame 20 detections: {len(dets20)} athletes found")
    assert len(dets20) >= 4, f"Expected >= 4 athletes on frame 20, got {len(dets20)}"
    cap.release()

    print("\n" + "=" * 60)
    print("[2] Testing UploadVideoModal with 2956-2978.mp4...")
    modal = UploadVideoModal(user_id="test_user")
    modal.resize(1100, 720)
    modal.show()
    app.processEvents()

    # Load video directly into person selector
    loaded = modal.person_selector.load_video(test_video)
    assert loaded, "Failed to load video in PersonSelectorWidget"
    app.processEvents()

    ps_widget = modal.person_selector
    detected_count = len(ps_widget.canvas._detected_people)
    print(f"[+] PersonSelectorWidget loaded frame #{ps_widget._current_frame_idx + 1} with {detected_count} athletes")
    assert detected_count >= 4, f"Expected >= 4 athletes detected, got {detected_count}"

    # Verify buttons count
    btn_count = ps_widget.h_athletes.count() - 1  # minus label
    print(f"[+] Athlete selection buttons count: {btn_count}")
    assert btn_count >= 4, f"Expected >= 4 buttons, got {btn_count}"

    # Verify default selection is Athlete 1
    assert ps_widget._selected_idx == 0
    modal._on_person_selected(0, ps_widget._selected_bbox, ps_widget._current_frame_idx)
    app.processEvents()
    print(f"[+] Initial lock: {modal.lbl_target_title.text()}")
    assert "ATHLETE #1" in modal.lbl_target_title.text()

    # Capture screenshot with Athlete 1 selected
    screen1 = modal.grab()
    out1 = "scratch/upload_modal_athlete1_2956.png"
    screen1.save(out1)
    print(f"[+] Saved screenshot 1 to {out1}")

    print("\n" + "=" * 60)
    print("[3] Switching to Athlete #3 via pill button...")
    ps_widget._select_person_by_idx(2)
    app.processEvents()
    assert ps_widget._selected_idx == 2
    modal._on_person_selected(2, ps_widget._selected_bbox, ps_widget._current_frame_idx)
    app.processEvents()
    print(f"[+] Target lock updated: {modal.lbl_target_title.text()}")
    assert "ATHLETE #3" in modal.lbl_target_title.text()

    screen2 = modal.grab()
    out2 = "scratch/upload_modal_athlete3_2956.png"
    screen2.save(out2)
    print(f"[+] Saved screenshot 2 to {out2}")

    print("\n" + "=" * 60)
    print("[4] Testing geometry pre-computation for Athlete #2...")
    bbox_ath2 = ps_widget.canvas._detected_people[1][0]
    geom = geometry_cache.get_or_compute_geometry(
        test_video,
        initial_bbox=bbox_ath2,
        start_frame=ps_widget._current_frame_idx,
        force_recompute=True,
    )
    tracked_frames = [f for f in geom["frames"] if f["detected"]]
    print(f"[+] Geometry extracted {len(tracked_frames)}/{len(geom['frames'])} frames tracked for Athlete #2")
    assert len(tracked_frames) >= 18, f"Expected >= 18 frames tracked, got {len(tracked_frames)}"

    print("\n[+] ALL MULTI-PERSON SELECTION AND TRACKING TESTS PASSED SUCCESSFULLY!")
    modal.close()

if __name__ == "__main__":
    test_multi_person_detection()
