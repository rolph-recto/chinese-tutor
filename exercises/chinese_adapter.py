"""Chinese language adapter for exercise generation.

Transforms Chinese knowledge points into generic exercise inputs.
This module contains all domain-specific logic for Chinese language tutoring.
"""

import random
import uuid

from models import KnowledgePoint
from exercises.generic_models import (
    FillBlankExercise,
    MultipleChoiceExercise,
    ReorderExercise,
)
from exercises.base import select_distractors
from storage import get_cloze_templates_repo, get_minimal_pairs_repo


# Exercise templates for segmented translation
# (english_template, chinese_chunks_template, knowledge_point_ids)
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


class ChineseExerciseAdapter:
    """Adapts Chinese knowledge points to generic exercises.

    This class contains all domain-specific logic for transforming
    Chinese vocabulary and grammar knowledge points into generic
    exercise models.
    """

    def __init__(self, knowledge_points: list[KnowledgePoint]):
        self.knowledge_points = knowledge_points
        self.vocab_kps = [
            kp for kp in knowledge_points if kp.type.value == "vocabulary"
        ]
        self.kp_dict = {kp.id: kp for kp in knowledge_points}

    def create_chinese_to_english(
        self, target_kp: KnowledgePoint | None = None
    ) -> MultipleChoiceExercise | None:
        """Create a Chinese-to-English multiple choice exercise.

        Shows a Chinese word and asks for the English translation.
        """
        if len(self.vocab_kps) < 4:
            return None

        selected = (
            target_kp
            if target_kp and target_kp.type.value == "vocabulary"
            else random.choice(self.vocab_kps)
        )
        distractors = select_distractors(selected, self.vocab_kps, count=3)

        if len(distractors) < 3:
            return None

        correct_english = selected.english.split(",")[0].strip()
        options = [correct_english] + [
            d.english.split(",")[0].strip() for d in distractors
        ]
        random.shuffle(options)

        return MultipleChoiceExercise(
            id=str(uuid.uuid4()),
            source_ids=[selected.id],
            difficulty=0.3,
            prompt=f'What is the English for "{selected.chinese}"?',
            prompt_secondary=selected.pinyin,
            options=options,
            correct_index=options.index(correct_english),
            metadata={
                "chinese": selected.chinese,
                "pinyin": selected.pinyin,
                "english": selected.english,
                "direction": "chinese_to_english",
            },
        )

    def create_english_to_chinese(
        self, target_kp: KnowledgePoint | None = None
    ) -> MultipleChoiceExercise | None:
        """Create an English-to-Chinese multiple choice exercise.

        Shows an English word and asks for the Chinese translation.
        """
        if len(self.vocab_kps) < 4:
            return None

        selected = (
            target_kp
            if target_kp and target_kp.type.value == "vocabulary"
            else random.choice(self.vocab_kps)
        )
        distractors = select_distractors(selected, self.vocab_kps, count=3)

        if len(distractors) < 3:
            return None

        correct_option = f"{selected.chinese} ({selected.pinyin})"
        options = [correct_option] + [f"{d.chinese} ({d.pinyin})" for d in distractors]
        random.shuffle(options)

        prompt_english = selected.english.split(",")[0].strip()

        return MultipleChoiceExercise(
            id=str(uuid.uuid4()),
            source_ids=[selected.id],
            difficulty=0.4,
            prompt=f'What is the Chinese for "{prompt_english}"?',
            prompt_secondary="",
            options=options,
            correct_index=options.index(correct_option),
            metadata={
                "chinese": selected.chinese,
                "pinyin": selected.pinyin,
                "english": selected.english,
                "direction": "english_to_chinese",
            },
        )

    def create_minimal_pair(
        self, target_kp: KnowledgePoint | None = None
    ) -> MultipleChoiceExercise | None:
        """Create a minimal pair discrimination exercise.

        Shows an English definition and asks to select the correct Chinese character
        from visually/phonetically similar options.
        """
        repo = get_minimal_pairs_repo()
        minimal_pairs = repo.get_all_as_dict()

        if not minimal_pairs:
            return None

        vocab_with_pairs = [kp for kp in self.vocab_kps if kp.id in minimal_pairs]
        if not vocab_with_pairs:
            return None

        selected = (
            target_kp
            if target_kp and target_kp.id in minimal_pairs
            else random.choice(vocab_with_pairs)
        )
        distractors = minimal_pairs[selected.id]

        correct_option = selected.chinese
        options = [correct_option] + [d["chinese"] for d in distractors]
        random.shuffle(options)

        target_english = selected.english.split(",")[0].strip()

        return MultipleChoiceExercise(
            id=str(uuid.uuid4()),
            source_ids=[selected.id],
            difficulty=0.4,
            prompt=f'Select the character for "{target_english}"',
            prompt_secondary=selected.pinyin,
            options=options,
            correct_index=options.index(correct_option),
            metadata={
                "target_chinese": selected.chinese,
                "target_pinyin": selected.pinyin,
                "target_english": target_english,
                "distractors": distractors,
            },
        )

    def create_cloze_deletion(
        self, target_kp: KnowledgePoint | None = None
    ) -> FillBlankExercise | None:
        """Create a cloze deletion exercise.

        Shows a Chinese sentence with a blank and asks to select the correct
        vocabulary word to fill it.
        """
        repo = get_cloze_templates_repo()
        templates = repo.get_all()

        if not templates or len(self.vocab_kps) < 4:
            return None

        template = random.choice(templates)
        target = next(
            (kp for kp in self.vocab_kps if kp.id == template["target_vocab_id"]), None
        )

        if target is None:
            return None

        distractors = select_distractors(target, self.vocab_kps, count=3)
        if len(distractors) < 3:
            return None

        correct_option = f"{target.chinese} ({target.pinyin})"
        options = [correct_option] + [f"{d.chinese} ({d.pinyin})" for d in distractors]
        random.shuffle(options)

        english_translation = template["english"].replace(
            "_____", target.english.split(",")[0].strip()
        )

        return FillBlankExercise(
            id=str(uuid.uuid4()),
            source_ids=[target.id],
            difficulty=0.5,
            sentence=template["chinese"],
            context=english_translation,
            options=options,
            correct_index=options.index(correct_option),
            metadata={
                "target_word": target.chinese,
                "target_pinyin": target.pinyin,
                "target_english": target.english.split(",")[0].strip(),
            },
        )

    def create_segmented_translation(
        self, target_kp: KnowledgePoint | None = None
    ) -> ReorderExercise:
        """Create a segmented translation (reorder) exercise.

        Shows an English sentence and asks to arrange Chinese chunks
        in the correct order.
        """
        template = random.choice(TEMPLATES)

        english_parts = {}
        chinese_parts = {}
        used_kp_ids = []

        for slot_name, category in template["slots"].items():
            vocab_ids = VOCAB_CATEGORIES.get(category, [])
            available = [self.kp_dict[vid] for vid in vocab_ids if vid in self.kp_dict]
            if available:
                chosen = random.choice(available)
                english_parts[slot_name] = chosen.english.split(",")[0].strip()
                chinese_parts[f"{slot_name}_cn"] = chosen.chinese
                used_kp_ids.append(chosen.id)

        # Handle verb conjugation for "to be"
        if "subject" in english_parts:
            english_parts["be"] = _conjugate_be(english_parts["subject"])
            third_person = _is_third_person(english_parts["subject"])
            for verb_key, (base, third) in template.get("verbs", {}).items():
                english_parts[verb_key] = third if third_person else base

        english_sentence = template["english"].format(**english_parts)

        chinese_chunks = []
        for chunk in template["chunks"]:
            if chunk.startswith("{") and chunk.endswith("}"):
                chinese_chunks.append(chinese_parts.get(chunk[1:-1], chunk))
            else:
                chinese_chunks.append(chunk)

        if template.get("grammar_id"):
            used_kp_ids.append(template["grammar_id"])

        # Store knowledge points for feedback
        kps_for_feedback = [
            self.kp_dict.get(kp_id) for kp_id in used_kp_ids if kp_id in self.kp_dict
        ]

        return ReorderExercise(
            id=str(uuid.uuid4()),
            source_ids=used_kp_ids,
            difficulty=0.3,
            prompt=f'Translate: "{english_sentence}"',
            items=chinese_chunks,
            correct_order=list(range(len(chinese_chunks))),
            metadata={
                "english_sentence": english_sentence,
                "chinese_chunks": chinese_chunks,
                "knowledge_points": kps_for_feedback,
            },
        )
