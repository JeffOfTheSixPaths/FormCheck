"""
Person selection module: Allows interactive or automatic selection of a specific
person in the video before running pose estimation and tracking.
"""

from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np


class PersonSelector:
    """
    Handles person detection and interactive ROI / ID selection in video frames.
    """

    def __init__(
        self,
        model_path: str = "pose_landmarker.task",
        min_detection_confidence: float = 0.5,
    ):
        self.model_path = model_path
        self.min_detection_confidence = min_detection_confidence

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        self.options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=6,
            min_pose_detection_confidence=min_detection_confidence,
        )

    def detect_people_in_frame(
        self, frame: np.ndarray
    ) -> List[Tuple[Tuple[int, int, int, int], List]]:
        """
        Detects all people in the frame.
        Returns a list of tuples: ((x, y, w, h), landmarks)
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        results = []
        with vision.PoseLandmarker.create_from_options(self.options) as landmarker:
            det = landmarker.detect(mp_image)
            if det.pose_landmarks:
                for lms in det.pose_landmarks:
                    xs = [lm.x * w for lm in lms if getattr(lm, "visibility", 1.0) > 0.25]
                    ys = [lm.y * h for lm in lms if getattr(lm, "visibility", 1.0) > 0.25]
                    if len(xs) >= 8:
                        x1 = max(0, int(min(xs) - 15))
                        y1 = max(0, int(min(ys) - 25))
                        x2 = min(w, int(max(xs) + 15))
                        y2 = min(h, int(max(ys) + 20))
                        bbox = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
                        results.append((bbox, lms))

        # Sort by area descending (largest person first)
        results.sort(key=lambda item: item[0][2] * item[0][3], reverse=True)
        return results

    def select_person_interactive(
        self,
        video_path: str,
        window_name: str = "Select Person - FormCheck",
    ) -> Tuple[Tuple[int, int, int, int], int]:
        """
        Opens an interactive window to scrub through video frames and select a person.
        Returns:
            selected_bbox: (x, y, w, h)
            start_frame_idx: the frame index where the person was selected
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video at {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        current_frame_idx = 0

        # State for mouse drag
        drag_state = {
            "drawing": False,
            "start_pt": None,
            "current_pt": None,
            "selected_roi": None,
            "clicked_person_idx": None,
        }

        detected_people: List[Tuple[Tuple[int, int, int, int], List]] = []

        def mouse_callback(event, x, y, flags, param):
            nonlocal drag_state
            if event == cv2.EVENT_LBUTTONDOWN:
                drag_state["drawing"] = True
                drag_state["start_pt"] = (x, y)
                drag_state["current_pt"] = (x, y)

                # Check if clicked inside any detected person's box
                for idx, (bbox, _) in enumerate(detected_people):
                    bx, by, bw, bh = bbox
                    if bx <= x <= bx + bw and by <= y <= by + bh:
                        drag_state["clicked_person_idx"] = idx
                        break

            elif event == cv2.EVENT_MOUSEMOVE:
                if drag_state["drawing"]:
                    drag_state["current_pt"] = (x, y)

            elif event == cv2.EVENT_LBUTTONUP:
                if drag_state["drawing"]:
                    drag_state["drawing"] = False
                    sx, sy = drag_state["start_pt"]
                    # If dragged enough distance, create ROI
                    if abs(x - sx) > 20 and abs(y - sy) > 20:
                        x1, x2 = min(sx, x), max(sx, x)
                        y1, y2 = min(sy, y), max(sy, y)
                        drag_state["selected_roi"] = (x1, y1, x2 - x1, y2 - y1)
                        drag_state["clicked_person_idx"] = None

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, mouse_callback)

        selected_bbox = None
        start_frame = 0

        print("\n" + "=" * 60)
        print("PERSON SELECTION INSTRUCTIONS:")
        print("  - Drag a box around the person you want to analyze with your mouse")
        print("  - OR press number key [1-9] to select a highlighted person")
        print("  - OR click directly on a highlighted person")
        print("  - Space/Enter: Confirm selection (defaults to Person 1)")
        print("  - 'D' or Right Arrow: Next frame | 'A' or Left Arrow: Prev frame")
        print("  - 'Q' or Esc: Cancel and exit")
        print("=" * 60 + "\n")

        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            detected_people = self.detect_people_in_frame(frame)

            # Display loop for the current frame
            while True:
                display = frame.copy()

                # Draw detected people
                colors = [
                    (0, 255, 0),
                    (255, 200, 0),
                    (0, 200, 255),
                    (255, 100, 255),
                    (100, 255, 255),
                ]
                for idx, (bbox, _) in enumerate(detected_people):
                    color = colors[idx % len(colors)]
                    bx, by, bw, bh = bbox
                    cv2.rectangle(display, (bx, by), (bx + bw, by + bh), color, 2)
                    label = f"[{idx + 1}] Person {idx + 1}"
                    # Label background
                    (tw, th), _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
                    )
                    cv2.rectangle(
                        display, (bx, max(0, by - 25)), (bx + tw + 10, by), color, -1
                    )
                    cv2.putText(
                        display,
                        label,
                        (bx + 5, by - 7),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 0),
                        2,
                    )

                # Draw custom drag box if user is dragging or has selected
                if (
                    drag_state["drawing"]
                    and drag_state["start_pt"]
                    and drag_state["current_pt"]
                ):
                    sx, sy = drag_state["start_pt"]
                    cx, cy = drag_state["current_pt"]
                    cv2.rectangle(
                        display, (sx, sy), (cx, cy), (0, 0, 255), 2
                    )
                    cv2.putText(
                        display,
                        "Release to set ROI",
                        (min(sx, cx), min(sy, cy) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2,
                    )
                elif drag_state["selected_roi"]:
                    rx, ry, rw, rh = drag_state["selected_roi"]
                    cv2.rectangle(
                        display, (rx, ry), (rx + rw, ry + rh), (0, 0, 255), 3
                    )
                    cv2.putText(
                        display,
                        "Selected Custom ROI (Press Enter to confirm)",
                        (rx, max(20, ry - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2,
                    )
                elif drag_state["clicked_person_idx"] is not None:
                    cidx = drag_state["clicked_person_idx"]
                    if cidx < len(detected_people):
                        bx, by, bw, bh = detected_people[cidx][0]
                        cv2.rectangle(
                            display, (bx, by), (bx + bw, by + bh), (0, 255, 255), 3
                        )
                        cv2.putText(
                            display,
                            f"Selected Person {cidx + 1} (Press Enter to confirm)",
                            (bx, max(20, by - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 255),
                            2,
                        )

                # Instruction overlay header
                header = (
                    f"Frame {current_frame_idx + 1}/{total_frames} | "
                    f"Press [1-{max(1, len(detected_people))}] or Click to select | "
                    f"Drag mouse for ROI | Space/Enter to confirm"
                )
                cv2.rectangle(display, (0, 0), (w, 38), (20, 20, 20), -1)
                cv2.putText(
                    display,
                    header,
                    (15, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )

                cv2.imshow(window_name, display)
                key = cv2.waitKey(20) & 0xFF

                # Exit / cancel
                if key in [ord("q"), ord("Q"), 27]:
                    cap.release()
                    cv2.destroyWindow(window_name)
                    raise KeyboardInterrupt("Person selection cancelled by user.")

                # Frame navigation
                if key in [ord("d"), ord("D"), 83]:  # Next frame
                    current_frame_idx = min(total_frames - 1, current_frame_idx + 1)
                    break
                elif key in [ord("a"), ord("A"), 81]:  # Prev frame
                    current_frame_idx = max(0, current_frame_idx - 1)
                    break

                # Number selection [1-9]
                if ord("1") <= key <= ord("9"):
                    selected_num = key - ord("1")
                    if selected_num < len(detected_people):
                        selected_bbox = detected_people[selected_num][0]
                        start_frame = current_frame_idx
                        print(f"Selected Person {selected_num + 1} at frame {start_frame}")
                        break

                # Confirm selection
                if key in [13, 32]:  # Enter or Space
                    if drag_state["selected_roi"]:
                        selected_bbox = drag_state["selected_roi"]
                        start_frame = current_frame_idx
                        print(f"Confirmed custom ROI selection at frame {start_frame}: {selected_bbox}")
                        break
                    elif drag_state["clicked_person_idx"] is not None:
                        cidx = drag_state["clicked_person_idx"]
                        selected_bbox = detected_people[cidx][0]
                        start_frame = current_frame_idx
                        print(f"Confirmed clicked Person {cidx + 1} at frame {start_frame}")
                        break
                    elif detected_people:
                        selected_bbox = detected_people[0][0]
                        start_frame = current_frame_idx
                        print(f"Confirmed default Person 1 at frame {start_frame}")
                        break
                    else:
                        # Full frame fallback
                        selected_bbox = (0, 0, w, h)
                        start_frame = current_frame_idx
                        print(f"Confirmed full frame selection at frame {start_frame}")
                        break

            if selected_bbox is not None:
                break

        cap.release()
        cv2.destroyWindow(window_name)

        if selected_bbox is None:
            # Default to full frame if nothing chosen
            selected_bbox = (0, 0, w, h)
            start_frame = 0

        return selected_bbox, start_frame

    def auto_select_person(
        self, video_path: str, person_index: int = 0
    ) -> Tuple[Tuple[int, int, int, int], int]:
        """
        Automatically selects the person by index (0 for primary/largest)
        without opening a GUI window.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video at {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_idx = 0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Check first 30 frames for a valid person detection
        selected_bbox = None
        while frame_idx < min(30, total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            people = self.detect_people_in_frame(frame)
            if people:
                idx = min(person_index, len(people) - 1)
                selected_bbox = people[idx][0]
                cap.release()
                return selected_bbox, frame_idx
            frame_idx += 1

        cap.release()
        # Fallback to full frame
        return (0, 0, w, h), 0
