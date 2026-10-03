"""Biomechanical form analyzers for Volleyball athletic movements.

Covers:
1. Volleyball: Hitting (Arm Swing)
2. Volleyball: Hitting (Approach)
3. Volleyball: Passing
4. Volleyball: Setting
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from exercises.base_exercise import BaseExercise, ExerciseMetrics
from pose.analyzer import (
    calculate_angle_2d,
    calculate_angle_to_vertical,
    calculate_distance_2d,
    get_landmark_coords,
)
from pose.landmarks import PoseLandmark


class VolleyballHittingArmSwingExercise(BaseExercise):
    """Analyzes attack arm swing mechanics: high elbow draw, full extension, and snap."""

    def __init__(self) -> None:
        super().__init__(
            name="Volleyball: Hitting (Arm Swing)",
            description="Analyzes attack arm swing mechanics: high elbow draw, arm extension at contact, and snap follow-through.",
        )
        self._state = "PREPARATION"  # "PREPARATION", "COCKING", "ACCELERATION", "FOLLOW_THROUGH"
        self._max_elbow_angle = 0.0
        self._peak_wrist_y = 1.0  # Normalized (smaller is higher)
        self._had_high_elbow = False
        self._had_full_extension = False

    def reset(self) -> None:
        super().reset()
        self._state = "PREPARATION"
        self._max_elbow_angle = 0.0
        self._peak_wrist_y = 1.0
        self._had_high_elbow = False
        self._had_full_extension = False

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

        # Extract arms and shoulders
        l_shoulder = get_landmark_coords(landmarks, PoseLandmark.LEFT_SHOULDER, w, h)
        l_elbow = get_landmark_coords(landmarks, PoseLandmark.LEFT_ELBOW, w, h)
        l_wrist = get_landmark_coords(landmarks, PoseLandmark.LEFT_WRIST, w, h)
        l_hip = get_landmark_coords(landmarks, PoseLandmark.LEFT_HIP, w, h)

        r_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        r_elbow = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ELBOW, w, h)
        r_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)
        r_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)

        if not (l_shoulder and l_elbow and l_wrist and r_shoulder and r_elbow and r_wrist):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Ensure upper body and arms are clearly visible."],
            )

        # Detect active hitting arm (highest wrist during motion)
        if (l_wrist[1] < r_wrist[1]):
            shoulder, elbow, wrist, hip = l_shoulder, l_elbow, l_wrist, l_hip
            active_side = "Left"
            elbow_idx, wrist_idx = PoseLandmark.LEFT_ELBOW, PoseLandmark.LEFT_WRIST
        else:
            shoulder, elbow, wrist, hip = r_shoulder, r_elbow, r_wrist, r_hip
            active_side = "Right"
            elbow_idx, wrist_idx = PoseLandmark.RIGHT_ELBOW, PoseLandmark.RIGHT_WRIST

        elbow_angle = calculate_angle_2d(shoulder, elbow, wrist)
        # Shoulder elevation relative to torso (hip-shoulder-elbow)
        shoulder_elev = calculate_angle_2d(hip, shoulder, elbow) if hip else 90.0
        torso_angle = calculate_angle_to_vertical(shoulder, hip) if hip else 0.0

        joint_angles = {
            "Elbow Angle": round(elbow_angle, 1),
            "Shoulder Elevation": round(shoulder_elev, 1),
            "Torso Lean": round(torso_angle, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        # Normalized wrist Y
        wrist_norm_y = wrist[1] / h
        shoulder_norm_y = shoulder[1] / h
        elbow_norm_y = elbow[1] / h

        # State machine
        if self._state == "PREPARATION":
            self._current_phase = "Preparation"
            self._feedback.append("Draw hitting elbow high and back behind shoulder.")
            # Trigger cocking if elbow flexes and shoulder elevates
            if shoulder_elev > 65.0 and elbow_angle < 125.0:
                self._state = "COCKING"
                self._max_elbow_angle = elbow_angle
                self._peak_wrist_y = wrist_norm_y

        elif self._state == "COCKING":
            self._current_phase = "Elbow Draw / Cocking"
            if shoulder_elev >= 75.0 or elbow_norm_y <= shoulder_norm_y + 0.05:
                self._had_high_elbow = True
                self._feedback.append("Good high elbow draw. Accelerate and reach high!")
            else:
                self._feedback.append("Keep hitting elbow at or above shoulder level.")

            if elbow_angle > self._max_elbow_angle:
                self._max_elbow_angle = elbow_angle

            if wrist_norm_y < self._peak_wrist_y:
                self._peak_wrist_y = wrist_norm_y

            # Transition to acceleration when elbow rapidly extends above head
            if elbow_angle > 140.0 and wrist_norm_y < shoulder_norm_y:
                self._state = "ACCELERATION"

        elif self._state == "ACCELERATION":
            self._current_phase = "Acceleration / Contact"
            if elbow_angle > 155.0 and wrist_norm_y < shoulder_norm_y:
                self._had_full_extension = True
                self._feedback.append("Full high contact reach achieved! Snap wrist forward.")
            else:
                self._feedback.append("Reach high at peak contact - don't drop elbow.")

            # Transition to follow through as wrist drops below shoulder
            if wrist_norm_y > shoulder_norm_y:
                self._state = "FOLLOW_THROUGH"

        elif self._state == "FOLLOW_THROUGH":
            self._current_phase = "Follow-Through"
            # Count repetition
            self._rep_count += 1
            if self._had_high_elbow and self._had_full_extension:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 2.0)
                self._feedback.append("Clean attack arm swing executed!")
                highlights[wrist_idx] = (172, 239, 134)  # Mint
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 8.0)
                if not self._had_high_elbow:
                    self._feedback.append("Form Break: Low elbow draw. Pull elbow up and back.")
                elif not self._had_full_extension:
                    self._feedback.append("Form Break: Short arm reach. Extend fully at contact.")
                highlights[elbow_idx] = (165, 165, 252)  # Coral

            # Reset swing cycle
            self._state = "PREPARATION"
            self._had_high_elbow = False
            self._had_full_extension = False
            self._max_elbow_angle = 0.0

        return ExerciseMetrics(
            phase=self._current_phase,
            score=self.get_score(),
            rep_count=self._rep_count,
            good_reps=self._good_reps,
            bad_reps=self._bad_reps,
            feedback=self.get_feedback(),
            joint_angles=joint_angles,
            joint_highlights=highlights,
        )


class VolleyballHittingApproachExercise(BaseExercise):
    """Tracks penultimate step knee drive, arm backswing, and vertical block-jump."""

    def __init__(self) -> None:
        super().__init__(
            name="Volleyball: Hitting (Approach)",
            description="Tracks penultimate step knee drive, arm backswing, and vertical block-jump transition.",
        )
        self._state = "APPROACH"  # "APPROACH", "PENULTIMATE_PLANT", "EXPLOSIVE_DRIVE", "LANDING"
        self._min_knee_angle = 180.0
        self._had_deep_plant = False
        self._had_arm_backswing = False

    def reset(self) -> None:
        super().reset()
        self._state = "APPROACH"
        self._min_knee_angle = 180.0
        self._had_deep_plant = False
        self._had_arm_backswing = False

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

        l_hip = get_landmark_coords(landmarks, PoseLandmark.LEFT_HIP, w, h)
        l_knee = get_landmark_coords(landmarks, PoseLandmark.LEFT_KNEE, w, h)
        l_ankle = get_landmark_coords(landmarks, PoseLandmark.LEFT_ANKLE, w, h)
        l_shoulder = get_landmark_coords(landmarks, PoseLandmark.LEFT_SHOULDER, w, h)
        l_wrist = get_landmark_coords(landmarks, PoseLandmark.LEFT_WRIST, w, h)

        r_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)
        r_knee = get_landmark_coords(landmarks, PoseLandmark.RIGHT_KNEE, w, h)
        r_ankle = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ANKLE, w, h)
        r_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        r_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)

        if not (l_hip and l_knee and l_ankle and r_hip and r_knee and r_ankle):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Keep lower body and knees visible for approach tracking."],
            )

        l_knee_angle = calculate_angle_2d(l_hip, l_knee, l_ankle)
        r_knee_angle = calculate_angle_2d(r_hip, r_knee, r_ankle)
        lead_knee_angle = min(l_knee_angle, r_knee_angle)

        hip = l_hip if l_knee_angle < r_knee_angle else r_hip
        shoulder = l_shoulder if l_knee_angle < r_knee_angle else r_shoulder
        wrist = l_wrist if l_knee_angle < r_knee_angle else r_wrist

        hip_hinge = calculate_angle_2d(shoulder, hip, l_knee) if shoulder else 120.0
        torso_angle = calculate_angle_to_vertical(shoulder, hip) if shoulder else 15.0

        joint_angles = {
            "Plant Knee Flexion": round(lead_knee_angle, 1),
            "Hip Hinge": round(hip_hinge, 1),
            "Torso Lean": round(torso_angle, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        if self._state == "APPROACH":
            self._current_phase = "Approach Rhythm"
            self._feedback.append("Build forward momentum into penultimate step.")
            # Trigger plant if knee bends significantly
            if lead_knee_angle < 135.0:
                self._state = "PENULTIMATE_PLANT"
                self._min_knee_angle = lead_knee_angle

        elif self._state == "PENULTIMATE_PLANT":
            self._current_phase = "Penultimate Step Plant"
            if lead_knee_angle < self._min_knee_angle:
                self._min_knee_angle = lead_knee_angle

            if self._min_knee_angle <= 125.0:
                self._had_deep_plant = True
                self._feedback.append("Excellent deep knee load. Explode straight up!")
            else:
                self._feedback.append("Sink hips deeper on penultimate step (90°-120°).")

            # Check arm backswing (wrists behind hips/shoulders)
            if wrist and shoulder and wrist[0] < hip[0]:
                self._had_arm_backswing = True

            # Trigger explosive jump drive when knees extend rapidly
            if lead_knee_angle > 150.0:
                self._state = "EXPLOSIVE_DRIVE"

        elif self._state == "EXPLOSIVE_DRIVE":
            self._current_phase = "Vertical Jump Drive"
            self._feedback.append("Explosive triple extension into vertical flight.")
            # Landing when knees flex again after jump
            if lead_knee_angle < 145.0:
                self._state = "LANDING"

        elif self._state == "LANDING":
            self._current_phase = "Landing Absorption"
            self._rep_count += 1
            if self._had_deep_plant:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 3.0)
                self._feedback.append("Strong approach and explosive plant jump!")
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 7.0)
                self._feedback.append("Form Break: Plant knee too upright. Bend knees to convert speed.")

            # Reset
            self._state = "APPROACH"
            self._min_knee_angle = 180.0
            self._had_deep_plant = False
            self._had_arm_backswing = False

        return ExerciseMetrics(
            phase=self._current_phase,
            score=self.get_score(),
            rep_count=self._rep_count,
            good_reps=self._good_reps,
            bad_reps=self._bad_reps,
            feedback=self.get_feedback(),
            joint_angles=joint_angles,
            joint_highlights=highlights,
        )


class VolleyballPassingExercise(BaseExercise):
    """Evaluates forearm platform lock (straight elbows), knee-driven lift, and torso forward tilt."""

    def __init__(self) -> None:
        super().__init__(
            name="Volleyball: Passing",
            description="Evaluates forearm platform lock (straight elbows), knee-driven lift, and torso forward tilt.",
        )
        self._state = "READY_BASE"  # "READY_BASE", "PLATFORM_LOCKED", "LEG_DRIVE", "FINISH"
        self._had_locked_elbows = True
        self._had_knee_drive = False
        self._min_knee_angle = 180.0

    def reset(self) -> None:
        super().reset()
        self._state = "READY_BASE"
        self._had_locked_elbows = True
        self._had_knee_drive = False
        self._min_knee_angle = 180.0

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

        l_shoulder = get_landmark_coords(landmarks, PoseLandmark.LEFT_SHOULDER, w, h)
        l_elbow = get_landmark_coords(landmarks, PoseLandmark.LEFT_ELBOW, w, h)
        l_wrist = get_landmark_coords(landmarks, PoseLandmark.LEFT_WRIST, w, h)
        l_hip = get_landmark_coords(landmarks, PoseLandmark.LEFT_HIP, w, h)
        l_knee = get_landmark_coords(landmarks, PoseLandmark.LEFT_KNEE, w, h)
        l_ankle = get_landmark_coords(landmarks, PoseLandmark.LEFT_ANKLE, w, h)

        r_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        r_elbow = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ELBOW, w, h)
        r_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)
        r_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)
        r_knee = get_landmark_coords(landmarks, PoseLandmark.RIGHT_KNEE, w, h)
        r_ankle = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ANKLE, w, h)

        if not (l_shoulder and l_elbow and l_wrist and r_shoulder and r_elbow and r_wrist and l_knee and r_knee):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Keep platform arms and knees visible."],
            )

        l_elbow_angle = calculate_angle_2d(l_shoulder, l_elbow, l_wrist)
        r_elbow_angle = calculate_angle_2d(r_shoulder, r_elbow, r_wrist)
        avg_elbow_angle = (l_elbow_angle + r_elbow_angle) / 2.0

        l_knee_angle = calculate_angle_2d(l_hip, l_knee, l_ankle) if l_ankle else 140.0
        r_knee_angle = calculate_angle_2d(r_hip, r_knee, r_ankle) if r_ankle else 140.0
        avg_knee_angle = (l_knee_angle + r_knee_angle) / 2.0

        torso_angle = calculate_angle_to_vertical(l_shoulder, l_hip) if l_hip else 20.0

        joint_angles = {
            "Platform Elbow Lock": round(avg_elbow_angle, 1),
            "Knee Base": round(avg_knee_angle, 1),
            "Torso Tilt": round(torso_angle, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        # Check elbow lock: in volleyball passing, elbows MUST stay straight (>= 160°)
        if avg_elbow_angle < 152.0:
            self._had_locked_elbows = False
            highlights[PoseLandmark.LEFT_ELBOW] = (165, 165, 252)
            highlights[PoseLandmark.RIGHT_ELBOW] = (165, 165, 252)

        # Distance between wrists: platform formed when wrists join close together
        wrist_dist = calculate_distance_2d(l_wrist, r_wrist) / w

        if self._state == "READY_BASE":
            self._current_phase = "Ready Stance"
            self._feedback.append("Low athletic base. Ready to join hands into platform.")
            if wrist_dist < 0.12 and avg_knee_angle < 140.0:
                self._state = "PLATFORM_LOCKED"
                self._min_knee_angle = avg_knee_angle
                self._had_locked_elbows = True

        elif self._state == "PLATFORM_LOCKED":
            self._current_phase = "Platform Formed"
            if avg_knee_angle < self._min_knee_angle:
                self._min_knee_angle = avg_knee_angle

            if avg_elbow_angle >= 160.0:
                self._feedback.append("Platform solid and locked. Push upward with legs.")
            else:
                self._feedback.append("Lock elbows straight! Do not bend arms.")

            # Leg extension pushing through ball
            if avg_knee_angle > self._min_knee_angle + 18.0:
                self._state = "LEG_DRIVE"
                self._had_knee_drive = True

        elif self._state == "LEG_DRIVE":
            self._current_phase = "Leg Drive & Pass Contact"
            self._feedback.append("Smooth leg drive through the ball.")
            # Reset after contact
            if wrist_dist > 0.18 or avg_knee_angle > 165.0:
                self._state = "FINISH"

        elif self._state == "FINISH":
            self._current_phase = "Pass Complete"
            self._rep_count += 1
            if self._had_locked_elbows and self._had_knee_drive:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 2.5)
                self._feedback.append("Clean pass: Straight platform with good leg drive!")
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 8.0)
                if not self._had_locked_elbows:
                    self._feedback.append("Form Break: Bent elbows. Lock arms completely straight.")
                else:
                    self._feedback.append("Form Break: Stiff knees. Pass with legs, not swinging arms.")

            self._state = "READY_BASE"
            self._had_locked_elbows = True
            self._had_knee_drive = False
            self._min_knee_angle = 180.0

        return ExerciseMetrics(
            phase=self._current_phase,
            score=self.get_score(),
            rep_count=self._rep_count,
            good_reps=self._good_reps,
            bad_reps=self._bad_reps,
            feedback=self.get_feedback(),
            joint_angles=joint_angles,
            joint_highlights=highlights,
        )


class VolleyballSettingExercise(BaseExercise):
    """Monitors overhead setting triangle window, synchronized elbow cushion, and target extension."""

    def __init__(self) -> None:
        super().__init__(
            name="Volleyball: Setting",
            description="Monitors overhead setting triangle window, synchronized elbow cushion, and target extension.",
        )
        self._state = "READY_BASE"  # "READY_BASE", "HANDS_UP_CUSHION", "EXTENSION", "FOLLOW_THROUGH"
        self._had_high_hands = False
        self._had_clean_extension = False
        self._min_elbow_angle = 180.0

    def reset(self) -> None:
        super().reset()
        self._state = "READY_BASE"
        self._had_high_hands = False
        self._had_clean_extension = False
        self._min_elbow_angle = 180.0

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

        nose = get_landmark_coords(landmarks, PoseLandmark.NOSE, w, h)
        l_shoulder = get_landmark_coords(landmarks, PoseLandmark.LEFT_SHOULDER, w, h)
        l_elbow = get_landmark_coords(landmarks, PoseLandmark.LEFT_ELBOW, w, h)
        l_wrist = get_landmark_coords(landmarks, PoseLandmark.LEFT_WRIST, w, h)

        r_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        r_elbow = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ELBOW, w, h)
        r_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)

        if not (l_shoulder and l_elbow and l_wrist and r_shoulder and r_elbow and r_wrist and nose):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Keep head, shoulders, and hands visible for setting analysis."],
            )

        l_elbow_angle = calculate_angle_2d(l_shoulder, l_elbow, l_wrist)
        r_elbow_angle = calculate_angle_2d(r_shoulder, r_elbow, r_wrist)
        avg_elbow_angle = (l_elbow_angle + r_elbow_angle) / 2.0

        avg_wrist_y = (l_wrist[1] + r_wrist[1]) / 2.0
        avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2.0
        nose_y = nose[1]

        joint_angles = {
            "Elbow Cushion Angle": round(avg_elbow_angle, 1),
            "Left Elbow": round(l_elbow_angle, 1),
            "Right Elbow": round(r_elbow_angle, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        # Setting position: hands are raised above nose/forehead
        hands_above_forehead = avg_wrist_y < nose_y

        if self._state == "READY_BASE":
            self._current_phase = "Ready / Tracking"
            self._feedback.append("Bring hands up early into triangle window above forehead.")
            if hands_above_forehead and avg_elbow_angle < 125.0:
                self._state = "HANDS_UP_CUSHION"
                self._min_elbow_angle = avg_elbow_angle
                self._had_high_hands = True

        elif self._state == "HANDS_UP_CUSHION":
            self._current_phase = "Soft Hands Cushion"
            if avg_elbow_angle < self._min_elbow_angle:
                self._min_elbow_angle = avg_elbow_angle

            if avg_wrist_y < nose_y - 20:
                self._feedback.append("Good hand height above forehead. Cushion and extend!")
            else:
                self._feedback.append("Hands too low: Shape setting window above forehead.")

            # Extend through set
            if avg_elbow_angle > 145.0:
                self._state = "EXTENSION"

        elif self._state == "EXTENSION":
            self._current_phase = "Release & Extension"
            if avg_elbow_angle > 158.0:
                self._had_clean_extension = True
                self._feedback.append("Full symmetrical extension through the ball.")

            # Return hands down or reset
            if avg_elbow_angle > 165.0 or avg_wrist_y > nose_y:
                self._state = "FOLLOW_THROUGH"

        elif self._state == "FOLLOW_THROUGH":
            self._current_phase = "Follow-Through"
            self._rep_count += 1
            if self._had_high_hands and self._had_clean_extension:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 2.5)
                self._feedback.append("Clean set: High contact point with smooth extension!")
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 7.0)
                if not self._had_high_hands:
                    self._feedback.append("Form Break: Set contact too low. Contact 6 inches above forehead.")
                else:
                    self._feedback.append("Form Break: Incomplete arm extension on release.")

            self._state = "READY_BASE"
            self._had_high_hands = False
            self._had_clean_extension = False
            self._min_elbow_angle = 180.0

        return ExerciseMetrics(
            phase=self._current_phase,
            score=self.get_score(),
            rep_count=self._rep_count,
            good_reps=self._good_reps,
            bad_reps=self._bad_reps,
            feedback=self.get_feedback(),
            joint_angles=joint_angles,
            joint_highlights=highlights,
        )
