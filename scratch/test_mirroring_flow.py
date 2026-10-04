import os
import sys
from pathlib import Path
import cv2
import numpy as np

# Set offscreen Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from ui.comparison_screen import ComparisonScreen
from services.comparison_engine import comparison_engine

print("Initializing ComparisonScreen...")
screen = ComparisonScreen()
screen.resize(1340, 840)

pro_vid = "server_storage/pro/1_5265_MicahMaa31.mp4"
user_vid = "server_storage/personal/3_2421_2956-2978.mp4"

if not Path(pro_vid).exists():
    print(f"Error: {pro_vid} not found")
    sys.exit(1)

print("Loading pro video...")
screen.load_pro_video(pro_vid)
if Path(user_vid).exists():
    print("Loading user video...")
    screen.load_user_video(user_vid)

# Set slider to 50%
screen.slider.setValue(500)
screen._render_current_frame()

print("Testing initial state:")
assert screen._mirror_pro is False
assert screen._mirror_user is False
assert screen.btn_p_mirror.isChecked() is False
assert screen.chk_mirror_pro.isChecked() is False

# Test toggling mirror pro via btn
print("Toggling pro mirror via btn_p_mirror...")
screen.btn_p_mirror.setChecked(True)
screen.btn_p_mirror.clicked.emit()
assert screen._mirror_pro is True
assert screen.chk_mirror_pro.isChecked() is True
assert screen.btn_p_mirror.text() == "MIRRORED"

# Render in geom mode
screen._set_display_mode("geom")
screen._render_current_frame()
pm_geom = screen.viewport._overlay_pixmap
if pm_geom:
    img_geom = pm_geom.toImage()
    img_geom.save("scratch/geom_mirrored_pro.png")
    print("Saved scratch/geom_mirrored_pro.png")

# Render in overlay mode
screen._set_display_mode("overlay")
screen._render_current_frame()
pm_ov = screen.viewport._overlay_pixmap
if pm_ov:
    img_ov = pm_ov.toImage()
    img_ov.save("scratch/overlay_mirrored_pro.png")
    print("Saved scratch/overlay_mirrored_pro.png")

# Render in split mode
screen._set_display_mode("split")
screen._render_current_frame()
# Grab viewport widget
vp_img = screen.viewport.grab().toImage()
vp_img.save("scratch/split_mirrored_pro.png")
print("Saved scratch/split_mirrored_pro.png")

# Test toggling pro mirror off via checkbox
print("Toggling pro mirror off via chk_mirror_pro...")
screen.chk_mirror_pro.setChecked(False)
assert screen._mirror_pro is False
assert screen.btn_p_mirror.isChecked() is False
assert screen.btn_p_mirror.text() == "MIRROR"

# Test toggling user mirror on via btn_u_mirror
print("Toggling user mirror on via btn_u_mirror...")
screen.btn_u_mirror.setChecked(True)
screen.btn_u_mirror.clicked.emit()
assert screen._mirror_user is True
assert screen.chk_mirror_user.isChecked() is True
assert screen.btn_u_mirror.text() == "MIRRORED"

print("All mirror toggles and rendering tests passed successfully!")
