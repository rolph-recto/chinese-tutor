"""Segmented translation exercise.

English sentence to reorder Chinese chunks (template-based).
"""

import random
import uuid
from typing import Any

from exercises.base import ExerciseHandler
from models import KnowledgePoint, SegmentedTranslationExercise


# Exercise templates: (english_template, chinese_chunks_template, knowledge_point_ids)
# Placeholders: {subject}, {object}, {verb}, etc. are replaced with vocabulary
TEMPLATES = [
    # Basic 是 sentences
    {
        "english": "{subject} {be} a {noun}",
        "chunks": ["{subject_cn}", "是", "{noun_cn}"],
        "slots": {"subject": "pronoun", "noun": "noun"},
        "grammar_id": "g001",
    },
    # Negation with 不是
    {
        "english": "{subject} {be} not a {noun}",
        "chunks": ["{subject_cn}", "不", "是", "{noun_cn}"],
        "slots": {"subject": "pronoun", "noun": "noun"},
        "grammar_id": "g002",
    },
    # 很 + Adjective
    {
        "english": "{subject} {be} very {adjective}",
        "chunks": ["{subject_cn}", "很", "{adjective_cn}"],
        "slots": {"subject": "pronoun", "adjective": "adjective"},
        "grammar_id": "g004",
    },
    # 喜欢 + Object
    {
        "english": "{subject} {like} {object}",
        "chunks": ["{subject_cn}", "喜欢", "{object_cn}"],
        "slots": {"subject": "pronoun", "object": "noun"},
        "grammar_id": "g005",
        "verbs": {"like": ("like", "likes")},
    },
    # Verb + Object
    {
        "english": "{subject} {drink} {object}",
        "chunks": ["{subject_cn}", "喝", "{object_cn}"],
        "slots": {"subject": "pronoun", "object": "drink"},
        "grammar_id": None,
        "verbs": {"drink": ("drink", "drinks")},
    },
    {
        "english": "{subject} {eat} {object}",
        "chunks": ["{subject_cn}", "吃", "{object_cn}"],
        "slots": {"subject": "pronoun", "object": "food"},
        "grammar_id": None,
        "verbs": {"eat": ("eat", "eats")},
    },
]

# Vocabulary categories for template filling
VOCAB_CATEGORIES = {
    "pronoun": ["v001", "v002", "v003", "v004"],  # 我, 你, 他, 她
    "noun": ["v007", "v008", "v009", "v011"],  # 学生, 老师, 朋友, 人
    "adjective": ["v017"],  # 好
    "drink": ["v014", "v015"],  # 水, 茶
    "food": ["v016"],  # 米饭
}


def _conjugate_be(subject: str) -> str:
    """Return the correct form of 'to be' for the subject."""
    if subject.lower() == "i":
        return "am"
    elif subject.lower() in ("you", "we", "they"):
        return "are"
    else:
        return "is"


def _is_third_person(subject: str) -> bool:
    """Check if subject is third person singular."""
    return subject.lower() not in ("i", "you", "we", "they")


