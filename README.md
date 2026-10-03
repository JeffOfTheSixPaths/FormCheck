# FormCheck 🏋️‍♂️

A modular Windows desktop application for real-time exercise form analysis powered by **PySide6 (Qt)**, **MediaPipe Pose Estimation**, and **OpenCV**.

---

## Architecture Overview

FormCheck is organized into modular layers with strict separation of concerns:

```
FormCheck/
├── main.py                     # Desktop application entrypoint & Qt initialization
├── requirements.txt            # Python dependencies (PySide6, mediapipe, opencv-python)
├── pose_landmarker.task        # MediaPipe pose estimation model bundle
├── assets/
│   └── styles.qss              # Modern dark-theme desktop styling
├── services/
│   ├── settings.py             # Global constants, paths, and hardware defaults
│   └── camera.py               # Video capture service and device enumeration
├── pose/
│   ├── landmarks.py            # PoseLandmark enum and skeleton connection definitions
│   ├── detector.py             # MediaPipe PoseLandmarker wrapper and drawing overlay
│   └── analyzer.py             # Joint angle calculations and kinematic geometry
├── exercises/
│   ├── base_exercise.py        # Abstract BaseExercise interface & ExerciseMetrics dataclass
│   ├── registry.py             # Dynamic exercise registry for pluggable exercise modules
│   ├── squat.py                # Squat form analyzer (depth, chest angle, rep count)
│   └── pushup.py               # Push-up form analyzer (elbow flexion, body alignment, rep count)
└── ui/
    ├── worker.py               # Non-blocking QThread worker for camera & pose analysis
    ├── camera_view.py          # High-DPI responsive video feed viewport with HUD
    ├── exercise_panel.py       # Sidebar for workout selection, camera device & session controls
    ├── feedback_panel.py       # Real-time form cues, score gauge, and joint angle telemetry
    ├── results_panel.py        # Repetition counters (clean vs flawed) and success rate
    └── main_window.py          # QMainWindow orchestrating layouts and thread signals
```

---

## Quickstart

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Setup Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run Application
```powershell
python main.py
```

---

## Adding New Exercises

To add a new exercise (e.g., `Deadlift`, `VerticalJump`, `VolleyballApproach`):

1. Create a new file in `exercises/` (e.g., `exercises/deadlift.py`).
2. Inherit from `BaseExercise`:
   ```python
   from exercises.base_exercise import BaseExercise, ExerciseMetrics

   class DeadliftExercise(BaseExercise):
       def __init__(self):
           super().__init__(name="Deadlift", description="Analyzes hip hinge and spinal alignment.")

       def analyze(self, landmarks, frame_shape) -> ExerciseMetrics:
           # Perform biomechanical angle checks and state transitions
           ...
   ```
3. Register the exercise in `exercises/registry.py`:
   ```python
   from exercises.deadlift import DeadliftExercise
   registry.register(DeadliftExercise)
   ```
The exercise will automatically appear in the UI dropdown without needing any UI modifications!
