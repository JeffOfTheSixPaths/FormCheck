"""Registry for dynamic registration and retrieval of athletic exercises."""

from typing import Dict, List, Type
from exercises.base_exercise import BaseExercise
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
from exercises.squat import SquatExercise
from exercises.pushup import PushUpExercise


class ExerciseRegistry:
    """Registry maintaining available athletic movement modules."""

    def __init__(self) -> None:
        self._exercises: Dict[str, Type[BaseExercise]] = {}
        # 1. Volleyball Modules
        self.register(VolleyballHittingArmSwingExercise)
        self.register(VolleyballHittingApproachExercise)
        self.register(VolleyballPassingExercise)
        self.register(VolleyballSettingExercise)

        # 2. Baseball Modules
        self.register(BaseballHittingExercise)
        self.register(BaseballPitchingExercise)
        self.register(BaseballFieldingExercise)

        # 3. Foundational Athletic Drills
        self.register(SquatExercise)
        self.register(PushUpExercise)

    def register(self, exercise_cls: Type[BaseExercise]) -> None:
        """Registers a new exercise class."""
        instance = exercise_cls()
        self._exercises[instance.name] = exercise_cls

    def get_names(self) -> List[str]:
        """Returns list of registered exercise names."""
        return list(self._exercises.keys())

    def create(self, name: str) -> BaseExercise:
        """Instantiates a fresh exercise analyzer by name."""
        if name not in self._exercises:
            raise ValueError(f"Exercise '{name}' not found. Available: {self.get_names()}")
        return self._exercises[name]()


# Global registry instance
registry = ExerciseRegistry()
