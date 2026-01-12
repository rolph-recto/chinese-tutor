"""Configuration for exercise generation.

These configuration models allow users to tune exercise generation behavior,
such as the number of distractors, whether to shuffle options, etc.
"""

from pydantic import BaseModel, Field


class MultipleChoiceConfig(BaseModel):
    """Configuration for multiple choice generation."""

    total_options: int = Field(default=4, ge=2, le=6)
    min_distractors: int = Field(default=1, ge=0)
    max_distractors: int = Field(default=3, ge=0)
    shuffle_options: bool = True


class FillBlankConfig(BaseModel):
    """Configuration for fill-blank generation."""

    total_options: int = Field(default=4, ge=2, le=6)
    min_distractors: int = Field(default=1, ge=0)
    shuffle_options: bool = True


class ReorderConfig(BaseModel):
    """Configuration for reorder generation."""

    shuffle_chunks: bool = True


class ExerciseGeneratorConfig(BaseModel):
    """Master configuration for all exercise types."""

    multiple_choice: MultipleChoiceConfig = Field(default_factory=MultipleChoiceConfig)
    fill_blank: FillBlankConfig = Field(default_factory=FillBlankConfig)
    reorder: ReorderConfig = Field(default_factory=ReorderConfig)
