"""Chinese to English multiple choice exercise.

Shows a Chinese word and asks the student to select the correct English translation
from 4 choices.
"""

import random
import uuid
from typing import Any

from exercises.base import ExerciseHandler, parse_letter_input, select_distractors
from models import KnowledgePoint, MultipleChoiceVocabExercise


class ChineseToEnglishHandler(ExerciseHandler[MultipleChoiceVocabExercise]):
    """Handler for Chinese to English multiple choice exercises."""

    @classmethod
    def generate(
        cls,
        knowledge_points: list[KnowledgePoint],
        target_kp: KnowledgePoint | None = None,
    ) -> MultipleChoiceVocabExercise | None:
        """Generate a Chinese to English multiple choice exercise.

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

        # Build options: correct English + distractor English translations
        # Use first translation if multiple are provided (split by comma)
        correct_english = selected_kp.english.split(",")[0].strip()
        distractor_english = [d.english.split(",")[0].strip() for d in distractors]

        all_options = [correct_english] + distractor_english
        random.shuffle(all_options)

        # Find correct index after shuffling
        correct_index = all_options.index(correct_english)

        return MultipleChoiceVocabExercise(
            id=str(uuid.uuid4()),
            knowledge_point_ids=[selected_kp.id],
            difficulty=0.3,
            direction="chinese_to_english",
            prompt=selected_kp.chinese,
            prompt_pinyin=selected_kp.pinyin,
            options=all_options,
            correct_index=correct_index,
        )

    def present(self) -> list[str]:
        """Present the exercise to the user.

        Returns the options list for answer checking.
        """
        print(
            f'\nWhat is the English for "{self.exercise.prompt}" '
            f"({self.exercise.prompt_pinyin})?"
        )
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
