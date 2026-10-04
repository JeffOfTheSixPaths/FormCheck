"""Unit tests for Volleyball and Baseball athletic exercise analyzers."""

import numpy as np
from dataclasses import dataclass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exercises.registry import registry
from exercises.volleyball import (
    VolleyballHittingArmSwingExercise,
    VolleyballHittingApproachExercise,
    VolleyballPassingExercise,
    VolleyballSettingExercise,
)
from exercises.baseball import (
    BaseballHittingExercise,
    BaseballPitchingExercise,
    BaseballFieldingExercise,
)
from pose.landmarks import PoseLandmark


@dataclass
class DummyLandmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 0.99


def create_mock_pose(overrides=None):
    """Creates a 33-landmark pose with natural standing coordinates."""
    # Normalized coords [0, 1]
    landmarks = [DummyLandmark(0.5, 0.5) for _ in range(33)]

    # Head
    landmarks[PoseLandmark.NOSE] = DummyLandmark(0.50, 0.20)
    # Shoulders
    landmarks[PoseLandmark.LEFT_SHOULDER] = DummyLandmark(0.55, 0.32)
    landmarks[PoseLandmark.RIGHT_SHOULDER] = DummyLandmark(0.45, 0.32)
    # Elbows
    landmarks[PoseLandmark.LEFT_ELBOW] = DummyLandmark(0.58, 0.45)
    landmarks[PoseLandmark.RIGHT_ELBOW] = DummyLandmark(0.42, 0.45)
    # Wrists
    landmarks[PoseLandmark.LEFT_WRIST] = DummyLandmark(0.59, 0.58)
    landmarks[PoseLandmark.RIGHT_WRIST] = DummyLandmark(0.41, 0.58)
    # Hips
    landmarks[PoseLandmark.LEFT_HIP] = DummyLandmark(0.54, 0.56)
    landmarks[PoseLandmark.RIGHT_HIP] = DummyLandmark(0.46, 0.56)
    # Knees
    landmarks[PoseLandmark.LEFT_KNEE] = DummyLandmark(0.54, 0.74)
    landmarks[PoseLandmark.RIGHT_KNEE] = DummyLandmark(0.46, 0.74)
    # Ankles
    landmarks[PoseLandmark.LEFT_ANKLE] = DummyLandmark(0.54, 0.92)
    landmarks[PoseLandmark.RIGHT_ANKLE] = DummyLandmark(0.46, 0.92)

    if overrides:
        for idx, lm in overrides.items():
            landmarks[idx] = lm

    return landmarks


def test_registry():
    names = registry.get_names()
    assert "Volleyball: Hitting (Arm Swing)" in names
    assert "Volleyball: Hitting (Approach)" in names
    assert "Volleyball: Passing" in names
    assert "Volleyball: Setting" in names
    assert "Baseball: Hitting" in names
    assert "Baseball: Pitching" in names
    assert "Baseball: Fielding" in names
    print("[PASS] All 7 athletic movements registered.")


def test_volleyball_hitting_arm_swing():
    ex = VolleyballHittingArmSwingExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Elbow Angle" in m.joint_angles
    print("[PASS] Volleyball Hitting Arm Swing analyzed.")


def test_volleyball_hitting_approach():
    ex = VolleyballHittingApproachExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Plant Knee Flexion" in m.joint_angles
    print("[PASS] Volleyball Hitting Approach analyzed.")


def test_volleyball_passing():
    ex = VolleyballPassingExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Platform Elbow Lock" in m.joint_angles
    print("[PASS] Volleyball Passing analyzed.")


def test_volleyball_setting():
    ex = VolleyballSettingExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Elbow Cushion Angle" in m.joint_angles
    print("[PASS] Volleyball Setting analyzed.")


def test_baseball_hitting():
    ex = BaseballHittingExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Back Elbow Slot" in m.joint_angles
    print("[PASS] Baseball Hitting analyzed.")


def test_baseball_pitching():
    ex = BaseballPitchingExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Throwing Elbow 90/90" in m.joint_angles
    print("[PASS] Baseball Pitching analyzed.")


def test_baseball_fielding():
    ex = BaseballFieldingExercise()
    pose = create_mock_pose()
    m = ex.analyze(pose, (720, 1280))
    assert m.phase is not None
    assert "Hip Sink Depth" in m.joint_angles
    print("[PASS] Baseball Fielding analyzed.")


if __name__ == "__main__":
    test_registry()
    test_volleyball_hitting_arm_swing()
    test_volleyball_hitting_approach()
    test_volleyball_passing()
    test_volleyball_setting()
    test_baseball_hitting()
    test_baseball_pitching()
    test_baseball_fielding()
    print("\nALL ATHLETIC EXERCISE TESTS PASSED!")
