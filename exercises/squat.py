"""Squat exercise form analyzer."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from exercises.base_exercise import BaseExercise, ExerciseMetrics
from pose.analyzer import (
    calculate_angle_2d,
    calculate_angle_to_vertical,
    get_landmark_coords,
)
from pose.landmarks import PoseLandmark


class SquatExercise(BaseExercise):
    """Real-time biomechanical analysis for bodyweight and barbell squats."""

    def __init__(self) -> None:
        super().__init__(
            name="Squat",
            description="Analyzes knee depth, hip flexion, and torso posture during squats.",
        )
        self._state = "UP"  # "UP", "DESCENDING", "BOTTOM", "ASCENDING"
        self._min_knee_angle_in_rep = 180.0
        self._rep_had_chest_collapse = False
        self._rep_reached_depth = False

    def reset(self) -> None:
        super().reset()
        self._state = "UP"
        self._min_knee_angle_in_rep = 180.0
        self._rep_had_chest_collapse = False
        self._rep_reached_depth = False

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
                feedback=["Step back into full camera view."],
            )

        h, w = frame_shape[:2]

        # Extract both left and right sides to determine best visibility
        left_hip = get_landmark_coords(landmarks, PoseLandmark.LEFT_HIP, w, h)
        left_knee = get_landmark_coords(landmarks, PoseLandmark.LEFT_KNEE, w, h)
        left_ankle = get_landmark_coords(landmarks, PoseLandmark.LEFT_ANKLE, w, h)
        left_shoulder = get_landmark_coords(landmarks, PoseLandmark.LEFT_SHOULDER, w, h)

        right_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)
        right_knee = get_landmark_coords(landmarks, PoseLandmark.RIGHT_KNEE, w, h)
        right_ankle = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ANKLE, w, h)
        right_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)

        # Select the side with higher presence
        left_vis = landmarks[PoseLandmark.LEFT_KNEE].visibility if hasattr(landmarks[PoseLandmark.LEFT_KNEE], "visibility") else 1.0
        right_vis = landmarks[PoseLandmark.RIGHT_KNEE].visibility if hasattr(landmarks[PoseLandmark.RIGHT_KNEE], "visibility") else 1.0

        if left_vis >= right_vis:
            hip, knee, ankle, shoulder = left_hip, left_knee, left_ankle, left_shoulder
            hip_idx, knee_idx, shoulder_idx = (
                PoseLandmark.LEFT_HIP,
                PoseLandmark.LEFT_KNEE,
                PoseLandmark.LEFT_SHOULDER,
            )
        else:
            hip, knee, ankle, shoulder = right_hip, right_knee, right_ankle, right_shoulder
            hip_idx, knee_idx, shoulder_idx = (
                PoseLandmark.RIGHT_HIP,
                PoseLandmark.RIGHT_KNEE,
                PoseLandmark.RIGHT_SHOULDER,
            )

        if not (hip and knee and ankle and shoulder):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Ensure hips, knees, and ankles are visible."],
            )

        # Calculate joint angles
        knee_angle = calculate_angle_2d(hip, knee, ankle)
        hip_angle = calculate_angle_2d(shoulder, hip, knee)
        torso_angle = calculate_angle_to_vertical(shoulder, hip)

        joint_angles = {
            "Knee Angle": round(knee_angle, 1),
            "Hip Angle": round(hip_angle, 1),
            "Torso Lean": round(torso_angle, 1),
        }

        feedback: List[str] = []
        highlights: Dict[int, Tuple[int, int, int]] = {}
        score_deductions = 0.0

        # Posture checks
        # 1. Torso collapse check (> 42 degrees forward lean)
        if torso_angle > 42.0:
            feedback.append("Keep chest proud & upright")
            highlights[shoulder_idx] = (0, 0, 255)  # Red
            highlights[hip_idx] = (0, 0, 255)
            score_deductions += 20.0
            self._rep_had_chest_collapse = True
        else:
            highlights[shoulder_idx] = (0, 255, 0)

        # 2. State Machine & Repetition Counting
        # Thresholds:
        # Standing: knee_angle > 155
        # Parallel Depth: knee_angle <= 95
        if self._state == "UP":
            if knee_angle < 150.0:
                self._state = "DESCENDING"
                self._min_knee_angle_in_rep = knee_angle
                self._rep_had_chest_collapse = False
                self._rep_reached_depth = False
            else:
                feedback.append("Begin squat descent")

        elif self._state == "DESCENDING":
            self._min_knee_angle_in_rep = min(self._min_knee_angle_in_rep, knee_angle)
            if knee_angle <= 95.0:
                self._state = "BOTTOM"
                self._rep_reached_depth = True
                feedback.append("Great depth! Drive up through heels")
                highlights[knee_idx] = (0, 255, 0)
            elif knee_angle > 155.0:
                # Returned before bottom
                self._state = "UP"
            else:
                feedback.append("Squat deeper - aim for thighs parallel")
                highlights[knee_idx] = (0, 165, 255)  # Orange

        elif self._state == "BOTTOM":
            self._min_knee_angle_in_rep = min(self._min_knee_angle_in_rep, knee_angle)
            if knee_angle > 105.0:
                self._state = "ASCENDING"
            else:
                feedback.append("Drive up aggressively")
                highlights[knee_idx] = (0, 255, 0)

        elif self._state == "ASCENDING":
            if knee_angle > 155.0:
                # Completed rep!
                self._rep_count += 1
                self._state = "UP"

                if self._rep_reached_depth and not self._rep_had_chest_collapse:
                    self._good_reps += 1
                    feedback.append("Rep completed! Perfect form.")
                else:
                    self._bad_reps += 1
                    reasons = []
                    if not self._rep_reached_depth:
                        reasons.append("shallow depth")
                    if self._rep_had_chest_collapse:
                        reasons.append("chest collapse")
                    feedback.append(f"Rep completed with flaws ({', '.join(reasons)})")

                # Reset rep tracker flags
                self._min_knee_angle_in_rep = 180.0
            else:
                feedback.append("Push through to full lockout")

        # Live score calculation
        if knee_angle <= 95.0:
            depth_score = 100.0
        elif knee_angle < 120.0:
            depth_score = 80.0
        elif knee_angle < 145.0:
            depth_score = 65.0
        else:
            depth_score = 90.0

        current_instant_score = max(0.0, depth_score - score_deductions)
        # Smooth score with exponential moving average
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
