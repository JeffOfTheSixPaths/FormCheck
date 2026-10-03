import cv2
import mediapipe as mp
import time

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


MODEL_PATH = "pose_landmarker.task"


# MediaPipe's 33 pose landmarks.
# Each tuple connects two landmark indexes.
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),

    (9, 10),

    (11, 12),

    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21),

    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22),

    (11, 23),
    (12, 24),

    (23, 24),

    (23, 25), (25, 27),
    (27, 29), (29, 31),

    (24, 26), (26, 28),
    (28, 30), (30, 32),
]


def draw_pose(frame, landmarks):
    height, width = frame.shape[:2]

    # Draw connections
    for start_idx, end_idx in POSE_CONNECTIONS:
        start = landmarks[start_idx]
        end = landmarks[end_idx]

        x1 = int(start.x * width)
        y1 = int(start.y * height)

        x2 = int(end.x * width)
        y2 = int(end.y * height)

        cv2.line(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 0, 0),
            2,
        )

    # Draw landmarks
    for landmark in landmarks:
        x = int(landmark.x * width)
        y = int(landmark.y * height)

        # Ignore points that are wildly outside the image.
        if 0 <= x < width and 0 <= y < height:
            cv2.circle(
                frame,
                (x, y),
                5,
                (0, 255, 0),
                -1,
            )


def main():
    print("Loading pose model...")

    base_options = python.BaseOptions(
        model_asset_path=MODEL_PATH
    )

    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    print("Opening camera...")

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Could not open camera.")
        return

    # Optional camera resolution
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    start_time = time.perf_counter()
    frame_count = 0

    print("Camera started.")
    print("Press Q to quit.")

    with vision.PoseLandmarker.create_from_options(options) as landmarker:

        while True:
            success, frame = camera.read()

            if not success:
                print("ERROR: Could not read frame.")
                break

            # BGR -> RGB
            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            # Timestamp in milliseconds.
            timestamp_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            result = landmarker.detect_for_video(
                mp_image,
                timestamp_ms,
            )

            # Draw poses
            if result.pose_landmarks:

                for landmarks in result.pose_landmarks:
                    draw_pose(frame, landmarks)

            # FPS
            frame_count += 1
            elapsed = time.perf_counter() - start_time

            fps = frame_count / elapsed if elapsed > 0 else 0

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            cv2.putText(
                frame,
                "Q = quit",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.imshow(
                "MediaPipe Pose",
                frame,
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
