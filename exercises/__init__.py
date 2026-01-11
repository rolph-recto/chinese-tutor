"""Exercise handlers for the Chinese tutor application.

This package provides different exercise types, all implementing the
ExerciseHandler abstract base class.

To add a new exercise type:
1. Create a Pydantic model in models.py extending Exercise
2. Create a handler class extending ExerciseHandler[YourExerciseModel]
3. Implement all abstract methods (generate, present, check_answer, get_input_prompt)
4. Register in EXERCISE_HANDLERS dict in main.py
"""

from exercises.base import ExerciseHandler, parse_letter_input, select_distractors
from exercises.chinese_to_english import ChineseToEnglishHandler
from exercises.cloze_deletion import ClozeDeletionHandler
from exercises.english_to_chinese import EnglishToChineseHandler
from exercises.minimal_pair import MinimalPairHandler
from exercises.segmented_translation import SegmentedTranslationHandler

__all__ = [
    "ExerciseHandler",
    "parse_letter_input",
    "select_distractors",
    "ChineseToEnglishHandler",
    "ClozeDeletionHandler",
    "EnglishToChineseHandler",
    "MinimalPairHandler",
    "SegmentedTranslationHandler",
]
