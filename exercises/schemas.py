"""Declarative schemas for exercise generation.

These models define the 'database' structure that adapters populate
and exercise generators consume. This separates domain-specific knowledge
(what exercises are possible) from exercise generation logic (how to
build exercises from the schema).
"""

from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Multiple Choice Schema
# =============================================================================


class PromptType(BaseModel):
    """Defines a type of prompt with its template.

    Examples:
        - id="chinese_to_english", template='What is the English for "{value}"?'
        - id="english_to_chinese", template='What is the Chinese for "{value}"?'
    """

    id: str
    template: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptValue(BaseModel):
    """A specific value that can be prompted, with its correct answer.

    Examples:
        - prompt_type_id="chinese_to_english", value="朋友", correct_answer="friend"
        - prompt_type_id="english_to_chinese", value="friend", correct_answer="朋友 (péngyou)"
    """

    prompt_type_id: str
    value: str
    correct_answer: str
    knowledge_point_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptionType(BaseModel):
    """Defines a category of options for a prompt type.

    Examples:
        - id="distractor", prompt_type_id="chinese_to_english"
          (options from the same semantic cluster)
        - id="nondistractor", prompt_type_id="chinese_to_english"
          (options from different semantic clusters)
    """

    id: str
    prompt_type_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Option(BaseModel):
    """A possible option for a specific prompt value.

    Examples:
        For prompt value="friend" (English-to-Chinese):
        - option_type_id="distractor", option_value="学生" (same cluster: people)
        - option_type_id="nondistractor", option_value="好" (different cluster: adjective)
    """

    prompt_type_id: str
    value: str  # The prompt value this option belongs to
    option_type_id: str
    option_value: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultipleChoiceSchema(BaseModel):
    """Complete schema for multiple choice exercise generation.

    Contains four "tables":
    - prompt_types: Types of prompts with templates
    - prompt_values: Specific values that can be prompted
    - option_types: Categories of options (distractor vs non-distractor)
    - options: All possible options for each prompt value
    """

    prompt_types: list[PromptType] = Field(default_factory=list)
    prompt_values: list[PromptValue] = Field(default_factory=list)
    option_types: list[OptionType] = Field(default_factory=list)
    options: list[Option] = Field(default_factory=list)


# =============================================================================
# Fill-in-Blank Schema
# =============================================================================


class BlankTemplate(BaseModel):
    """A sentence template with a blank to fill.

    Examples:
        - sentence="_____ 是学生。", context="_____ is a student."
    """

    id: str
    sentence: str  # Sentence with _____ marker
    context: str = ""  # Optional context/hint (e.g., English translation)
    target_position: int = 0  # Which blank (for multi-blank templates)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BlankFill(BaseModel):
    """A specific fill value for a blank template.

    Examples:
        - template_id="t001", correct_answer="我 (wǒ)", knowledge_point_id="v001"
    """

    template_id: str
    correct_answer: str
    knowledge_point_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BlankOptionType(BaseModel):
    """Option type for fill-blank exercises."""

    id: str
    template_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BlankOption(BaseModel):
    """Possible fill options for a blank."""

    template_id: str
    fill_value: str  # The correct answer this option is for
    option_type_id: str
    option_value: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FillBlankSchema(BaseModel):
    """Complete schema for fill-blank exercise generation.

    Contains four "tables":
    - templates: Sentence templates with blanks
    - fills: Correct fill values for each template
    - option_types: Categories of options
    - options: All possible options for each fill
    """

    templates: list[BlankTemplate] = Field(default_factory=list)
    fills: list[BlankFill] = Field(default_factory=list)
    option_types: list[BlankOptionType] = Field(default_factory=list)
    options: list[BlankOption] = Field(default_factory=list)


# =============================================================================
# Reorder Schema
# =============================================================================


class ReorderTemplate(BaseModel):
    """A template for reorder exercises.

    Examples:
        - prompt_template='Translate: "{subject} is a {noun}"'
        - slot_types=["subject", "noun"]
        - fixed_chunks=["是"] (chunks that don't vary)
        - chunk_order=[0, 1, 2] (correct order of all chunks)
    """

    id: str
    prompt_template: str
    slot_types: list[str] = Field(default_factory=list)
    fixed_chunks: list[str] = Field(default_factory=list)
    chunk_order: list[int] = Field(default_factory=list)
    grammar_point_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SlotFill(BaseModel):
    """A possible fill for a slot in a reorder template.

    Examples:
        - slot_type="subject", slot_value="我", english_value="I"
        - slot_type="noun", slot_value="学生", english_value="student"
    """

    template_id: str
    slot_type: str
    slot_value: str  # Chinese chunk
    english_value: str  # For prompt generation
    knowledge_point_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReorderSchema(BaseModel):
    """Complete schema for reorder exercise generation.

    Contains two "tables":
    - templates: Reorder templates with slot definitions
    - slot_fills: Possible fills for each slot type
    """

    templates: list[ReorderTemplate] = Field(default_factory=list)
    slot_fills: list[SlotFill] = Field(default_factory=list)
