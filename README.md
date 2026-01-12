# Chinese Tutor

![test workflow](https://github.com/rolph-recto/chinese-tutor/actions/workflows/main.yml/badge.svg)

This is an Chinese tutoring system with spaced repetition.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the tutoring system
uv run python main.py
```

## Core Components

- **models.py** - Pydantic data models for knowledge points, exercises, student mastery, and FSRS scheduling
- **scheduler.py** - Selects next knowledge point based on review urgency, frontier expansion, and interleaving
- **main.py** - Interactive CLI loop that orchestrates exercise selection, presentation, and mastery updates
- **simulate.py** - Simulator for testing scheduling algorithms
- **simulator_models.py** - Additional models for simulation

## Terminal UI (ui/)

The application uses the [rich](https://github.com/Textualize/rich) library for a styled terminal interface.

- **app.py** - `TutorUI` class that orchestrates UI components and handles user input
- **components.py** - Rich-based UI components:
  - `ExercisePanel` - Displays exercises with progress bar and options
  - `FeedbackPanel` - Shows correct/incorrect feedback with styling
  - `RatingMenu` - Difficulty rating selection (1-4 FSRS scale)
  - `MasteryTable` - Displays mastery updates after exercises
  - `WelcomeScreen` - Welcome banner with session stats
  - `ProgressTracker` - Tracks and displays session progress
- **styles.py** - Color scheme and style definitions (Chinese red/gold theme)

## Exercise Types (exercises/)

All exercises use a generic architecture with Chinese-specific adapters:

### Generic Models
- **generic_models.py** - Base exercise types:
  - `MultipleChoiceExercise` - Pick one option from a list
  - `FillBlankExercise` - Select word to complete a sentence
  - `ReorderExercise` - Arrange items in correct sequence

### Generic Handlers
- **generic_handlers.py** - Exercise handlers that process user input and generate feedback

### Chinese Adapter
- **chinese_adapter.py** - Transforms Chinese knowledge points into generic exercises:
  - `create_chinese_to_english()` - Pick the correct English translation for a Chinese word
  - `create_english_to_chinese()` - Pick the correct Chinese word for an English translation
  - `create_minimal_pair()` - Multiple choice discrimination for visually/phonetically similar characters
  - `create_cloze_deletion()` - Fill-in-blank sentence completion
  - `create_segmented_translation()` - English sentence → reorder Chinese chunks (template-based)

### Utilities
- **base.py** - Shared utilities for input parsing and distractor selection

## Storage Layer (storage/)

Repository pattern with SQLite backend for data persistence:

### Abstract Interfaces
- **base.py** - Repository interfaces:
  - `KnowledgePointRepository` - Knowledge point CRUD operations
  - `StudentStateRepository` - Student mastery state operations
  - `MinimalPairsRepository` - Minimal pair distractor data
  - `ClozeTemplatesRepository` - Cloze template data

### SQLite Implementation
- **sqlite.py** - SQLite repository implementations
- **connection.py** - Database connection and schema initialization

### Factory Functions
- **__init__.py** - Repository factory functions for easy access

## State Persistence

Student progress and application data are stored in `data/tutor.db` (SQLite database).

## Scheduling Algorithm

The system uses the FSRS spaced repetition algorithm to schedule exercises,
as implemented in the [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
library.
