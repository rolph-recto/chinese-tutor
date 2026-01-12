"""Generic, domain-agnostic exercise handlers.

These handlers only handle presentation, input processing, and answer checking.
They do NOT know how to generate exercises - that's done by adapters.
"""

import random
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from exercises.generic_models import (
    FillBlankExercise,
    GenericExercise,
    MultipleChoiceExercise,
    ReorderExercise,
)
from exercises.base import parse_letter_input

E = TypeVar("E", bound=GenericExercise)


class GenericExerciseHandler(ABC, Generic[E]):
    """Abstract base class for generic exercise handlers.

    These handlers only handle presentation, input processing, and answer checking.
    They do NOT know how to generate exercises - that's done by adapters.
    """

    def __init__(self, exercise: E):
        self.exercise = exercise

    @abstractmethod
    def get_prompt_text(self) -> str:
        """Return the main prompt text."""
        ...

    @abstractmethod
    def get_options(self) -> list[str]:
        """Return options for display."""
        ...

    @abstractmethod
    def check_answer(self, user_input: str, context: Any = None) -> tuple[bool, str]:
        """Check answer. Returns (is_correct, correct_answer_display)."""
        ...

    @abstractmethod
    def get_input_prompt(self) -> str:
        """Return input prompt string."""
        ...

    def format_feedback(self, is_correct: bool, correct_answer: str) -> str:
        """Format feedback string. Override for custom feedback."""
        if is_correct:
            return f"\n✓ Correct! The answer is: {correct_answer}"
        else:
            return f"\n✗ Incorrect. The correct answer is: {correct_answer}"

    def process_user_input_with_input(
        self, user_input: str
    ) -> tuple[bool, bool | None, str]:
        """Process user input for this exercise with pre-collected input.

        Args:
            user_input: Raw user input string.

        Returns:
            Tuple of (should_retry, is_correct_or_None, correct_answer_display).
            - should_retry: True if invalid input, user should retry.
            - is_correct_or_None: True/False for correct/incorrect, None if quit.
            - correct_answer_display: String showing the correct answer.
        """
        if user_input.lower() == "q":
            return False, None, ""

        is_correct, correct_answer = self.check_answer(user_input)
        return False, is_correct, correct_answer


class MultipleChoiceHandler(GenericExerciseHandler[MultipleChoiceExercise]):
    """Handler for multiple choice exercises."""

    def get_prompt_text(self) -> str:
        if self.exercise.prompt_secondary:
            return f"{self.exercise.prompt} ({self.exercise.prompt_secondary})"
        return self.exercise.prompt

    def get_options(self) -> list[str]:
        return self.exercise.options

    def check_answer(self, user_input: str, context: Any = None) -> tuple[bool, str]:
        correct_answer = self.exercise.options[self.exercise.correct_index]
        user_index = parse_letter_input(user_input, len(self.exercise.options))
        if user_index is None:
            return False, correct_answer
        return user_index == self.exercise.correct_index, correct_answer

    def get_input_prompt(self) -> str:
        return "Enter your choice (A/B/C/D or 1/2/3/4): "


class FillBlankHandler(GenericExerciseHandler[FillBlankExercise]):
    """Handler for fill-in-blank exercises."""

    def get_prompt_text(self) -> str:
        text = f"Complete the sentence:\n  {self.exercise.sentence}"
        if self.exercise.context:
            text += f"\n  ({self.exercise.context})"
        return text

    def get_options(self) -> list[str]:
        return self.exercise.options

    def check_answer(self, user_input: str, context: Any = None) -> tuple[bool, str]:
        correct_answer = self.exercise.options[self.exercise.correct_index]
        user_index = parse_letter_input(user_input, len(self.exercise.options))
        if user_index is None:
            return False, correct_answer
        return user_index == self.exercise.correct_index, correct_answer

    def get_input_prompt(self) -> str:
        return "Enter your choice (A/B/C/D or 1/2/3/4): "


class ReorderHandler(GenericExerciseHandler[ReorderExercise]):
    """Handler for reorder exercises."""

    _shuffled_indices: list[int] | None = None

    def __init__(self, exercise: ReorderExercise):
        super().__init__(exercise)
        self._shuffled_indices = None

    def get_prompt_text(self) -> str:
        return self.exercise.prompt

    def get_options(self) -> list[str]:
        """Return shuffled items for display.

        Stores the shuffle state so answer checking uses the same order.
        """
        if self._shuffled_indices is None:
            self._shuffled_indices = list(range(len(self.exercise.items)))
            random.shuffle(self._shuffled_indices)
        return [self.exercise.items[i] for i in self._shuffled_indices]

    def check_answer(self, user_input: str, context: Any = None) -> tuple[bool, str]:
        """Check answer against the shuffled presentation."""
        # Use stored shuffle or context if provided
        shuffled_items = context if context else self.get_options()

        correct_sequence = [self.exercise.items[i] for i in self.exercise.correct_order]
        correct_answer = "".join(correct_sequence)

        try:
            user_order = [int(x) for x in user_input.split()]
            user_sequence = [shuffled_items[i - 1] for i in user_order]
            is_correct = "".join(user_sequence) == correct_answer
        except (IndexError, ValueError):
            is_correct = False

        return is_correct, correct_answer

    def get_input_prompt(self) -> str:
        return "Enter the numbers in correct order (e.g., 2 1 3): "

    def process_user_input_with_input(
        self, user_input: str
    ) -> tuple[bool, bool | None, str]:
        """Process user input with pre-collected input.

        Uses the stored shuffle state from get_options() for consistent answer checking.
        """
        # Ensure shuffle is initialized
        if self._shuffled_indices is None:
            self.get_options()

        shuffled_items = [self.exercise.items[i] for i in self._shuffled_indices]

        if user_input.lower() == "q":
            return False, None, ""

        # Validate input format
        try:
            [int(x) for x in user_input.split()]
        except ValueError:
            return True, False, ""

        is_correct, correct_answer = self.check_answer(user_input, shuffled_items)
        return False, is_correct, correct_answer
