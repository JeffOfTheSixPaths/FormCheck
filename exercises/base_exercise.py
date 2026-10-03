"""Abstract base class and data structures for modular exercise analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExerciseMetrics:
    """Encapsulates the evaluation state for a single frame of an exercise."""

    phase: str = "Idle"
    score: float = 100.0  # Real-time form score [0.0 - 100.0]
    rep_count: int = 0
    good_reps: int = 0
    bad_reps: int = 0
    feedback: List[str] = field(default_factory=list)
    joint_angles: Dict[str, float] = field(default_factory=dict)
    # Highlight landmark indices on video feed with specific BGR colors
    # e.g. landmark_index: (B, G, R)
    joint_highlights: Dict[int, Tuple[int, int, int]] = field(default_factory=dict)


class BaseExercise(ABC):
    """Abstract interface for all FormCheck exercise analyzers."""

    def __init__(self, name: str, description: str = "") -> None:
        self._name = name
        self._description = description
        self._rep_count = 0
        self._good_reps = 0
        self._bad_reps = 0
        self._current_phase = "Idle"
        self._current_score = 100.0
        self._feedback: List[str] = []

    @property
    def name(self) -> str:
        """Name of the exercise."""
        return self._name

    @property
    def description(self) -> str:
        """Brief description of the exercise."""
        return self._description

    @property
    def rep_count(self) -> int:
        """Total completed reps."""
        return self._rep_count

    @property
    def good_reps(self) -> int:
        """Reps completed with proper form."""
        return self._good_reps

    @property
    def bad_reps(self) -> int:
        """Reps completed with form flaws."""
        return self._bad_reps

    @property
    def current_phase(self) -> str:
        """Current motion phase (e.g., Setup, Eccentric, Bottom, Concentric)."""
        return self._current_phase

    @abstractmethod
    def analyze(self, landmarks: Any, frame_shape: Tuple[int, ...]) -> ExerciseMetrics:
        """Processes pose landmarks for the current frame and returns evaluation metrics."""
        pass

    @abstractmethod
    def get_feedback(self) -> List[str]:
        """Returns the latest form cues and corrective feedback."""
        pass

    @abstractmethod
    def get_score(self) -> float:
        """Returns the current real-time or overall form quality score [0 - 100]."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets the repetition counters, state machines, and historical scores."""
        self._rep_count = 0
        self._good_reps = 0
        self._bad_reps = 0
        self._current_phase = "Idle"
        self._current_score = 100.0
        self._feedback.clear()
