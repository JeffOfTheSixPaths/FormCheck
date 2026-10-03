# FormCheck: Kinematic Pose Analysis & Joint Angle Statistics

**FormCheck** is a computer vision and biomechanical analysis tool built with OpenCV and Google MediaPipe. It allows you to choose a video, interactively or programmatically select a specific person in the video, track them across frames, and extract high-precision joint angle kinematics—including the **Expected Value (Mean $\mathbb{E}[\theta]$)** and **Variance ($\text{Var}(\theta) = \sigma^2$)** of key joint angles (Femur & Shin, Torso & Femur, Ankles, etc.).

---

## Features

- **Video Selection**:
  - Set directly in code via `DEFAULT_VIDEO_PATH` in [`form_check.py`](file:///home/gohith/Music/FormCheck/form_check.py).
  - Or pass dynamically via CLI argument: `--video /path/to/video.mp4`.
- **Target Person Selection & Tracking**:
  - **Interactive Selection UI**:
    - Highlights all detected people with numbered bounding boxes (`[1] Person 1`, `[2] Person 2`, etc.).
    - Select by pressing number keys `[1-9]`, clicking on a person, or dragging a custom rectangle ROI with your mouse.
    - Scrub forward/backward through video frames (`D`/`Right Arrow` and `A`/`Left Arrow`) to locate the subject.
  - **Robust Tracking**: Multi-pose landmark association + OpenCV CSRT tracking keeps the target locked even through movement and occlusions.
- **Biomechanical Joint Angles**:
  - **Femur & Shin (Knee Angle)**: Formed by Hip $\to$ Knee $\to$ Ankle.
  - **Torso & Femur (Hip Angle)**: Formed by Shoulder $\to$ Hip $\to$ Knee.
  - **Pelvis & Femur (Abduction)**: Formed by Opposite Hip $\to$ Same Hip $\to$ Knee.
  - **Shin & Foot (Ankle Angle)**: Formed by Knee $\to$ Ankle $\to$ Foot Index.
  - **Upper Arm & Forearm (Elbow Angle)**: Formed by Shoulder $\to$ Elbow $\to$ Wrist.
  - **Torso & Upper Arm (Shoulder Angle)**: Formed by Hip $\to$ Shoulder $\to$ Elbow.
  - **Trunk Inclination**: Angle of the torso vector relative to the vertical axis ($0^\circ$ = vertical upright).
- **Comprehensive Statistics**:
  - **Expected Value ($\mathbb{E}[\theta] = \mu$)**: Average joint angle during execution.
  - **Variance ($\text{Var}(\theta) = \sigma^2$)**: Spread/dispersion of joint excursions.
  - **Standard Deviation ($\sigma$)**: Direct degree variation ($\sqrt{\text{Variance}}$).
  - **Range of Motion (ROM)**: $\Delta \theta = \max(\theta) - \min(\theta)$, with Min/Max angles.
  - **Quartiles & Median**: 25th, 50th, and 75th percentiles.
- **Outputs & Exports**:
  - **Real-Time HUD Overlay**: Live telemetry table and skeletal overlay rendered directly on the video.
  - **Annotated Video**: Saved to MP4 (`formcheck_output.mp4`).
  - **Kinematics Plot**: Publication-grade Matplotlib graph showing angle time series, expected value dashed lines, and $\pm 1 \sigma$ variance bands (`formcheck_kinematics.png`).
  - **JSON Report**: Full structured export with summary metrics and per-frame values (`formcheck_results.json`).
  - **CSV Time Series**: Tabular dataset ready for spreadsheet or statistical modeling (`formcheck_angles.csv`).

---

## Quick Start

### 1. Run Analysis on Video

To run with interactive person selection:
```bash
python form_check.py --video /path/to/your/video.mp4
```

Or simply run:
```bash
python form_check.py
```
*(Uses `DEFAULT_VIDEO_PATH` configured at the top of [`form_check.py`](file:///home/gohith/Music/FormCheck/form_check.py)).*

### 2. Interactive Controls During Selection

When the video opens:
- **Press `1` - `9`**: Instantly selects highlighted person 1, 2, 3...
- **Mouse Drag**: Click and drag a bounding box around any person to define custom ROI.
- **Mouse Click**: Click directly inside a detected person's box.
- **`Space` or `Enter`**: Confirm selection and begin analysis.
- **`D` / `Right Arrow`**: Advance to next frame.
- **`A` / `Left Arrow`**: Step back to previous frame.
- **`Q` / `Esc`**: Cancel and exit.

### 3. Controls During Video Analysis

- **`Space`**: Pause / Resume video playback.
- **`Q`**: Complete analysis early and generate reports.

---

## Command-Line Options

| Flag | Default | Description |
|---|---|---|
| `--video` | `/home/gohith/Downloads/WIN_20261003_14_31_28_Pro.mp4` | Path to input video file |
| `--no-gui` | `False` | Run headlessly (no display windows) |
| `--select-person` | `None` | Automatically select person by 1-based index (e.g. `1`) |
| `--select-bbox` | `None` | Manually specify initial box as `x,y,w,h` |
| `--output-video` | `formcheck_output.mp4` | Output path for annotated video |
| `--output-plot` | `formcheck_kinematics.png` | Output path for kinematics plot |
| `--output-json` | `formcheck_results.json` | Output path for JSON report |
| `--output-csv` | `formcheck_angles.csv` | Output path for CSV time series |
| `--model` | `pose_landmarker.task` | Path to MediaPipe task model |

---

## Mathematical Formulation

### 1. 3D Joint Angle Calculation

For three landmarks $A$ (proximal), $B$ (joint vertex), and $C$ (distal):
$$\vec{v}_1 = A - B, \quad \vec{v}_2 = C - B$$

The interior joint angle $\theta$ is:
$$\cos(\theta) = \frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}$$
$$\theta = \arccos\left(\text{clip}\left(\frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}, -1.0, 1.0\right)\right) \times \frac{180}{\pi}$$

Calculated using MediaPipe 3D `pose_world_landmarks` in metric units (meters), ensuring invariance to camera perspective distortion.

### 2. Statistical Metrics

Across $N$ observed frames for joint $j$:

- **Expected Value (Mean)**:
  $$\mathbb{E}[\theta] = \mu = \frac{1}{N} \sum_{i=1}^N \theta_i$$

- **Variance**:
  $$\text{Var}(\theta) = \sigma^2 = \frac{1}{N} \sum_{i=1}^N (\theta_i - \mu)^2$$

- **Standard Deviation**:
  $$\sigma = \sqrt{\text{Var}(\theta)}$$

- **Range of Motion (ROM)**:
  $$\text{ROM} = \max_{1 \le i \le N}(\theta_i) - \min_{1 \le i \le N}(\theta_i)$$

---

## File Structure

- [`form_check.py`](file:///home/gohith/Music/FormCheck/form_check.py): Main application entry point and pipeline orchestrator.
- [`kinematics.py`](file:///home/gohith/Music/FormCheck/kinematics.py): Joint angle geometry, landmark definitions, and running statistical accumulators.
- [`person_selector.py`](file:///home/gohith/Music/FormCheck/person_selector.py): Interactive and automated person detection & ROI selector.
- [`tracker.py`](file:///home/gohith/Music/FormCheck/tracker.py): Multi-pose landmark association and OpenCV CSRT tracking.
- [`visualizer.py`](file:///home/gohith/Music/FormCheck/visualizer.py): Skeletal rendering, joint degree callouts, and real-time HUD telemetry.
- [`reporter.py`](file:///home/gohith/Music/FormCheck/reporter.py): Summary tables, JSON exports, CSV datasets, and Matplotlib kinematic plots.
- [`pose.py`](file:///home/gohith/Music/FormCheck/pose.py): Backwards-compatible wrapper; runs FormCheck by default or live camera with `--camera`.