class SegmentedTranslationHandler(ExerciseHandler[SegmentedTranslationExercise]):
    """Handler for segmented translation exercises."""

    # Store knowledge points for feedback formatting
    _knowledge_points: list[KnowledgePoint] | None = None

    @classmethod
    def generate(
        cls,
        knowledge_points: list[KnowledgePoint],
        target_kp: KnowledgePoint | None = None,
    ) -> SegmentedTranslationExercise:
        """Generate a segmented translation exercise.

        If target_kp is provided, tries to generate an exercise that tests
        that knowledge point.

        Note: This method always returns an exercise (never None).
        """
        kp_dict = {kp.id: kp for kp in knowledge_points}

        # Select a template (random for now, could be smarter based on target_kp)
        template = random.choice(TEMPLATES)

        # Fill in the template slots with vocabulary
        english_parts = {}
        chinese_parts = {}
        used_kp_ids = []

        for slot_name, category in template["slots"].items():
            vocab_ids = VOCAB_CATEGORIES.get(category, [])
            available = [kp_dict[vid] for vid in vocab_ids if vid in kp_dict]
            if not available:
                continue
            chosen = random.choice(available)
            english_parts[slot_name] = chosen.english.split(",")[0].strip()
            chinese_parts[f"{slot_name}_cn"] = chosen.chinese
            used_kp_ids.append(chosen.id)

        # Handle verb conjugation for "to be"
        if "subject" in english_parts:
            english_parts["be"] = _conjugate_be(english_parts["subject"])
            # Handle other verbs
            third_person = _is_third_person(english_parts["subject"])
            for verb_key, (base, third) in template.get("verbs", {}).items():
                english_parts[verb_key] = third if third_person else base

        # Build the English sentence
        english_sentence = template["english"].format(**english_parts)

        # Build the Chinese chunks
        chinese_chunks = []
        for chunk in template["chunks"]:
            if chunk.startswith("{") and chunk.endswith("}"):
                chinese_chunks.append(chinese_parts.get(chunk[1:-1], chunk))
            else:
                chinese_chunks.append(chunk)

        # Add grammar knowledge point if applicable
        if template["grammar_id"]:
            used_kp_ids.append(template["grammar_id"])

        # Correct order is just 0, 1, 2, ... (chunks are in correct order in template)
        correct_order = list(range(len(chinese_chunks)))

        return SegmentedTranslationExercise(
            id=str(uuid.uuid4()),
            knowledge_point_ids=used_kp_ids,
            difficulty=0.3,  # Basic difficulty for HSK1
            english_sentence=english_sentence,
            chinese_chunks=chinese_chunks,
            correct_order=correct_order,
        )

    def __init__(
        self,
        exercise: SegmentedTranslationExercise,
        knowledge_points: list[KnowledgePoint] | None = None,
    ):
        """Initialize handler with exercise and optional knowledge points for feedback."""
        super().__init__(exercise)
        self._knowledge_points = knowledge_points

    def present(self) -> list[str]:
        """Present the exercise to the user.

        Returns the shuffled chunks for display.
        """
        # Create shuffled indices
        shuffled_indices = list(range(len(self.exercise.chinese_chunks)))
        random.shuffle(shuffled_indices)

        # Return chunks in shuffled order
        shuffled_chunks = [self.exercise.chinese_chunks[i] for i in shuffled_indices]

        print(f'\nTranslate: "{self.exercise.english_sentence}"')
        print()
        print("Chunks:")
        for i, chunk in enumerate(shuffled_chunks, 1):
            print(f"  {i}. {chunk}")
        print()

        return shuffled_chunks

    def check_answer(
        self,
        user_input: str,
        context: Any = None,
    ) -> tuple[bool, str]:
        """Check if the user's answer is correct.

        Args:
            user_input: Space-separated numbers (e.g., "2 1 3").
            context: The shuffled chunks as presented to the user.

        Returns:
            Tuple of (is_correct, correct_sentence).
        """
        shuffled_chunks = context if context else self.exercise.chinese_chunks

        # Build the correct sentence
        correct_chunks = [
            self.exercise.chinese_chunks[i] for i in self.exercise.correct_order
        ]
        correct_sentence = "".join(correct_chunks)

        # Parse user input
        try:
            user_order = [int(x) for x in user_input.split()]
            user_chunks = [shuffled_chunks[i - 1] for i in user_order]
            user_sentence = "".join(user_chunks)
            is_correct = user_sentence == correct_sentence
        except (IndexError, TypeError, ValueError):
            is_correct = False

        return is_correct, correct_sentence

    def get_input_prompt(self) -> str:
        """Return the input prompt string."""
        return "Enter the numbers in correct order (e.g., 2 1 3): "

    def process_user_input(self) -> tuple[bool, bool | None, str]:
        """Process user input for a segmented translation exercise.

        Overrides default to handle invalid input retry behavior.

        Returns:
            Tuple of (should_retry, is_correct_or_None, correct_answer_display).
        """
        shuffled_chunks = self.present()

        user_input = input(self.get_input_prompt()).strip()

        if user_input.lower() == "q":
            return False, None, ""

        try:
            # Validate that input can be parsed as integers
            [int(x) for x in user_input.split()]
        except ValueError:
            print("Invalid input. Please enter numbers separated by spaces.\n")
            return True, False, ""

        is_correct, correct_sentence = self.check_answer(user_input, shuffled_chunks)

        return False, is_correct, correct_sentence

    def format_feedback(self, is_correct: bool, correct_answer: str) -> str:
        """Return formatted feedback string for a segmented translation exercise.

        Includes pinyin in the feedback if knowledge_points were provided.
        """
        knowledge_points = self._knowledge_points or []
        kp_dict = {kp.chinese: kp for kp in knowledge_points}

        chunks = list(correct_answer)
        pinyin_parts = []
        for chunk in chunks:
            if chunk in kp_dict:
                pinyin_parts.append(kp_dict[chunk].pinyin)
            else:
                pinyin_parts.append("")

        if is_correct:
            return f"\nCorrect! {correct_answer} ({' '.join(pinyin_parts)})"
        else:
            return (
                f"\nIncorrect. The correct answer is: {correct_answer}\n"
                f"Pinyin: {' '.join(pinyin_parts)}"
            )
