#!/usr/bin/env python3
"""
FormCheck: Kinematic Pose Analysis & Joint Angle Statistics
Tracks a chosen person in a video, calculates joint angles (Femur & Shin, Torso & Femur,
Ankle, etc.), and reports the Expected Value (Mean) and Variance across frames.
"""

import argparse
import os
import sys
import time
import cv2
import numpy as np

from kinematics import KinematicTracker
from person_selector import PersonSelector
from reporter import KinematicReporter
from tracker import PersonPoseTracker
from visualizer import PoseVisualizer


# ==============================================================================
# CONFIGURATION: You can change the video path here in code directly!
# ==============================================================================
DEFAULT_VIDEO_PATH = "/home/gohith/Downloads/WIN_20261003_14_31_28_Pro.mp4"
DEFAULT_MODEL_PATH = "pose_landmarker.task"
# ==============================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="FormCheck: Select a person in a video and compute joint angle statistics (Expected Value, Variance, etc.)."
    )
    parser.add_argument(
        "--video",
        type=str,
        default=DEFAULT_VIDEO_PATH,
        help=f"Path to input video file (default: {DEFAULT_VIDEO_PATH})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help=f"Path to MediaPipe pose_landmarker.task model (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run headlessly without opening interactive display windows",
    )
    parser.add_argument(
        "--select-person",
        type=int,
        default=None,
        help="Automatically select person by 1-based index (e.g. 1 for primary person)",
    )
    parser.add_argument(
        "--select-bbox",
        type=str,
        default=None,
        help="Specify bounding box manually as 'x,y,w,h' (e.g. '450,150,420,880')",
    )
    parser.add_argument(
        "--output-video",
        type=str,
        default="formcheck_output.mp4",
        help="Path to save the annotated video (set to '' or 'none' to skip)",
    )
    parser.add_argument(
        "--output-plot",
        type=str,
        default="formcheck_kinematics.png",
        help="Path to save the kinematic angle plot (default: formcheck_kinematics.png)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="formcheck_results.json",
        help="Path to save the JSON analysis report (default: formcheck_results.json)",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="formcheck_angles.csv",
        help="Path to save the CSV angles time series (default: formcheck_angles.csv)",
    )
    parser.add_argument(
        "--skip-frames",
        type=int,
        default=0,
        help="Skip the first N frames before analysis",
    )
    return parser.parse_args()


def resolve_video_path(requested_path: str) -> str:
    """Checks if requested video exists, and searches common locations if not found."""
    if os.path.isfile(requested_path):
        return os.path.abspath(requested_path)

    # Search in common locations
    candidates = [
        os.path.join(".", os.path.basename(requested_path)),
        os.path.expanduser(f"~/Downloads/{os.path.basename(requested_path)}"),
        os.path.expanduser("~/Downloads/WIN_20261003_14_31_28_Pro.mp4"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            print(f"[!] Target video '{requested_path}' not found at exact path. Using found candidate: {c}")
            return os.path.abspath(c)

    # Search current directory for any mp4/mov/avi
    for fname in os.listdir("."):
        if fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            print(f"[!] Using video in current directory: {fname}")
            return os.path.abspath(fname)

    raise FileNotFoundError(
        f"Video file not found at '{requested_path}'. Please check DEFAULT_VIDEO_PATH or specify --video <path>."
    )


def main():
    args = parse_args()

    # Step 1: Verify model and video file
    if not os.path.isfile(args.model):
        print(f"ERROR: MediaPipe model not found at '{args.model}'")
        print("Please ensure pose_landmarker.task is in the working directory.")
        sys.exit(1)

    try:
        video_path = resolve_video_path(args.video)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("=" * 70)
    print("                FORMCHECK: JOINT ANGLE KINEMATICS                ")
    print("=" * 70)
    print(f" Loaded Video: {video_path}")
    print(f" Model Asset:  {args.model}")

    # Inspect video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open video file '{video_path}'")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_s = total_frames / fps if fps > 0 else 0.0
    cap.release()

    print(
        f" Video Info:   {width}x{height} @ {fps:.1f} FPS | {total_frames} frames ({duration_s:.1f}s)"
    )
    print("=" * 70)

    # Step 2: Choose someone in the video
    selector = PersonSelector(model_path=args.model)
    selected_bbox = None
    start_frame = args.skip_frames

    if args.select_bbox:
        try:
            parts = [int(v.strip()) for v in args.select_bbox.split(",")]
            if len(parts) == 4:
                selected_bbox = tuple(parts)
                print(f"[✓] Using manually specified bounding box: {selected_bbox}")
        except Exception as e:
            print(f"[!] Warning: invalid --select-bbox format ({e}). Expected 'x,y,w,h'.")

    if selected_bbox is None:
        if args.select_person is not None:
            # 1-based index to 0-based
            p_idx = max(0, args.select_person - 1)
            selected_bbox, start_frame = selector.auto_select_person(
                video_path, person_index=p_idx
            )
            print(f"[✓] Automatically selected Person {p_idx + 1}: {selected_bbox}")
        elif args.no_gui:
            # Auto-select primary person without GUI
            selected_bbox, start_frame = selector.auto_select_person(
                video_path, person_index=0
            )
            print(f"[✓] Headless mode: Auto-selected primary person: {selected_bbox}")
        else:
            # Interactive GUI selection
            try:
                selected_bbox, start_frame = selector.select_person_interactive(
                    video_path
                )
            except KeyboardInterrupt:
                print("\n[!] Analysis cancelled by user during person selection.")
                sys.exit(0)

    print(f"[✓] Target person acquired: Bounding Box = {selected_bbox} at frame {start_frame}")

    # Step 3: Initialize Video Reader, Tracker, Kinematics, and Visualizer
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    ret, init_frame = cap.read()
    if not ret:
        print("ERROR: Failed to read frame for tracking initialization.")
        sys.exit(1)

    # Initialize tracker with target bounding box
    tracker = PersonPoseTracker(model_path=args.model)
    tracker.init_tracker(init_frame, selected_bbox)

    kinematic_tracker = KinematicTracker()
    visualizer = PoseVisualizer(show_hud=True, show_joint_labels=True)

    # Setup video writer if output video requested
    video_writer = None
    save_video = args.output_video and args.output_video.lower() not in ["none", ""]
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(
            args.output_video, fourcc, fps, (width, height)
        )
        print(f"[✓] Recording annotated video to: {args.output_video}")

    window_name = "FormCheck: Real-Time Joint Kinematics"
    if not args.no_gui:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("\nProcessing video frames...")
    curr_frame_idx = start_frame
    start_time = time.perf_counter()
    processed_count = 0
    paused = False

    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp_s = curr_frame_idx / fps if fps > 0 else 0.0

                # Track chosen person & run pose estimation on target
                det_result = tracker.process_frame(frame, curr_frame_idx, timestamp_s)

                # Compute joint angles for this frame
                current_angles = kinematic_tracker.process_frame(
                    curr_frame_idx,
                    timestamp_s,
                    det_result.world_landmarks,
                    det_result.image_landmarks,
                )

                # Render skeleton, annotations, and HUD
                annotated_frame = visualizer.render(
                    frame,
                    det_result,
                    current_angles,
                    kinematic_tracker,
                    curr_frame_idx,
                    total_frames,
                    fps,
                )

                if video_writer is not None:
                    video_writer.write(annotated_frame)

                curr_frame_idx += 1
                processed_count += 1

                # Progress log in console
                if processed_count % 25 == 0 or curr_frame_idx == total_frames:
                    elapsed = time.perf_counter() - start_time
                    cur_fps = processed_count / elapsed if elapsed > 0 else 0
                    pct = (curr_frame_idx / total_frames) * 100
                    sys.stdout.write(
                        f"\r  Frame {curr_frame_idx}/{total_frames} ({pct:5.1f}%) | Speed: {cur_fps:5.1f} FPS"
                    )
                    sys.stdout.flush()

            # GUI display
            if not args.no_gui:
                cv2.imshow(window_name, annotated_frame)
                key = cv2.waitKey(1 if not paused else 50) & 0xFF
                if key in [ord("q"), ord("Q"), 27]:
                    print("\n[!] User interrupted playback.")
                    break
                elif key == ord(" "):  # Space to pause / resume
                    paused = not paused

    finally:
        cap.release()
        if video_writer is not None:
            video_writer.release()
        tracker.close()
        if not args.no_gui:
            cv2.destroyAllWindows()

    print(f"\n\n[✓] Completed analysis on {processed_count} frames.")

    # Step 4: Generate reports and statistics
    metadata = {
        "video_path": video_path,
        "total_frames": total_frames,
        "analyzed_frames": processed_count,
        "fps": fps,
        "resolution": f"{width}x{height}",
        "duration_s": duration_s,
        "initial_target_bbox": selected_bbox,
    }

    reporter = KinematicReporter(kinematic_tracker, metadata)

    # 1. Print formatted table in console
    reporter.print_terminal_summary()

    # 2. Save JSON report
    if args.output_json and args.output_json.lower() != "none":
        reporter.save_json(args.output_json)

    # 3. Save CSV time series
    if args.output_csv and args.output_csv.lower() != "none":
        reporter.save_csv(args.output_csv)

    # 4. Save Kinematics Plot
    if args.output_plot and args.output_plot.lower() != "none":
        reporter.save_kinematics_plot(args.output_plot)

    print("\nAll tasks finished successfully!")


if __name__ == "__main__":
    main()
