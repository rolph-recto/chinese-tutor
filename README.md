# Chinese Tutor

![test workflow](https://github.com/rolph-recto/chinese-tutor/actions/workflows/main.yml/badge.svg)

Chinese tutoring system with spaced repetition.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the tutoring system (interactive CLI)
uv run python main.py

# Run the student simulator
uv run python main.py simulate

# Run tests
uv run pytest -v

# Run linter with auto-fix
uvx ruff check --fix

# Run formatter
uvx ruff format
```

## Core Components

- `models.py` - Pydantic data models for knowledge points, exercises, student mastery, and FSRS scheduling
- `scheduler.py` - Selects next knowledge point based on review urgency, frontier expansion, and interleaving
- `main.py` - Interactive CLI loop that orchestrates exercise selection, presentation, and mastery updates
- `simulate.py` and  - Student simulator for testing scheduling algorithms
- `simulator_models.py` - Models for the simulator

## Terminal UI (ui/)

The application uses the [rich](https://github.com/Textualize/rich) library for a styled terminal interface.

- UI components (`components.py`)
  - **ExercisePanel** - Displays exercises with progress bar and options
  - **FeedbackPanel** - Shows correct/incorrect feedback with styling
  - **RatingMenu** - Difficulty rating selection (1-4 FSRS scale)
  - **MasteryTable** - Displays mastery updates after exercises
  - **WelcomeScreen** - Welcome banner with session stats
  - **ProgressTracker** - Tracks and displays session progress
- `app.py` - `TutorUI` class that orchestrates UI components and handles user input
- `styles.py` - Color scheme and style definitions (Chinese red/gold theme)

## Exercise Types (exercises/)

Exercises are designed to be reusable templates that don't care about the
specific subject. To make it work:

- A _populator_ acts as a bridge, taking specific info (like Chinese
  vocabulary) and formatting it to fit a template.

- A _generator_ handles the procedural logic to generate exercises.

The populator stays simple--—it just delivers the data without needing to know
how the actual exercise is built.

For the Chinese language knowledge base, the flow looks like:
```
KnowledgePoint → ChineseSchemaPopulator.populate() → Schema (tables)
                                                          ↓
                 ExerciseGenerator.generate(schema, config) → Exercise
                 (procedural logic here)
```

**Exercise types** (`generic_models.py`)
  - `MultipleChoiceExercise` - pick one option from a list
  - `FillBlankExercise` - select word to complete a sentence
  - `ReorderExercise` - arrange items in correct sequence

**Schemas** (`schemas.py`)- schema for generic databases used to generate exercises
   - `MultipleChoiceSchema` - Prompt types, values, options for multiple choice
   - `FillBlankSchema` - Templates, fills, options for fill-in-blank
   - `ReorderSchema` - Templates, slot fills for reordering exercises

**Populators** (`populator.py`) - transforms domain knowledge into schemas
   - `chinese_populator.py` - `ChineseSchemaPopulator` for Chinese vocabulary/grammar

**Exercise Generators** (`generators.py`) - consume generic databases to produce exercises:
   - `MultipleChoiceGenerator` - generates `MultipleChoiceExercise`
   - `FillBlankGenerator` - generates `FillBlankExercise`
   - `ReorderGenerator` - generates `ReorderExercise`

**Configuration** (`config.py`) - configure exercise generation behavior
   - `MultipleChoiceConfig` - configure `MultipleChoiceGenerator`
   - `FillBlankConfig` - configure `FillBlankGenerator`
   - `ReorderConfig` - configure `ReorderGenerator`

## Storage Layer (storage/)

Student progress and application data are stored in `data/tutor.db` (SQLite database).

### Abstract Interfaces
- Repository interfaces (`base.py`)
  - **KnowledgePointRepository** - Knowledge point CRUD operations
  - **StudentStateRepository** - Student mastery state operations
  - **MinimalPairsRepository** - Minimal pair distractor data
  - **ClozeTemplatesRepository** - Cloze template data

### SQLite Implementation
- `sqlite.py` - SQLite repository implementations
- `connection.py` - Database connection and schema initialization

## Scheduling Algorithm

The system uses the FSRS spaced repetition algorithm to schedule exercises,
as implemented in the [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
library.

