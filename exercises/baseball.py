"""Biomechanical form analyzers for Baseball athletic movements.

Covers:
1. Baseball: Hitting
2. Baseball: Pitching
3. Baseball: Fielding
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


class BaseballHittingExercise(BaseExercise):
    """Analyzes batting swing mechanics: stance load, hip rotation, lead elbow path, and follow-through."""

    def __init__(self) -> None:
        super().__init__(
            name="Baseball: Hitting",
            description="Analyzes batting swing mechanics: stance load, hip rotation, lead elbow path, and follow-through.",
        )
        self._state = "STANCE"  # "STANCE", "LOAD_STRIDE", "ROTATION_CONTACT", "FOLLOW_THROUGH"
        self._had_hip_load = False
        self._had_slot_elbow = False
        self._had_balanced_finish = True

    def reset(self) -> None:
        super().reset()
        self._state = "STANCE"
        self._had_hip_load = False
        self._had_slot_elbow = False
        self._had_balanced_finish = True

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

        r_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        r_elbow = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ELBOW, w, h)
        r_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)
        r_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)
        r_knee = get_landmark_coords(landmarks, PoseLandmark.RIGHT_KNEE, w, h)

        if not (l_shoulder and r_shoulder and l_elbow and r_elbow and l_hip and r_hip):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Ensure batting stance, shoulders, and hips are visible."],
            )

        # Calculate elbow angles
        l_elbow_angle = calculate_angle_2d(l_shoulder, l_elbow, l_wrist) if l_wrist else 90.0
        r_elbow_angle = calculate_angle_2d(r_shoulder, r_elbow, r_wrist) if r_wrist else 90.0

        # Back elbow vs lead elbow: typically the back elbow is flexed (80°-110°) during swing initiation
        back_elbow_angle = min(l_elbow_angle, r_elbow_angle)
        lead_elbow_angle = max(l_elbow_angle, r_elbow_angle)

        # Hip line angle and shoulder line angle relative to horizontal
        shoulder_dx = r_shoulder[0] - l_shoulder[0]
        shoulder_dy = r_shoulder[1] - l_shoulder[1]
        shoulder_rot = np.degrees(np.arctan2(shoulder_dy, shoulder_dx))

        hip_dx = r_hip[0] - l_hip[0]
        hip_dy = r_hip[1] - l_hip[1]
        hip_rot = np.degrees(np.arctan2(hip_dy, hip_dx))

        separation = abs(shoulder_rot - hip_rot)
        torso_tilt = calculate_angle_to_vertical(l_shoulder, l_hip)

        joint_angles = {
            "Back Elbow Slot": round(back_elbow_angle, 1),
            "Lead Elbow Path": round(lead_elbow_angle, 1),
            "Hip-Shoulder Separation": round(separation, 1),
            "Torso Spine Angle": round(torso_tilt, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        # Distance between hands/wrists
        wrist_dist = calculate_distance_2d(l_wrist, r_wrist) if (l_wrist and r_wrist) else 50.0

        if self._state == "STANCE":
            self._current_phase = "Stance & Athletic Setup"
            self._feedback.append("Athletic balanced stance. Stay relaxed and load weight onto back hip.")
            # Trigger load when hands move back and knees flex
            if back_elbow_angle < 100.0 and separation > 5.0:
                self._state = "LOAD_STRIDE"
                self._had_hip_load = True

        elif self._state == "LOAD_STRIDE":
            self._current_phase = "Load & Stride Separation"
            if back_elbow_angle <= 110.0:
                self._had_slot_elbow = True
                self._feedback.append("Hands stay back, creating good rotational coil.")
            else:
                self._feedback.append("Don't drop hands early: Keep barrel loaded upright.")

            # Swing rotation initiation
            if lead_elbow_angle > 135.0:
                self._state = "ROTATION_CONTACT"

        elif self._state == "ROTATION_CONTACT":
            self._current_phase = "Hip Rotation & Contact Zone"
            self._feedback.append("Drive hips through and extend through the hitting zone!")
            # Finish swing
            if lead_elbow_angle > 150.0 or abs(shoulder_rot) > 25.0:
                self._state = "FOLLOW_THROUGH"

        elif self._state == "FOLLOW_THROUGH":
            self._current_phase = "Follow-Through & Balanced Finish"
            self._rep_count += 1
            if self._had_hip_load and self._had_slot_elbow:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 3.0)
                self._feedback.append("Clean baseball swing: Powerful hip initiation and slotted barrel!")
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 7.0)
                if not self._had_slot_elbow:
                    self._feedback.append("Form Break: Casting bat barrel. Keep back elbow connected to ribs.")
                else:
                    self._feedback.append("Form Break: Lunging forward. Maintain balance over center.")

            self._state = "STANCE"
            self._had_hip_load = False
            self._had_slot_elbow = False

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


class BaseballPitchingExercise(BaseExercise):
    """Monitors delivery mechanics: leg lift balance, 90/90 arm cocking, lead leg block, and deceleration."""

    def __init__(self) -> None:
        super().__init__(
            name="Baseball: Pitching",
            description="Monitors delivery mechanics: leg lift balance, 90/90 arm cocking, lead leg block, and deceleration.",
        )
        self._state = "WINDUP"  # "WINDUP", "LEG_LIFT", "ARM_COCKING_STRIDE", "RELEASE", "DECELERATION"
        self._had_high_leg_lift = False
        self._had_safe_arm_cocking = False
        self._had_front_leg_block = False

    def reset(self) -> None:
        super().reset()
        self._state = "WINDUP"
        self._had_high_leg_lift = False
        self._had_safe_arm_cocking = False
        self._had_front_leg_block = False

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

        if not (l_shoulder and r_shoulder and l_knee and r_knee and l_hip and r_hip):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Ensure full body pitching delivery is visible."],
            )

        # Detect high knee (lead leg lift)
        l_knee_y = l_knee[1]
        r_knee_y = r_knee[1]
        hip_y = (l_hip[1] + r_hip[1]) / 2.0

        # Throwing arm detection (arm that elevates high)
        if (l_wrist and r_wrist and l_wrist[1] < r_wrist[1]):
            t_shoulder, t_elbow, t_wrist = l_shoulder, l_elbow, l_wrist
            t_side = "Left"
            elbow_idx = PoseLandmark.LEFT_ELBOW
        else:
            t_shoulder, t_elbow, t_wrist = r_shoulder, r_elbow, r_wrist
            t_side = "Right"
            elbow_idx = PoseLandmark.RIGHT_ELBOW

        t_elbow_angle = calculate_angle_2d(t_shoulder, t_elbow, t_wrist) if (t_shoulder and t_elbow and t_wrist) else 90.0
        # Arm cocking angle: shoulder to elbow relative to vertical or torso
        shoulder_elev = calculate_angle_to_vertical(t_elbow, t_shoulder) if (t_shoulder and t_elbow) else 80.0

        l_knee_angle = calculate_angle_2d(l_hip, l_knee, l_ankle) if l_ankle else 140.0
        r_knee_angle = calculate_angle_2d(r_hip, r_knee, r_ankle) if r_ankle else 140.0
        lead_knee_angle = min(l_knee_angle, r_knee_angle)

        joint_angles = {
            "Throwing Elbow 90/90": round(t_elbow_angle, 1),
            "Shoulder Elevation": round(shoulder_elev, 1),
            "Lead Knee Block": round(lead_knee_angle, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        if self._state == "WINDUP":
            self._current_phase = "Windup & Balance Point"
            self._feedback.append("Establish rhythm and initiate balance leg lift.")
            # Trigger leg lift
            if min(l_knee_y, r_knee_y) < hip_y + 40:
                self._state = "LEG_LIFT"
                self._had_high_leg_lift = True

        elif self._state == "LEG_LIFT":
            self._current_phase = "Peak Balance Point"
            self._feedback.append("Hold stable balance over rubber. Drive down the mound.")
            # Stride into arm cocking
            if t_elbow_angle > 70.0 and t_wrist and t_wrist[1] < t_shoulder[1]:
                self._state = "ARM_COCKING_STRIDE"

        elif self._state == "ARM_COCKING_STRIDE":
            self._current_phase = "Stride & Arm Cocking"
            # 90/90 check: elbow at shoulder height and flexed 80°-110°
            if 75.0 <= t_elbow_angle <= 115.0:
                self._had_safe_arm_cocking = True
                self._feedback.append("Excellent 90/90 arm cocking: UCL protection maintained.")
            else:
                self._feedback.append("Arm slot warning: Keep elbow at shoulder height in 90° angle.")

            # Acceleration toward release
            if t_elbow_angle > 140.0:
                self._state = "RELEASE"

        elif self._state == "RELEASE":
            self._current_phase = "Ball Release Point"
            self._feedback.append("Full chest extension over firm front knee block.")
            if lead_knee_angle > 135.0:
                self._had_front_leg_block = True

            # Deceleration
            if t_wrist and t_wrist[1] > t_shoulder[1] + 30:
                self._state = "DECELERATION"

        elif self._state == "DECELERATION":
            self._current_phase = "Deceleration & Finish"
            self._rep_count += 1
            if self._had_safe_arm_cocking and self._had_high_leg_lift:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 3.0)
                self._feedback.append("Clean pitching delivery: High balance with protected 90/90 arm slot!")
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 8.0)
                if not self._had_safe_arm_cocking:
                    self._feedback.append("Form Break: Low elbow at foot strike. Raise elbow to shoulder height.")
                else:
                    self._feedback.append("Form Break: Rushed balance point. Stabilize leg lift before driving.")

            self._state = "WINDUP"
            self._had_high_leg_lift = False
            self._had_safe_arm_cocking = False
            self._had_front_leg_block = False

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


class BaseballFieldingExercise(BaseExercise):
    """Evaluates infield ground ball posture: hip hinge depth, glove reach out front, and funnel transfer."""

    def __init__(self) -> None:
        super().__init__(
            name="Baseball: Fielding",
            description="Evaluates infield ground ball posture: hip hinge depth, glove reach out front, and funnel transfer.",
        )
        self._state = "READY_STANCE"  # "READY_STANCE", "BREAKDOWN_SINK", "GLOVE_OUT_FRONT", "TRANSFER"
        self._had_deep_hips = False
        self._had_glove_out_front = False
        self._min_hip_angle = 180.0

    def reset(self) -> None:
        super().reset()
        self._state = "READY_STANCE"
        self._had_deep_hips = False
        self._had_glove_out_front = False
        self._min_hip_angle = 180.0

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
        l_hip = get_landmark_coords(landmarks, PoseLandmark.LEFT_HIP, w, h)
        l_knee = get_landmark_coords(landmarks, PoseLandmark.LEFT_KNEE, w, h)
        l_ankle = get_landmark_coords(landmarks, PoseLandmark.LEFT_ANKLE, w, h)
        l_wrist = get_landmark_coords(landmarks, PoseLandmark.LEFT_WRIST, w, h)

        r_shoulder = get_landmark_coords(landmarks, PoseLandmark.RIGHT_SHOULDER, w, h)
        r_hip = get_landmark_coords(landmarks, PoseLandmark.RIGHT_HIP, w, h)
        r_knee = get_landmark_coords(landmarks, PoseLandmark.RIGHT_KNEE, w, h)
        r_ankle = get_landmark_coords(landmarks, PoseLandmark.RIGHT_ANKLE, w, h)
        r_wrist = get_landmark_coords(landmarks, PoseLandmark.RIGHT_WRIST, w, h)

        if not (l_hip and r_hip and l_knee and r_knee and l_ankle and r_ankle):
            return ExerciseMetrics(
                phase="Calibrating",
                score=self._current_score,
                rep_count=self._rep_count,
                feedback=["Keep lower body and glove hand visible for fielding posture."],
            )

        l_knee_angle = calculate_angle_2d(l_hip, l_knee, l_ankle)
        r_knee_angle = calculate_angle_2d(r_hip, r_knee, r_ankle)
        avg_knee_angle = (l_knee_angle + r_knee_angle) / 2.0

        hip = l_hip
        shoulder = l_shoulder if l_shoulder else r_shoulder
        hip_angle = calculate_angle_2d(shoulder, hip, l_knee) if shoulder else 120.0
        torso_tilt = calculate_angle_to_vertical(shoulder, hip) if shoulder else 30.0

        # Glove hand is lowest wrist toward ground
        lowest_wrist_y = max(l_wrist[1] if l_wrist else 0, r_wrist[1] if r_wrist else 0)
        knee_y = (l_knee[1] + r_knee[1]) / 2.0

        joint_angles = {
            "Hip Sink Depth": round(hip_angle, 1),
            "Knee Flexion": round(avg_knee_angle, 1),
            "Torso Spine Angle": round(torso_tilt, 1),
        }

        self._feedback.clear()
        highlights: Dict[int, Tuple[int, int, int]] = {}

        if self._state == "READY_STANCE":
            self._current_phase = "Ready Prep Step"
            self._feedback.append("Active prep step: feet wide, knees bent, ready for hop.")
            # Trigger breakdown sink when knees and hips bend low
            if avg_knee_angle < 135.0:
                self._state = "BREAKDOWN_SINK"
                self._min_hip_angle = hip_angle

        elif self._state == "BREAKDOWN_SINK":
            self._current_phase = "Breakdown & Hip Sink"
            if hip_angle < self._min_hip_angle:
                self._min_hip_angle = hip_angle

            if self._min_hip_angle <= 120.0 and avg_knee_angle <= 125.0:
                self._had_deep_hips = True
                self._feedback.append("Great low fielding base! Present glove out in front.")
            else:
                self._feedback.append("Drop your hips lower. Bend knees, don't bend at waist.")

            # Check glove presentation (wrist reaches near or below knee level)
            if lowest_wrist_y >= knee_y - 20:
                self._state = "GLOVE_OUT_FRONT"
                self._had_glove_out_front = True

        elif self._state == "GLOVE_OUT_FRONT":
            self._current_phase = "Glove Presentation & Funnel"
            self._feedback.append("Field ball out front on clean hop. Funnel smoothly to midsection.")
            # Transfer: athlete rises back up
            if avg_knee_angle > 145.0:
                self._state = "TRANSFER"

        elif self._state == "TRANSFER":
            self._current_phase = "Transfer to Throw"
            self._rep_count += 1
            if self._had_deep_hips and self._had_glove_out_front:
                self._good_reps += 1
                self._current_score = min(100.0, self._current_score + 2.5)
                self._feedback.append("Clean fielding rep: Deep hip sink with ball secured out front!")
            else:
                self._bad_reps += 1
                self._current_score = max(50.0, self._current_score - 7.0)
                if not self._had_deep_hips:
                    self._feedback.append("Form Break: Bent at waist. Drop your hips and bend knees.")
                else:
                    self._feedback.append("Form Break: Caught ball between feet. Reach glove out front.")

            self._state = "READY_STANCE"
            self._had_deep_hips = False
            self._had_glove_out_front = False
            self._min_hip_angle = 180.0

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
