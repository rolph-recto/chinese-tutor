"""Exercise handlers for the Chinese tutor application.

This package provides generic exercise types, declarative schemas, and
a Chinese-specific adapter.

Architecture:
- Schema models define "database tables" that adapters populate
- Populators transform domain knowledge into schemas (declarative)
- Generators consume schemas to produce exercises (procedural)
- Adapters provide high-level interface wrapping populators and generators

Generic exercise models:
- MultipleChoiceExercise: Pick one option from a list
- FillBlankExercise: Select word to complete a sentence
- ReorderExercise: Arrange items in correct sequence

Generic handlers:
- MultipleChoiceHandler: Handles multiple choice exercises
- FillBlankHandler: Handles fill-in-blank exercises
- ReorderHandler: Handles reorder exercises

Schema models:
- MultipleChoiceSchema, FillBlankSchema, ReorderSchema

Configuration:
- ExerciseGeneratorConfig: Configure exercise generation behavior

Generators:
- MultipleChoiceGenerator, FillBlankGenerator, ReorderGenerator

Chinese adapter:
- ChineseExerciseAdapter: Transforms Chinese knowledge points to generic exercises
- ChineseSchemaPopulator: Populates schemas with Chinese-specific data
"""

from exercises.base import parse_letter_input, select_distractors
from exercises.chinese_adapter import ChineseExerciseAdapter
from exercises.chinese_populator import ChineseSchemaPopulator
from exercises.config import (
    ExerciseGeneratorConfig,
    FillBlankConfig,
    MultipleChoiceConfig,
    ReorderConfig,
)
from exercises.generators import (
    ExerciseGenerator,
    FillBlankGenerator,
    MultipleChoiceGenerator,
    ReorderGenerator,
)
from exercises.generic_handlers import (
    FillBlankHandler,
    GenericExerciseHandler,
    MultipleChoiceHandler,
    ReorderHandler,
)
from exercises.generic_models import (
    FillBlankExercise,
    GenericExercise,
    MultipleChoiceExercise,
    ReorderExercise,
)
from exercises.populator import SchemaPopulator
from exercises.schemas import (
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

__all__ = [
    # Utilities
    "parse_letter_input",
    "select_distractors",
    # Generic models
    "GenericExercise",
    "MultipleChoiceExercise",
    "FillBlankExercise",
    "ReorderExercise",
    # Generic handlers
    "GenericExerciseHandler",
    "MultipleChoiceHandler",
    "FillBlankHandler",
    "ReorderHandler",
    # Schema models
    "MultipleChoiceSchema",
    "PromptType",
    "PromptValue",
    "OptionType",
    "Option",
    "FillBlankSchema",
    "BlankTemplate",
    "BlankFill",
    "BlankOptionType",
    "BlankOption",
    "ReorderSchema",
    "ReorderTemplate",
    "SlotFill",
    # Configuration
    "ExerciseGeneratorConfig",
    "MultipleChoiceConfig",
    "FillBlankConfig",
    "ReorderConfig",
    # Abstract classes
    "SchemaPopulator",
    "ExerciseGenerator",
    # Generators
    "MultipleChoiceGenerator",
    "FillBlankGenerator",
    "ReorderGenerator",
    # Chinese adapter
    "ChineseExerciseAdapter",
    "ChineseSchemaPopulator",
]
