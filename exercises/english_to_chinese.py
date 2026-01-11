"""English to Chinese multiple choice exercise.

Shows an English word and asks the student to select the correct Chinese translation
from 4 choices (with pinyin shown).
"""

import random
import uuid
from typing import Any

from exercises.base import ExerciseHandler, parse_letter_input, select_distractors
from models import KnowledgePoint, MultipleChoiceVocabExercise


class EnglishToChineseHandler(ExerciseHandler[MultipleChoiceVocabExercise]):
    """Handler for English to Chinese multiple choice exercises."""

    @classmethod
    def generate(
        cls,
        knowledge_points: list[KnowledgePoint],
        target_kp: KnowledgePoint | None = None,
    ) -> MultipleChoiceVocabExercise | None:
        """Generate an English to Chinese multiple choice exercise.

        If target_kp is provided, uses that knowledge point as the target.
        Returns None if there aren't enough vocabulary items (need at least 4).
        """
        # Filter to vocabulary knowledge points only
        vocab_kps = [kp for kp in knowledge_points if kp.type.value == "vocabulary"]

        if len(vocab_kps) < 4:
            return None

        # Select target (use provided or random)
        if target_kp and target_kp.type.value == "vocabulary":
            selected_kp = target_kp
        else:
            selected_kp = random.choice(vocab_kps)

        # Get distractors
        distractors = select_distractors(selected_kp, vocab_kps, count=3)

        if len(distractors) < 3:
            return None

        # Build options: Chinese with pinyin for each option
        # Format: "中文 (pīnyīn)"
        correct_option = f"{selected_kp.chinese} ({selected_kp.pinyin})"
        distractor_options = [f"{d.chinese} ({d.pinyin})" for d in distractors]

        all_options = [correct_option] + distractor_options
        random.shuffle(all_options)

        # Find correct index after shuffling
        correct_index = all_options.index(correct_option)

        # Use first English translation if multiple provided
        prompt_english = selected_kp.english.split(",")[0].strip()

        return MultipleChoiceVocabExercise(
            id=str(uuid.uuid4()),
            knowledge_point_ids=[selected_kp.id],
            difficulty=0.4,
            direction="english_to_chinese",
            prompt=prompt_english,
            prompt_pinyin="",  # Not shown for English prompts
            options=all_options,
            correct_index=correct_index,
        )

    def present(self) -> list[str]:
        """Present the exercise to the user.

        Returns the options list for answer checking.
        """
        print(f'\nWhat is the Chinese for "{self.exercise.prompt}"?')
        print()

        labels = ["A", "B", "C", "D"]
        for i, option in enumerate(self.exercise.options):
            label = labels[i] if i < len(labels) else str(i + 1)
            print(f"  {label}. {option}")
        print()

        return self.exercise.options

    def check_answer(
        self,
        user_input: str,
        context: Any = None,
    ) -> tuple[bool, str]:
        """Check if the user's answer is correct.

        Args:
            user_input: Letter (A/B/C/D) or number (1/2/3/4).
            context: Unused, kept for interface consistency.

        Returns:
            Tuple of (is_correct, correct_answer_display).
        """
        correct_answer = self.exercise.options[self.exercise.correct_index]
        user_index = parse_letter_input(user_input, len(self.exercise.options))

        if user_index is None:
            return False, correct_answer

        is_correct = user_index == self.exercise.correct_index
        return is_correct, correct_answer

    def get_input_prompt(self) -> str:
        """Return the input prompt string."""
        return "Enter your choice (A/B/C/D or 1/2/3/4): "

    def get_options(self) -> list[str]:
        """Return the exercise options for UI display."""
        return self.exercise.options

    def get_prompt_text(self) -> str:
        """Return the prompt text for UI display."""
        return f'What is the Chinese for "{self.exercise.prompt}"?'

    def format_feedback(self, is_correct: bool, correct_answer: str) -> str:
        """Return formatted feedback string."""
        if is_correct:
            return f"\n✓ Correct! The answer is: {correct_answer}"
        else:
            return f"\n✗ Incorrect. The correct answer is: {correct_answer}"
