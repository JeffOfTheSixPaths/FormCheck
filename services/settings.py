"""Global application settings and configuration for FormCheck."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
STYLESHEET_PATH = ASSETS_DIR / "styles.qss"
DB_PATH = BASE_DIR / "formcheck.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# UI Theme & Styling
from services.theme import THEME

# Model settings
DEFAULT_MODEL_FILENAME = "pose_landmarker.task"
MODEL_PATH = BASE_DIR / DEFAULT_MODEL_FILENAME
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"

# Application metadata
APP_NAME = "FormCheck"
APP_TITLE = "FormCheck - Real-Time AI Exercise Form Analyzer"
APP_VERSION = "1.0.0"
WINDOW_DEFAULT_WIDTH = 1280
WINDOW_DEFAULT_HEIGHT = 800

# Camera defaults
DEFAULT_CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

# Pose Detection Confidence Defaults
MIN_POSE_DETECTION_CONFIDENCE = 0.5
MIN_POSE_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
NUM_POSES = 1
