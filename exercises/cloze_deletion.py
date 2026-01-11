"""Cloze deletion exercise.

Shows a Chinese sentence with a blank and asks the user to select the correct
vocabulary word from 4 choices to fill in the blank.
"""

import json
import random
import uuid
from pathlib import Path
from typing import Any

from exercises.base import ExerciseHandler, parse_letter_input, select_distractors
from models import ClozeDeletionExercise, KnowledgePoint


class ClozeDeletionHandler(ExerciseHandler[ClozeDeletionExercise]):
    """Handler for cloze deletion exercises."""

    DATA_DIR = Path(__file__).parent.parent / "data"

    @classmethod
    def generate(
        cls,
        knowledge_points: list[KnowledgePoint],
        target_kp: KnowledgePoint | None = None,
    ) -> ClozeDeletionExercise | None:
        """Generate a cloze deletion exercise.

        Args:
            knowledge_points: Available knowledge points.
            target_kp: Optional target knowledge point (unused for cloze).

        Returns:
            Generated exercise or None if generation fails.
        """
        templates = cls._load_templates()
        if not templates:
            return None

        template = random.choice(templates)

        vocab_kps = [kp for kp in knowledge_points if kp.type.value == "vocabulary"]
        if len(vocab_kps) < 4:
            return None

        target_kp = cls._find_target_vocab(template["target_vocab_id"], vocab_kps)
        if target_kp is None:
            return None

        distractors = select_distractors(target_kp, vocab_kps, count=3)
        if len(distractors) < 3:
            return None

        correct_option = f"{target_kp.chinese} ({target_kp.pinyin})"
        distractor_options = [f"{d.chinese} ({d.pinyin})" for d in distractors]

        all_options = [correct_option] + distractor_options
        random.shuffle(all_options)
        correct_index = all_options.index(correct_option)

        return ClozeDeletionExercise(
            id=str(uuid.uuid4()),
            knowledge_point_ids=[target_kp.id],
            difficulty=0.5,
            chinese_sentence=template["chinese"],
            english_translation=template["english"].replace(
                "_____", target_kp.english.split(",")[0].strip()
            ),
            target_word=target_kp.chinese,
            target_pinyin=target_kp.pinyin,
            target_english=target_kp.english.split(",")[0].strip(),
            options=all_options,
            correct_index=correct_index,
        )

    @classmethod
    def _load_templates(cls) -> list[dict]:
        """Load cloze templates from JSON file."""
        template_path = cls.DATA_DIR / "cloze_templates.json"
        if not template_path.exists():
            return []
        with open(template_path, encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _find_target_vocab(
        cls, vocab_id: str, vocab_kps: list[KnowledgePoint]
    ) -> KnowledgePoint | None:
        """Find vocabulary by ID."""
        for kp in vocab_kps:
            if kp.id == vocab_id:
                return kp
        return None

    def present(self) -> list[str]:
        """Present the exercise to the user.

        Returns the options list for answer checking.
        """
        print("\nComplete the sentence:")
        print(f"  {self.exercise.chinese_sentence}")
        print(f"  ({self.exercise.english_translation})")
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
        return f"Complete the sentence:\n  {self.exercise.chinese_sentence}\n  ({self.exercise.english_translation})"

    def format_feedback(self, is_correct: bool, correct_answer: str) -> str:
        """Return formatted feedback string."""
        if is_correct:
            return f"\n✓ Correct! {correct_answer}"
        else:
            return f"\n✗ Incorrect. The correct answer is: {correct_answer}"
