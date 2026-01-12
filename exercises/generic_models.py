"""Generic, domain-agnostic exercise models.

These models define reusable exercise patterns that know nothing about
the specific domain (e.g., Chinese language learning). They can be used
for any application that needs "present info -> get input -> check correctness".
"""

from typing import Any

from pydantic import BaseModel, Field


class GenericExercise(BaseModel):
    """Base class for all generic exercises."""

    id: str
    source_ids: list[str]  # IDs for mastery tracking (domain-agnostic)
    difficulty: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)  # Domain-specific data


class MultipleChoiceExercise(GenericExercise):
    """Generic multiple choice: pick one option from a list.

    Covers exercise patterns like:
    - Translation (source language -> target language)
    - Vocabulary matching
    - Discrimination between similar items
    """

    prompt: str  # Main question text
    prompt_secondary: str = ""  # Optional hint (e.g., pronunciation)
    options: list[str]  # Answer choices
    correct_index: int  # Index of correct answer


class FillBlankExercise(GenericExercise):
    """Generic fill-in-blank: select word to complete a sentence.

    Covers exercise patterns like:
    - Cloze deletion
    - Sentence completion
    """

    sentence: str  # Sentence with blank marker (e.g., "The _____ is red")
    context: str = ""  # Optional context/hint text
    options: list[str]  # Answer choices
    correct_index: int  # Index of correct answer


class ReorderExercise(GenericExercise):
    """Generic reorder: arrange items in correct sequence.

    Covers exercise patterns like:
    - Sentence construction from fragments
    - Step ordering
    """

    prompt: str  # Instruction text
    items: list[str]  # Items to reorder (displayed shuffled by handler)
    correct_order: list[int]  # Indices representing correct sequence
