"""Chinese language schema populator.

Populates exercise schemas with Chinese-specific knowledge.
This module contains all domain-specific logic for Chinese language tutoring.
"""

from models import KnowledgePoint
from storage import get_cloze_templates_repo, get_minimal_pairs_repo

from .populator import SchemaPopulator
from .schemas import (
    BlankFill,
    BlankOption,
    BlankOptionType,
    BlankTemplate,
    FillBlankSchema,
    MultipleChoiceSchema,
    Option,
    OptionType,
    PromptType,
    PromptValue,
    ReorderSchema,
    ReorderTemplate,
    SlotFill,
)


# Exercise templates for segmented translation (reorder exercises)
# Each template defines:
# - english: English sentence template with slots
# - chunks: Chinese chunks in correct order (slots use {slot_cn} format)
# - slots: Mapping from slot name to vocabulary category
# - grammar_id: Optional associated grammar point
# - verbs: Optional verb conjugation mapping
REORDER_TEMPLATES = [
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
    # Verb + Object (drink)
    {
        "english": "{subject} {drink} {object}",
        "chunks": ["{subject_cn}", "喝", "{object_cn}"],
        "slots": {"subject": "pronoun", "object": "drink"},
        "grammar_id": None,
        "verbs": {"drink": ("drink", "drinks")},
    },
    # Verb + Object (eat)
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


def _get_cluster_tags(kp: KnowledgePoint) -> set[str]:
    """Extract cluster tags from a knowledge point."""
    return {t for t in kp.tags if t.startswith("cluster:")}


def _is_same_cluster(kp1: KnowledgePoint, kp2: KnowledgePoint) -> bool:
    """Check if two knowledge points share a cluster tag."""
    return bool(_get_cluster_tags(kp1) & _get_cluster_tags(kp2))


class ChineseSchemaPopulator(SchemaPopulator):
    """Populates schemas with Chinese language data."""

    def populate_multiple_choice(
        self,
        knowledge_points: list[KnowledgePoint],
    ) -> MultipleChoiceSchema:
        """Populate multiple choice schema from Chinese knowledge points.

        Creates three prompt types:
        - chinese_to_english: Show Chinese, ask for English translation
        - english_to_chinese: Show English, ask for Chinese translation
        - minimal_pair: Show English, ask for correct Chinese character

        Options are categorized as:
        - distractor: Same semantic cluster (harder to distinguish)
        - nondistractor: Different semantic cluster (easier)
        """
        schema = MultipleChoiceSchema()

        vocab_kps = [kp for kp in knowledge_points if kp.type.value == "vocabulary"]

        # Define prompt types
        schema.prompt_types = [
            PromptType(
                id="chinese_to_english",
                template='What is the English for "{value}"?',
                metadata={"direction": "chinese_to_english"},
            ),
            PromptType(
                id="english_to_chinese",
                template='What is the Chinese for "{value}"?',
                metadata={"direction": "english_to_chinese"},
            ),
            PromptType(
                id="minimal_pair",
                template='Select the character for "{value}"',
                metadata={"direction": "minimal_pair"},
            ),
        ]

        # Define option types for each prompt type
        for pt in schema.prompt_types:
            schema.option_types.extend(
                [
                    OptionType(id="distractor", prompt_type_id=pt.id),
                    OptionType(id="nondistractor", prompt_type_id=pt.id),
                ]
            )

        # Populate prompt values and options for each vocab item
        for kp in vocab_kps:
            english_first = kp.english.split(",")[0].strip()

            # Chinese-to-English prompt value
            schema.prompt_values.append(
                PromptValue(
                    prompt_type_id="chinese_to_english",
                    value=kp.chinese,
                    correct_answer=english_first,
                    knowledge_point_id=kp.id,
                    metadata={"pinyin": kp.pinyin, "full_english": kp.english},
                )
            )

            # English-to-Chinese prompt value
            schema.prompt_values.append(
                PromptValue(
                    prompt_type_id="english_to_chinese",
                    value=english_first,
                    correct_answer=f"{kp.chinese} ({kp.pinyin})",
                    knowledge_point_id=kp.id,
                    metadata={"pinyin": kp.pinyin, "chinese": kp.chinese},
                )
            )

            # Generate options for this knowledge point
            for other_kp in vocab_kps:
                if other_kp.id == kp.id:
                    continue

                other_english_first = other_kp.english.split(",")[0].strip()
                is_distractor = _is_same_cluster(kp, other_kp)
                option_type = "distractor" if is_distractor else "nondistractor"

                # Chinese-to-English options (other English translations)
                schema.options.append(
                    Option(
                        prompt_type_id="chinese_to_english",
                        value=kp.chinese,
                        option_type_id=option_type,
                        option_value=other_english_first,
                    )
                )

                # English-to-Chinese options (other Chinese words)
                schema.options.append(
                    Option(
                        prompt_type_id="english_to_chinese",
                        value=english_first,
                        option_type_id=option_type,
                        option_value=f"{other_kp.chinese} ({other_kp.pinyin})",
                    )
                )

        # Handle minimal pairs from database
        minimal_pairs_repo = get_minimal_pairs_repo()
        all_pairs = minimal_pairs_repo.get_all_as_dict()

        for kp in vocab_kps:
            if kp.id not in all_pairs:
                continue

            english_first = kp.english.split(",")[0].strip()

            # Minimal pair prompt value
            schema.prompt_values.append(
                PromptValue(
                    prompt_type_id="minimal_pair",
                    value=english_first,
                    correct_answer=kp.chinese,
                    knowledge_point_id=kp.id,
                    metadata={"pinyin": kp.pinyin},
                )
            )

            # Minimal pair options (from database)
            for distractor in all_pairs[kp.id]:
                schema.options.append(
                    Option(
                        prompt_type_id="minimal_pair",
                        value=english_first,
                        option_type_id="distractor",
                        option_value=distractor["chinese"],
                        metadata={"reason": distractor.get("reason")},
                    )
                )

        return schema

    def populate_fill_blank(
        self,
        knowledge_points: list[KnowledgePoint],
    ) -> FillBlankSchema:
        """Populate fill-blank schema from Chinese knowledge points.

        Uses cloze templates from the database.
        """
        schema = FillBlankSchema()

        vocab_kps = [kp for kp in knowledge_points if kp.type.value == "vocabulary"]
        kp_dict = {kp.id: kp for kp in vocab_kps}

        # Load cloze templates from database
        cloze_repo = get_cloze_templates_repo()
        templates = cloze_repo.get_all()

        for template in templates:
            target_kp = kp_dict.get(template["target_vocab_id"])
            if not target_kp:
                continue

            template_id = template["id"]

            # Add template
            schema.templates.append(
                BlankTemplate(
                    id=template_id,
                    sentence=template["chinese"],
                    context=template["english"],
                    target_position=0,
                )
            )

            # Add fill
            correct_answer = f"{target_kp.chinese} ({target_kp.pinyin})"
            schema.fills.append(
                BlankFill(
                    template_id=template_id,
                    correct_answer=correct_answer,
                    knowledge_point_id=target_kp.id,
                    metadata={
                        "target_word": target_kp.chinese,
                        "target_pinyin": target_kp.pinyin,
                        "target_english": target_kp.english.split(",")[0].strip(),
                    },
                )
            )

            # Add option types
            schema.option_types.extend(
                [
                    BlankOptionType(id="distractor", template_id=template_id),
                    BlankOptionType(id="nondistractor", template_id=template_id),
                ]
            )

            # Generate options
            for other_kp in vocab_kps:
                if other_kp.id == target_kp.id:
                    continue

                is_distractor = _is_same_cluster(target_kp, other_kp)
                option_type = "distractor" if is_distractor else "nondistractor"

                schema.options.append(
                    BlankOption(
                        template_id=template_id,
                        fill_value=correct_answer,
                        option_type_id=option_type,
                        option_value=f"{other_kp.chinese} ({other_kp.pinyin})",
                    )
                )

        return schema

    def populate_reorder(
        self,
        knowledge_points: list[KnowledgePoint],
    ) -> ReorderSchema:
        """Populate reorder schema from Chinese knowledge points.

        Uses predefined templates for Chinese sentence patterns.
        """
        schema = ReorderSchema()
        kp_dict = {kp.id: kp for kp in knowledge_points}

        for i, tmpl in enumerate(REORDER_TEMPLATES):
            template_id = f"reorder_{i}"

            # Determine fixed chunks (chunks that don't start with {)
            fixed_chunks = [c for c in tmpl["chunks"] if not c.startswith("{")]

            schema.templates.append(
                ReorderTemplate(
                    id=template_id,
                    prompt_template=tmpl["english"],
                    slot_types=list(tmpl["slots"].keys()),
                    fixed_chunks=fixed_chunks,
                    chunk_order=list(range(len(tmpl["chunks"]))),
                    grammar_point_id=tmpl.get("grammar_id"),
                    metadata={
                        "english_template": tmpl["english"],
                        "chunks_template": tmpl["chunks"],
                        "verbs": tmpl.get("verbs", {}),
                    },
                )
            )

            # Populate slot fills from vocab categories
            for slot_type, category in tmpl["slots"].items():
                vocab_ids = VOCAB_CATEGORIES.get(category, [])
                for vid in vocab_ids:
                    kp = kp_dict.get(vid)
                    if kp:
                        schema.slot_fills.append(
                            SlotFill(
                                template_id=template_id,
                                slot_type=slot_type,
                                slot_value=kp.chinese,
                                english_value=kp.english.split(",")[0].strip(),
                                knowledge_point_id=kp.id,
                            )
                        )

        return schema
