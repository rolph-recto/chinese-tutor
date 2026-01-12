"""Exercise generators that consume schemas and produce exercises.

These generators contain the procedural logic for building exercises
from declarative schemas. The logic is generic and can work with
any schema populated by a language-specific populator.
"""

import random
import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .config import FillBlankConfig, MultipleChoiceConfig, ReorderConfig
from .generic_models import (
    FillBlankExercise,
    GenericExercise,
    MultipleChoiceExercise,
    ReorderExercise,
)
from .schemas import FillBlankSchema, MultipleChoiceSchema, ReorderSchema

S = TypeVar("S")  # Schema type
C = TypeVar("C")  # Config type
E = TypeVar("E", bound=GenericExercise)  # Exercise type


class ExerciseGenerator(ABC, Generic[S, C, E]):
    """Abstract base class for exercise generators."""

    def __init__(self, schema: S, config: C):
        self.schema = schema
        self.config = config

    @abstractmethod
    def generate(
        self,
        target_kp_id: str | None = None,
        prompt_type_id: str | None = None,
    ) -> E | None:
        """Generate an exercise, optionally targeting a specific KP.

        Args:
            target_kp_id: If provided, generate exercise for this knowledge point.
            prompt_type_id: If provided, use this specific prompt type.

        Returns:
            An exercise, or None if generation is not possible.
        """
        pass

    @abstractmethod
    def can_generate(self, target_kp_id: str | None = None) -> bool:
        """Check if generation is possible.

        Args:
            target_kp_id: If provided, check if this KP can be targeted.

        Returns:
            True if an exercise can be generated.
        """
        pass


class MultipleChoiceGenerator(
    ExerciseGenerator[
        MultipleChoiceSchema, MultipleChoiceConfig, MultipleChoiceExercise
    ]
):
    """Generates multiple choice exercises from schema."""

    def can_generate(self, target_kp_id: str | None = None) -> bool:
        if not self.schema.prompt_values:
            return False

        if target_kp_id:
            matching = [
                pv
                for pv in self.schema.prompt_values
                if pv.knowledge_point_id == target_kp_id
            ]
            return len(matching) > 0

        return True

    def generate(
        self,
        target_kp_id: str | None = None,
        prompt_type_id: str | None = None,
    ) -> MultipleChoiceExercise | None:
        # Select prompt value
        candidates = self.schema.prompt_values

        if target_kp_id:
            candidates = [
                pv for pv in candidates if pv.knowledge_point_id == target_kp_id
            ]

        if prompt_type_id:
            candidates = [
                pv for pv in candidates if pv.prompt_type_id == prompt_type_id
            ]

        if not candidates:
            return None

        prompt_value = random.choice(candidates)

        # Get prompt template
        prompt_type = next(
            (
                pt
                for pt in self.schema.prompt_types
                if pt.id == prompt_value.prompt_type_id
            ),
            None,
        )
        if not prompt_type:
            return None

        # Get available options for this prompt value
        available_options = [
            opt
            for opt in self.schema.options
            if opt.prompt_type_id == prompt_value.prompt_type_id
            and opt.value == prompt_value.value
        ]

        distractors = [o for o in available_options if o.option_type_id == "distractor"]
        nondistractors = [
            o for o in available_options if o.option_type_id == "nondistractor"
        ]

        # Build options list based on config
        # We need (total_options - 1) wrong answers
        num_wrong_needed = self.config.total_options - 1

        # Select distractors first (up to max_distractors, at least min_distractors)
        num_distractors = min(
            len(distractors),
            min(self.config.max_distractors, num_wrong_needed),
        )
        num_distractors = max(
            num_distractors, min(self.config.min_distractors, len(distractors))
        )

        random.shuffle(distractors)
        selected_options = [d.option_value for d in distractors[:num_distractors]]

        # Fill remaining slots with non-distractors
        remaining_slots = num_wrong_needed - len(selected_options)
        if remaining_slots > 0:
            random.shuffle(nondistractors)
            selected_options.extend(
                [n.option_value for n in nondistractors[:remaining_slots]]
            )

        # If still not enough options, can't generate
        if len(selected_options) < num_wrong_needed:
            return None

        # Add correct answer and shuffle
        options = [prompt_value.correct_answer] + selected_options[:num_wrong_needed]

        if self.config.shuffle_options:
            random.shuffle(options)

        # Build prompt
        prompt = prompt_type.template.format(value=prompt_value.value)

        # Only show pinyin as secondary prompt for chinese_to_english and minimal_pair
        # For english_to_chinese, secondary prompt is empty
        if prompt_value.prompt_type_id in ("chinese_to_english", "minimal_pair"):
            prompt_secondary = prompt_value.metadata.get("pinyin", "")
        else:
            prompt_secondary = ""

        return MultipleChoiceExercise(
            id=str(uuid.uuid4()),
            source_ids=[prompt_value.knowledge_point_id],
            difficulty=0.4,
            prompt=prompt,
            prompt_secondary=prompt_secondary,
            options=options,
            correct_index=options.index(prompt_value.correct_answer),
            metadata={
                "prompt_type": prompt_value.prompt_type_id,
                **prompt_type.metadata,
                **prompt_value.metadata,
            },
        )


