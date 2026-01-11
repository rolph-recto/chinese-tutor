"""Minimal pair exercise.

Multiple choice discrimination for visually/phonetically similar characters.
Shows an English definition and asks the student to pick the correct Chinese character.
"""

import json
import random
import uuid
from pathlib import Path
from typing import Any

from exercises.base import ExerciseHandler, parse_letter_input
from models import KnowledgePoint, MinimalPairExercise, MinimalPairOption

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_minimal_pairs() -> dict[str, list[dict]]:
    """Load minimal pairs data and return a dict mapping target_id to distractors."""
    pairs_file = DATA_DIR / "minimal_pairs.json"
    if not pairs_file.exists():
        return {}

    with open(pairs_file) as f:
        pairs_list = json.load(f)

    return {item["target_id"]: item["distractors"] for item in pairs_list}


class MinimalPairHandler(ExerciseHandler[MinimalPairExercise]):
    """Handler for minimal pair discrimination exercises."""

    @classmethod
    def generate(
        cls,
        knowledge_points: list[KnowledgePoint],
        target_kp: KnowledgePoint | None = None,
    ) -> MinimalPairExercise | None:
        """Generate a minimal pair exercise.

        If target_kp is provided, tries to generate an exercise for that knowledge point.
        Returns None if no minimal pairs are available for the selected vocabulary.
        """
        minimal_pairs = _load_minimal_pairs()

        if not minimal_pairs:
            return None

        # Get vocabulary knowledge points that have minimal pairs defined
        vocab_kps = [
            kp
            for kp in knowledge_points
            if kp.type.value == "vocabulary" and kp.id in minimal_pairs
        ]

        if not vocab_kps:
            return None

        # Select target (prefer target_kp if it has minimal pairs)
        if target_kp and target_kp.id in minimal_pairs:
            selected_kp = target_kp
        else:
            selected_kp = random.choice(vocab_kps)

        distractors = minimal_pairs[selected_kp.id]

        # Build options: correct answer + distractors
        correct_option = MinimalPairOption(
            chinese=selected_kp.chinese,
            pinyin=selected_kp.pinyin,
            english=selected_kp.english.split(",")[0].strip(),
        )

        distractor_options = [
            MinimalPairOption(
                chinese=d["chinese"], pinyin=d["pinyin"], english=d["english"]
            )
            for d in distractors
        ]

        # Combine and shuffle options
        all_options = [correct_option] + distractor_options
        random.shuffle(all_options)

        # Find the correct index after shuffling
        correct_index = next(
            i for i, opt in enumerate(all_options) if opt.chinese == selected_kp.chinese
        )

        return MinimalPairExercise(
            id=str(uuid.uuid4()),
            knowledge_point_ids=[selected_kp.id],
            difficulty=0.4,
            target_chinese=selected_kp.chinese,
            target_pinyin=selected_kp.pinyin,
            target_english=selected_kp.english.split(",")[0].strip(),
            options=all_options,
            correct_index=correct_index,
        )

    def present(self) -> list[MinimalPairOption]:
        """Present the exercise to the user.

        Returns the options list for answer checking.
        """
        print(
            f'\nSelect the character for "{self.exercise.target_english}" '
            f"({self.exercise.target_pinyin})"
        )
        print()

        labels = ["A", "B", "C", "D", "E", "F"]
        for i, option in enumerate(self.exercise.options):
            label = labels[i] if i < len(labels) else str(i + 1)
            print(f"  {label}. {option.chinese}")
        print()

        return self.exercise.options

    def check_answer(
        self,
        user_input: str,
        context: Any = None,
    ) -> tuple[bool, str]:
        """Check if the user's answer is correct.

        Args:
            user_input: Letter (A-F) or number (1-6).
            context: The options as presented (list of MinimalPairOption).

        Returns:
            Tuple of (is_correct, correct_answer_display).
        """
        options = context if context else self.exercise.options
        correct_opt = options[self.exercise.correct_index]
        correct_display = f"{correct_opt.chinese} ({correct_opt.pinyin})"

        user_index = parse_letter_input(user_input, len(options))

        if user_index is None:
            return False, correct_display

        is_correct = user_index == self.exercise.correct_index
        return is_correct, correct_display

    def get_input_prompt(self) -> str:
        """Return the input prompt string."""
        return "Enter your choice (A/B/C or 1/2/3): "

    def get_options(self) -> list[str]:
        """Return the exercise options for UI display."""
        return [opt.chinese for opt in self.exercise.options]

    def get_prompt_text(self) -> str:
        """Return the prompt text for UI display."""
        return f'Select the character for "{self.exercise.target_english}" ({self.exercise.target_pinyin})'

    def format_feedback(self, is_correct: bool, correct_answer: str) -> str:
        """Return formatted feedback string."""
        if is_correct:
            return f"\n✓ Correct! {correct_answer}"
        else:
            return f"\n✗ Incorrect. The correct answer is: {correct_answer}"
