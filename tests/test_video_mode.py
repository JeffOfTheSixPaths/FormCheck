"""Unit and integration tests for athletic video file upload mode and playback."""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from services.camera import CameraService
from ui.exercise_panel import ExercisePanel
from ui.camera_view import CameraView
from ui.worker import PoseWorker

SAMPLE_VIDEO = str(Path(__file__).resolve().parent.parent / "WIN_20261003_14_31_28_Pro.mp4")


def test_camera_service_video_mode():
    """Verify CameraService accurately opens, probes, reads, and loops video clips."""
    assert os.path.exists(SAMPLE_VIDEO), f"Sample video file not found: {SAMPLE_VIDEO}"

    info = CameraService.get_video_info(SAMPLE_VIDEO)
    assert info is not None, "Failed to retrieve video metadata"
    assert info["width"] == 1920
    assert info["height"] == 1080
    assert info["total_frames"] == 108
    assert info["fps"] > 20
    assert info["duration_seconds"] > 3

    # Test open and reading frames
    cam = CameraService(source=SAMPLE_VIDEO, loop=True)
    opened = cam.open()
    assert opened, "Failed to open sample video in CameraService"
    assert cam.is_file is True
    assert cam.native_fps > 0

    success, frame = cam.read_frame()
    assert success is True, "Failed to read first frame from video"
    assert frame is not None
    assert frame.shape[0] == 1080
    assert frame.shape[1] == 1920
    assert frame.shape[2] == 3

    # Read several frames and test seek
    for _ in range(5):
        s, f = cam.read_frame()
        assert s is True

    assert cam.current_frame_idx == 6
    seek_ok = cam.seek_frame(10)
    assert seek_ok is True
    assert cam.current_frame_idx == 10

    cam.release()
    assert cam.is_opened() is False


def test_exercise_panel_video_source():
    """Verify ExercisePanel modality switching and video file configuration."""
    app = QApplication.instance() or QApplication(sys.argv)

    panel = ExercisePanel()
    # Initial state should be camera
    info = panel.get_current_source_info()
    assert info["mode"] == "camera"

    # Switch to video mode
    panel.combo_source_mode.setCurrentIndex(1)  # video
    panel.set_video_file(SAMPLE_VIDEO)

    info2 = panel.get_current_source_info()
    assert info2["mode"] == "video"
    assert info2["source"] == SAMPLE_VIDEO
    assert info2["name"] == "WIN_20261003_14_31_28_Pro.mp4"
    assert info2["speed"] == 1.0
    assert info2["loop"] is True

    # Test speed change
    panel.combo_speed.setCurrentIndex(1)  # 0.5x
    info3 = panel.get_current_source_info()
    assert info3["speed"] == 0.5

    # Test loop toggle
    panel.chk_loop.setChecked(False)
    info4 = panel.get_current_source_info()
    assert info4["loop"] is False


def test_camera_view_source_info():
    """Verify CameraView HUD updates when switching to video mode."""
    app = QApplication.instance() or QApplication(sys.argv)

    view = CameraView()
    view.set_source_info("video", "drill_spike_clip.mp4", 0.5)
    assert view._source_mode == "video"
    assert view._source_label == "drill_spike_clip.mp4"
    assert view._playback_speed == 0.5
    assert "drill_spike_clip.mp4" in view._placeholder_text


def test_pose_worker_with_video():
    """Verify PoseWorker processes video frames without errors and emits frames."""
    app = QApplication.instance() or QApplication(sys.argv)

    worker = PoseWorker(
        source=SAMPLE_VIDEO,
        exercise_name="Squat",
        playback_speed=2.0,  # Fast forward for testing
        loop_video=False,
    )

    received_frames = []

    def on_frame(q_img, metrics, fps):
        received_frames.append(q_img)

    worker.frame_ready.connect(on_frame)
    worker.start()

    # Wait up to 3 seconds or until at least 3 frames received
    start_t = time.time()
    while len(received_frames) < 3 and time.time() - start_t < 3.0:
        app.processEvents()
        time.sleep(0.05)

    worker.stop()

    assert len(received_frames) >= 3, f"Expected at least 3 frames from PoseWorker, got {len(received_frames)}"
    first_img = received_frames[0]
    assert not first_img.isNull()
    assert first_img.width() == 1920
    assert first_img.height() == 1080


if __name__ == "__main__":
    test_camera_service_video_mode()
    test_exercise_panel_video_source()
    test_camera_view_source_info()
    test_pose_worker_with_video()
    print("ALL VIDEO MODE INTEGRATION TESTS PASSED SUCCESSFULLY!")
