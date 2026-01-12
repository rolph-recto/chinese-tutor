Currently, @exercises/chinese_adapter.py is used to convert target knowledge
points directly into exercise types. The problem with this setup is that this
adapter is not "declarative" enough; it effectively makes choices about the
exercise that will be generated, and this procedural, non-declarative logic
will be duplicated for all adapters. For example, the adapter currently chooses
the options that will go into a multiple choice question.

Instead, what we want is to keep the adapters "declarative" and factor out this
procedural logic, putting it instead into the exercise types directly.
The current interface of the adapters take in a target knowledge point plus other
information about knowledge points in general and generate an exercise of the
appropriate type. This should be changed such that for each exercise type
the adapter "queries" the input database of Chinese language knowledge points
and returns a new database (i.e. set of tables) that follows a generic schema
for that exercise type. The exercise type then contains the logic to use
database to generate possible exercises for a particular knowledge point.

For example, I think this is what should be the generic database schema
returned by the adapter for the multiple choice exercise type:

- A table of prompt types; each prompt type should have an associated prompt template
    - for the Chinese language database, this table should have two rows:
        [Chinese-to-English, "What is the English for {chinese-word}?"]
        [English-to-Chinese, "What is the Chinese for {english-definition}?"]

- A table of possible values for each prompt type, the correct answer for the value, and the associated knowledge point for each value
    - for the Chinese language database, at least the following rows should be in this table:
        [Chinese-to-English, "朋友", "friend", the knowledge point for "朋友"]
        [English-to-Chinese, "friend", "朋友", the knowledge point for "朋友"]

- A table of possible option types for each prompt type
    - for the Chinese language database, at least the following rows should be in this table:
        [Chinese-to-English, distractor]
        [Chinese-to-English, nondistractor]
        [English-to-Chinese, distractor]
        [English-to-Chinese, nondistractor]

- A table of possible options for each prompt type and value pair.
    - for the Chinese language database, at least the following rows should be in this table.
      Note that for "朋友", "学生" and "老师" are considered distractors because
      they are all people words, while "好" is not because it is an adjective.
        [English-to-Chinese, "friend", distractor, "学生"]
        [English-to-Chinese, "friend", distractor, "老师"]
        [English-to-Chinese, "friend", nondistractor, "好"]

Note that the multiple choice exercise type can then be configured by
the user to tune the possible exercises. For example, the user can specify
that there should be at least 1 distractor option generated per multiple choice
exercise.

# Plan: Declarative Exercise Adapter Architecture (by Claude)

## Overview

Refactor the exercise generation system so that adapters are **declarative** (return database schemas describing possible exercises) rather than **procedural** (directly generate exercises). Exercise generators consume these schemas and contain the procedural logic.

**Current flow:**
```
KnowledgePoint → ChineseExerciseAdapter.create_*() → Exercise
                 (procedural logic embedded)
```

**New flow:**
```
KnowledgePoint → ChineseSchemaPopulator.populate() → Schema (tables)
                                                          ↓
                 ExerciseGenerator.generate(schema, config) → Exercise
                 (procedural logic here)
```

## Files to Create

### 1. `exercises/schemas.py` - Schema Data Models

Defines the "database tables" that adapters populate:

**For Multiple Choice:**
- `PromptType`: id, template (e.g., "What is the English for {value}?")
- `PromptValue`: prompt_type_id, value, correct_answer, knowledge_point_id
- `OptionType`: id, prompt_type_id (e.g., "distractor", "nondistractor")
- `Option`: prompt_type_id, value, option_type_id, option_value
- `MultipleChoiceSchema`: container for all 4 tables

**For Fill-Blank:**
- `BlankTemplate`: id, sentence (with `_____`), context
- `BlankFill`: template_id, correct_answer, knowledge_point_id
- `BlankOptionType`: id, template_id
- `BlankOption`: template_id, fill_value, option_type_id, option_value
- `FillBlankSchema`: container for all tables

**For Reorder:**
- `ReorderTemplate`: id, prompt_template, slot_types, fixed_chunks, chunk_order
- `SlotFill`: template_id, slot_type, slot_value, english_value, knowledge_point_id
- `ReorderSchema`: container for both tables

### 2. `exercises/config.py` - Generation Configuration

```python
class MultipleChoiceConfig:
    total_options: int = 4
    min_distractors: int = 1
    max_distractors: int = 3
    shuffle_options: bool = True

class FillBlankConfig:
    total_options: int = 4
    min_distractors: int = 1
    shuffle_options: bool = True

class ReorderConfig:
    shuffle_chunks: bool = True

class ExerciseGeneratorConfig:
    multiple_choice: MultipleChoiceConfig
    fill_blank: FillBlankConfig
    reorder: ReorderConfig
```

### 3. `exercises/populator.py` - Abstract Interface

```python
class SchemaPopulator(ABC):
    @abstractmethod
    def populate_multiple_choice(self, kps: list[KnowledgePoint]) -> MultipleChoiceSchema

    @abstractmethod
    def populate_fill_blank(self, kps: list[KnowledgePoint]) -> FillBlankSchema

    @abstractmethod
    def populate_reorder(self, kps: list[KnowledgePoint]) -> ReorderSchema
```

