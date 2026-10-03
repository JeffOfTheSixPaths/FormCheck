"""Registry for dynamic registration and retrieval of exercises."""

from typing import Dict, List, Type
from exercises.base_exercise import BaseExercise
from exercises.pushup import PushUpExercise
from exercises.squat import SquatExercise


class ExerciseRegistry:
    """Registry maintaining available exercise modules."""

    def __init__(self) -> None:
        self._exercises: Dict[str, Type[BaseExercise]] = {}
        # Register core defaults
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
