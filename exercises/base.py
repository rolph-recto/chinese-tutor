"""Abstract base class and shared utilities for exercise handlers."""

import random
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from models import Exercise, KnowledgePoint

E = TypeVar("E", bound=Exercise)


class ExerciseHandler(ABC, Generic[E]):
    """Abstract base class for exercise handlers.

    Each exercise type should implement this interface to provide:
    - Exercise generation (classmethod)
    - Exercise presentation
    - Answer checking
    - User input processing (default implementation provided)
    - Feedback formatting (default implementation provided)

    To create a new exercise type:
    1. Create a Pydantic model in models.py extending Exercise
    2. Create a handler class extending ExerciseHandler[YourExerciseModel]
    3. Implement all abstract methods
    4. Register in EXERCISE_HANDLERS dict in main.py
    """

    def __init__(self, exercise: E):
        """Initialize handler with an exercise instance."""
        self.exercise = exercise

    @classmethod
    @abstractmethod
    def generate(
        cls,
        knowledge_points: list[KnowledgePoint],
        target_kp: KnowledgePoint | None = None,
    ) -> E | None:
        """Generate an exercise of this type.

        Args:
            knowledge_points: Available knowledge points for exercise generation.
            target_kp: Optional target knowledge point to focus on.

        Returns:
            Generated exercise or None if generation not possible.
        """
        ...

    @abstractmethod
    def present(self) -> Any:
        """Present the exercise to the user.

        Returns context needed for answer checking (e.g., shuffled options).
        """
        ...

    @abstractmethod
    def check_answer(
        self,
        user_input: str,
        context: Any = None,
    ) -> tuple[bool, str]:
        """Check if the user's answer is correct.

        Args:
            user_input: Raw user input string.
            context: Context from present() if needed.

        Returns:
            Tuple of (is_correct, correct_answer_display).
        """
        ...

    @abstractmethod
    def get_input_prompt(self) -> str:
        """Return the input prompt to show the user."""
        ...

    def process_user_input(self) -> tuple[bool, bool | None, str]:
        """Process user input for this exercise.

        Returns:
            Tuple of (should_retry, is_correct_or_None, correct_answer_display).
            - should_retry: True if invalid input, user should retry.
            - is_correct_or_None: True/False for correct/incorrect, None if quit.
            - correct_answer_display: String showing the correct answer.
        """
        context = self.present()
        user_input = input(self.get_input_prompt()).strip()

        if user_input.lower() == "q":
            return False, None, ""

        is_correct, correct_answer = self.check_answer(user_input, context)
        return False, is_correct, correct_answer

    def format_feedback(self, is_correct: bool, correct_answer: str) -> str:
        """Return formatted feedback string.

        Default implementation. Override for custom feedback.
        """
        if is_correct:
            return f"\nCorrect! {correct_answer}"
        else:
            return f"\nIncorrect. The correct answer is: {correct_answer}"


def parse_letter_input(user_input: str, max_options: int = 4) -> int | None:
    """Parse letter (A-F) or number (1-6) input to 0-based index.

    Args:
        user_input: Raw user input string.
        max_options: Maximum number of valid options.

    Returns:
        0-based index or None if input is invalid or out of bounds.
    """
    user_input = user_input.strip().upper()
    letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    if user_input in letter_map:
        index = letter_map[user_input]
    elif user_input.isdigit():
        index = int(user_input) - 1
    else:
        return None

    if index < 0 or index >= max_options:
        return None

    return index


def select_distractors(
    target_kp: KnowledgePoint,
    all_vocab: list[KnowledgePoint],
    count: int = 3,
) -> list[KnowledgePoint]:
    """Select distractor vocabulary items using mixed approach.

    Prefers items from the same cluster as the target, falls back to random.

    Args:
        target_kp: The target knowledge point to find distractors for.
        all_vocab: All available vocabulary knowledge points.
        count: Number of distractors to select.

    Returns:
        List of distractor knowledge points.
    """
    distractors = []
    used_ids = {target_kp.id}

    # Get target's cluster tags
    cluster_tags = [t for t in target_kp.tags if t.startswith("cluster:")]

    # First pass: same cluster
    if cluster_tags:
        same_cluster = [
            kp
            for kp in all_vocab
            if kp.id not in used_ids and any(t in kp.tags for t in cluster_tags)
        ]
        random.shuffle(same_cluster)
        for kp in same_cluster[:count]:
            distractors.append(kp)
            used_ids.add(kp.id)

    # Second pass: fill with random
    remaining = count - len(distractors)
    if remaining > 0:
        other_vocab = [kp for kp in all_vocab if kp.id not in used_ids]
        random.shuffle(other_vocab)
        distractors.extend(other_vocab[:remaining])

    return distractors