class FillBlankGenerator(
    ExerciseGenerator[FillBlankSchema, FillBlankConfig, FillBlankExercise]
):
    """Generates fill-blank exercises from schema."""

    def can_generate(self, target_kp_id: str | None = None) -> bool:
        if not self.schema.fills:
            return False

        if target_kp_id:
            matching = [
                f for f in self.schema.fills if f.knowledge_point_id == target_kp_id
            ]
            return len(matching) > 0

        return True

    def generate(
        self,
        target_kp_id: str | None = None,
        prompt_type_id: str | None = None,
    ) -> FillBlankExercise | None:
        candidates = self.schema.fills

        if target_kp_id:
            candidates = [f for f in candidates if f.knowledge_point_id == target_kp_id]

        if not candidates:
            return None

        fill = random.choice(candidates)

        # Get template
        template = next(
            (t for t in self.schema.templates if t.id == fill.template_id),
            None,
        )
        if not template:
            return None

        # Get options
        available_options = [
            opt
            for opt in self.schema.options
            if opt.template_id == fill.template_id
            and opt.fill_value == fill.correct_answer
        ]

        distractors = [o for o in available_options if o.option_type_id == "distractor"]
        nondistractors = [
            o for o in available_options if o.option_type_id == "nondistractor"
        ]

        num_wrong_needed = self.config.total_options - 1

        # Select distractors first
        num_distractors = min(len(distractors), self.config.min_distractors)
        random.shuffle(distractors)
        selected_options = [d.option_value for d in distractors[:num_distractors]]

        # Fill remaining with non-distractors
        remaining = num_wrong_needed - len(selected_options)
        if remaining > 0:
            random.shuffle(nondistractors)
            selected_options.extend(
                [n.option_value for n in nondistractors[:remaining]]
            )

        if len(selected_options) < num_wrong_needed:
            return None

        options = [fill.correct_answer] + selected_options[:num_wrong_needed]

        if self.config.shuffle_options:
            random.shuffle(options)

        return FillBlankExercise(
            id=str(uuid.uuid4()),
            source_ids=[fill.knowledge_point_id],
            difficulty=0.5,
            sentence=template.sentence,
            context=template.context,
            options=options,
            correct_index=options.index(fill.correct_answer),
            metadata={
                "template_id": template.id,
                **fill.metadata,
            },
        )


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


class ReorderGenerator(
    ExerciseGenerator[ReorderSchema, ReorderConfig, ReorderExercise]
):
    """Generates reorder exercises from schema."""

    def can_generate(self, target_kp_id: str | None = None) -> bool:
        if not self.schema.templates or not self.schema.slot_fills:
            return False
        return True

    def generate(
        self,
        target_kp_id: str | None = None,
        prompt_type_id: str | None = None,
    ) -> ReorderExercise | None:
        # Select a template
        # If target_kp_id is provided, prefer templates that can use that KP
        if target_kp_id:
            # Find templates where this KP can fill a slot
            viable_templates = []
            for tmpl in self.schema.templates:
                slot_fills_for_tmpl = [
                    sf
                    for sf in self.schema.slot_fills
                    if sf.template_id == tmpl.id
                    and sf.knowledge_point_id == target_kp_id
                ]
                if slot_fills_for_tmpl:
                    viable_templates.append(tmpl)

            if not viable_templates:
                # Fall back to any template
                viable_templates = self.schema.templates
        else:
            viable_templates = self.schema.templates

        if not viable_templates:
            return None

        template = random.choice(viable_templates)

        # Fill slots
        slot_values: dict[str, str] = {}  # slot_type -> chinese value
        english_values: dict[str, str] = {}  # slot_type -> english value
        used_kp_ids: list[str] = []

        for slot_type in template.slot_types:
            candidates = [
                sf
                for sf in self.schema.slot_fills
                if sf.template_id == template.id and sf.slot_type == slot_type
            ]

            if not candidates:
                return None

            # If targeting a KP and it can fill this slot, prefer it
            if target_kp_id:
                target_candidates = [
                    sf for sf in candidates if sf.knowledge_point_id == target_kp_id
                ]
                if target_candidates:
                    candidates = target_candidates

            chosen = random.choice(candidates)
            slot_values[slot_type] = chosen.slot_value
            english_values[slot_type] = chosen.english_value
            used_kp_ids.append(chosen.knowledge_point_id)

        if template.grammar_point_id:
            used_kp_ids.append(template.grammar_point_id)

        # Build English sentence from template
        english_template = template.metadata.get(
            "english_template", template.prompt_template
        )
        verbs = template.metadata.get("verbs", {})

        # Build format args
        format_args = dict(english_values)

        # Handle verb conjugation for "be"
        if "subject" in english_values and "{be}" in english_template:
            format_args["be"] = _conjugate_be(english_values["subject"])

        # Handle other verbs
        for verb_key, (base, third) in verbs.items():
            if "subject" in english_values:
                is_third = _is_third_person(english_values["subject"])
                format_args[verb_key] = third if is_third else base

        try:
            english_sentence = english_template.format(**format_args)
        except KeyError:
            english_sentence = english_template

        # Build Chinese chunks from template
        chunks_template = template.metadata.get("chunks_template", [])
        chinese_chunks = []

        for chunk in chunks_template:
            if chunk.startswith("{") and chunk.endswith("}"):
                slot_name = chunk[1:-1]
                if slot_name.endswith("_cn"):
                    slot_name = slot_name[:-3]
                chinese_chunks.append(slot_values.get(slot_name, chunk))
            else:
                chinese_chunks.append(chunk)

        if not chinese_chunks:
            return None

        return ReorderExercise(
            id=str(uuid.uuid4()),
            source_ids=used_kp_ids,
            difficulty=0.3,
            prompt=f'Translate: "{english_sentence}"',
            items=chinese_chunks,
            correct_order=list(range(len(chinese_chunks))),
            metadata={
                "template_id": template.id,
                "english_sentence": english_sentence,
                "chinese_chunks": chinese_chunks,
            },
        )