### 4. `exercises/chinese_populator.py` - Chinese Implementation

Implements `SchemaPopulator` with Chinese-specific logic:

- Defines prompt types: `chinese_to_english`, `english_to_chinese`, `minimal_pair`
- Populates prompt values from vocabulary knowledge points
- Categorizes options as "distractor" (same cluster) or "nondistractor" (different cluster) based on tags
- Integrates with `MinimalPairsRepository` and `ClozeTemplatesRepository`
- Moves `TEMPLATES` and `VOCAB_CATEGORIES` constants from current adapter

### 5. `exercises/generators.py` - Exercise Generators

```python
class MultipleChoiceGenerator:
    def __init__(self, schema: MultipleChoiceSchema, config: MultipleChoiceConfig)
    def generate(self, target_kp_id: str | None, prompt_type_id: str | None) -> MultipleChoiceExercise | None
    def can_generate(self, target_kp_id: str | None) -> bool

class FillBlankGenerator:
    def __init__(self, schema: FillBlankSchema, config: FillBlankConfig)
    def generate(self, target_kp_id: str | None) -> FillBlankExercise | None

class ReorderGenerator:
    def __init__(self, schema: ReorderSchema, config: ReorderConfig)
    def generate(self, target_kp_id: str | None) -> ReorderExercise | None
```

Generation logic:
1. Select prompt value (optionally filtered by target KP and prompt type)
2. Gather available options, separated by type (distractor vs nondistractor)
3. Select options based on config (e.g., at least 1 distractor)
4. Shuffle and build final exercise

## Files to Modify

### 6. `exercises/chinese_adapter.py` - Refactor to Use New Architecture

Maintain backward-compatible interface but use new internals:

```python
class ChineseExerciseAdapter:
    def __init__(self, knowledge_points, config=None):
        populator = ChineseSchemaPopulator()
        self._mc_schema = populator.populate_multiple_choice(knowledge_points)
        self._fb_schema = populator.populate_fill_blank(knowledge_points)
        self._reorder_schema = populator.populate_reorder(knowledge_points)

        self._mc_generator = MultipleChoiceGenerator(self._mc_schema, config.multiple_choice)
        self._fb_generator = FillBlankGenerator(self._fb_schema, config.fill_blank)
        self._reorder_generator = ReorderGenerator(self._reorder_schema, config.reorder)

    def create_chinese_to_english(self, target_kp=None):
        return self._mc_generator.generate(target_kp.id, "chinese_to_english")

    # ... other methods delegate to generators
```

### 7. `exercises/__init__.py` - Update Exports

Add new modules to exports.

## Files Unchanged

- `exercises/generic_models.py` - Exercise models stay the same
- `exercises/generic_handlers.py` - Handlers stay the same
- `main.py` - Uses adapter interface (unchanged)
- `storage/` - No changes needed

## Implementation Order

### Phase 1: Foundation
1. Create `exercises/schemas.py`
2. Create `exercises/config.py`
3. Create `exercises/populator.py`
4. Add tests for schema models

### Phase 2: Chinese Populator
5. Create `exercises/chinese_populator.py`
6. Add tests verifying schema matches expected structure
7. Verify distractor categorization matches current cluster logic

### Phase 3: Generators
8. Create `exercises/generators.py`
9. Add tests for each generator
10. Test config options (min/max distractors, shuffling)

### Phase 4: Integration
11. Refactor `exercises/chinese_adapter.py`
12. Run existing test suite to verify backward compatibility
13. Update `exercises/__init__.py`

### Phase 5: Cleanup
14. Remove duplicated logic
15. Deprecate `exercises/base.py:select_distractors` (logic now in populator)

## Verification

1. Run existing tests: `uv run pytest -v`
2. Run linter: `uvx ruff check --fix`
3. Run formatter: `uvx ruff format`
4. Manual testing: Run `uv run python main.py` and verify all exercise types work

## Example: Chinese Multiple Choice Schema

After population, the schema would contain:

**prompt_types:**
| id | template |
|----|----------|
| chinese_to_english | What is the English for "{value}"? |
| english_to_chinese | What is the Chinese for "{value}"? |
| minimal_pair | Select the character for "{value}" |

**prompt_values (partial):**
| prompt_type_id | value | correct_answer | knowledge_point_id |
|----------------|-------|----------------|-------------------|
| chinese_to_english | 朋友 | friend | v009 |
| english_to_chinese | friend | 朋友 (péngyou) | v009 |

**option_types:**
| id | prompt_type_id |
|----|----------------|
| distractor | chinese_to_english |
| nondistractor | chinese_to_english |
| distractor | english_to_chinese |
| nondistractor | english_to_chinese |

**options (partial for 朋友):**
| prompt_type_id | value | option_type_id | option_value |
|----------------|-------|----------------|--------------|
| english_to_chinese | friend | distractor | 学生 (xuéshēng) |
| english_to_chinese | friend | distractor | 老师 (lǎoshī) |
| english_to_chinese | friend | nondistractor | 好 (hǎo) |
