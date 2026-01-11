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

- **models.py** - Pydantic data models for knowledge points, exercises, and student mastery state
- **scheduler.py** - Selects next knowledge point based on review urgency, frontier expansion, and interleaving
- **main.py** - Interactive CLI loop that orchestrates exercise selection, presentation, and mastery updates
- **simulate.py** - Simulator

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

- **segmented_translation.py** - English sentence → reorder Chinese chunks (template-based)
- **minimal_pair.py** - Multiple choice discrimination for visually/phonetically similar characters
- **chinese_to_english.py** - Pick the correct English translation for a Chinese word
- **english_to_chinese.py** - Pick the correct Chinese word for an English translation

## Data Files (data/)

- **vocabulary.json** - Vocabulary items with Chinese, pinyin, English, HSK level
- **grammar.json** - Grammar patterns with structure templates
- **minimal_pairs.json** - Phonetic/visual distractor mappings for vocabulary

## State Persistence

Student progress is stored in `student_state.json` in the project root.

## Scheduling Algorithm

The system uses the FSRS spaced repetition algorithm to schedule exercises,
as implemented in the [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
library.
