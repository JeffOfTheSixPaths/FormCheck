"""Push-up exercise form analyzer."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from exercises.base_exercise import BaseExercise, ExerciseMetrics
from pose.analyzer import calculate_angle_2d, get_landmark_coords
from pose.landmarks import PoseLandmark


class PushUpExercise(BaseExercise):
    """Real-time biomechanical analysis for push-ups."""

    def __init__(self) -> None:
        super().__init__(
            name="Push-up",
            description="Analyzes chest depth, elbow flexion, and body plank alignment.",
        )
        self._state = "TOP"  # "TOP", "DESCENDING", "BOTTOM", "ASCENDING"
        self._min_elbow_angle = 180.0
        self._body_sagged = False
        self._reached_depth = False

    def reset(self) -> None:
        super().reset()
        self._state = "TOP"
        self._min_elbow_angle = 180.0
        self._body_sagged = False
        self._reached_depth = False

    def get_feedback(self) -> List[str]:
        return list(self._feedback)

    def get_score(self) -> float:
        return round(self._current_score, 1)

    def analyze(self, landmarks: Any, frame_shape: Tuple[int, ...]) -> ExerciseMetrics:
        if landmarks is None or len(landmarks) < 33:
            return ExerciseMetrics(
                phase="No Pose Detected",
                score=self._current_score,
                rep_count=self._rep_count,
                good_reps=self._good_reps,
                bad_reps=self._bad_reps,
                feedback=["Step back into full side-view camera frame."],
            )

        h, w = frame_shape[:2]

        left_elbow = get_landmark_coords(landmarks, PoseLandmark.LEFT_ELBOW, w, h)
        left_shoulder = get_landmark_coords(landmarks, PoseLandmark.LEFT_SHOULDER, w, h)
        left_wrist = get_landmark_coords(landmarks, PoseLandmark.LEFT_WRIST, w, h)
        left_hip = get_landmark_coords(landmarks, PoseLandmark.LEFT_HIP, w, h)
        left_ankle = get_landmark_coords(landmarks, PoseLandmark.LEFT_ANKLE, w, h)

        right_elbow = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ELBOW, w, h)
        right_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        right_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)
        right_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)
        right_ankle = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ANKLE, w, h)

        left_vis = landmarks[PoseLandmark.LEFT_ELBOW].visibility if hasattr(landmarks[PoseLandmark.LEFT_ELBOW], "visibility") else 1.0
        right_vis = landmarks[PoseLandmark.RIGHT_ELBOW].visibility if hasattr(landmarks[PoseLandmark.RIGHT_ELBOW], "visibility") else 1.0

        if left_vis >= right_vis:
            shoulder, elbow, wrist = left_shoulder, left_elbow, left_wrist
            hip, ankle = left_hip, left_ankle
            elbow_idx, hip_idx = PoseLandmark.LEFT_ELBOW, PoseLandmark.LEFT_HIP
        else:
            shoulder, elbow, wrist = right_shoulder, right_elbow, right_wrist
            hip, ankle = right_hip, right_ankle
            elbow_idx, hip_idx = PoseLandmark.RIGHT_ELBOW, PoseLandmark.RIGHT_HIP

        if not (shoulder and elbow and wrist and hip and ankle):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Ensure upper body, hips, and feet are visible."],
            )

        # Joint angle calculations
        elbow_angle = calculate_angle_2d(shoulder, elbow, wrist)
        body_angle = calculate_angle_2d(shoulder, hip, ankle)

        joint_angles = {
            "Elbow Angle": round(elbow_angle, 1),
            "Body Line": round(body_angle, 1),
        }

        feedback: List[str] = []
        highlights: Dict[int, Tuple[int, int, int]] = {}
        score_deductions = 0.0

        # Body alignment check: Should be ~160 to 180 degrees
        if body_angle < 150.0:
            feedback.append("Keep core engaged; don't sag hips")
            highlights[hip_idx] = (0, 0, 255)  # Red
            score_deductions += 25.0
            self._body_sagged = True
        else:
            highlights[hip_idx] = (0, 255, 0)

        # State machine
        # TOP plank: elbow_angle > 150
        # BOTTOM: elbow_angle <= 90
        if self._state == "TOP":
            if elbow_angle < 145.0:
                self._state = "DESCENDING"
                self._min_elbow_angle = elbow_angle
                self._body_sagged = False
                self._reached_depth = False
            else:
                feedback.append("Ready - lower your chest to begin")

        elif self._state == "DESCENDING":
            self._min_elbow_angle = min(self._min_elbow_angle, elbow_angle)
            if elbow_angle <= 90.0:
                self._state = "BOTTOM"
                self._reached_depth = True
                feedback.append("Good depth! Press back up")
                highlights[elbow_idx] = (0, 255, 0)
            elif elbow_angle > 150.0:
                self._state = "TOP"
            else:
                feedback.append("Lower down until elbows reach 90°")
                highlights[elbow_idx] = (0, 165, 255)

        elif self._state == "BOTTOM":
            self._min_elbow_angle = min(self._min_elbow_angle, elbow_angle)
            if elbow_angle > 100.0:
                self._state = "ASCENDING"
            else:
                feedback.append("Drive through palms")
                highlights[elbow_idx] = (0, 255, 0)

        elif self._state == "ASCENDING":
            if elbow_angle > 150.0:
                self._rep_count += 1
                self._state = "TOP"

                if self._reached_depth and not self._body_sagged:
                    self._good_reps += 1
                    feedback.append("Rep completed! Strong form.")
                else:
                    self._bad_reps += 1
                    reasons = []
                    if not self._reached_depth:
                        reasons.append("didn't reach 90° depth")
                    if self._body_sagged:
                        reasons.append("hip alignment loss")
                    feedback.append(f"Rep flaw detected: {', '.join(reasons)}")

                self._min_elbow_angle = 180.0
            else:
                feedback.append("Push through to full lockout")

        # Score calculation
        base_score = 95.0 if elbow_angle <= 95.0 else 80.0
        current_instant_score = max(0.0, base_score - score_deductions)
        self._current_score = 0.8 * self._current_score + 0.2 * current_instant_score
        self._current_phase = self._state
        self._feedback = feedback

        return ExerciseMetrics(
            phase=self._state,
            score=round(self._current_score, 1),
            rep_count=self._rep_count,
            good_reps=self._good_reps,
            bad_reps=self._bad_reps,
            feedback=feedback,
            joint_angles=joint_angles,
            joint_highlights=highlights,
        )
