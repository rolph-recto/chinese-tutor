"""Exercise handlers for the Chinese tutor application.

This package provides generic exercise types and a Chinese-specific adapter.

Generic exercise models:
- MultipleChoiceExercise: Pick one option from a list
- FillBlankExercise: Select word to complete a sentence
- ReorderExercise: Arrange items in correct sequence

Generic handlers:
- MultipleChoiceHandler: Handles multiple choice exercises
- FillBlankHandler: Handles fill-in-blank exercises
- ReorderHandler: Handles reorder exercises

Chinese adapter:
- ChineseExerciseAdapter: Transforms Chinese knowledge points to generic exercises
"""

from exercises.base import parse_letter_input, select_distractors
from exercises.generic_models import (
    FillBlankExercise,
    GenericExercise,
    MultipleChoiceExercise,
    ReorderExercise,
)
from exercises.generic_handlers import (
    FillBlankHandler,
    GenericExerciseHandler,
    MultipleChoiceHandler,
    ReorderHandler,
)
from exercises.chinese_adapter import ChineseExerciseAdapter

__all__ = [
    # Utilities
    "parse_letter_input",
    "select_distractors",
    # Generic models
    "GenericExercise",
    "MultipleChoiceExercise",
    "FillBlankExercise",
    "ReorderExercise",
    # Generic handlers
    "GenericExerciseHandler",
    "MultipleChoiceHandler",
    "FillBlankHandler",
    "ReorderHandler",
    # Chinese adapter
    "ChineseExerciseAdapter",
]
