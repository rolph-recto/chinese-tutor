# Chinese Tutor

This is an intelligent Chinese tutoring system using Bayesian Knowledge Tracing (BKT).

## Development Commands

```bash
# Install dependencies
uv sync

# Run the tutoring system
uv run python main.py
```

## Core Components

- **models.py** - Pydantic data models for knowledge points, exercises, and student mastery state
- **bkt.py** - Bayesian Knowledge Tracing implementation for updating mastery probabilities
- **scheduler.py** - Selects next knowledge point based on review urgency, frontier expansion, and interleaving
- **main.py** - Interactive CLI loop that orchestrates exercise selection, presentation, and mastery updates

## Exercise Types (exercises/)

- **segmented_translation.py** - English sentence → reorder Chinese chunks (template-based)
- **minimal_pair.py** - Multiple choice discrimination for visually/phonetically similar characters

## Data Files (data/)

- **vocabulary.json** - HSK1 vocabulary items with Chinese, pinyin, English, HSK level
- **grammar.json** - HSK1 grammar patterns with structure templates
- **minimal_pairs.json** - Phonetic/visual distractor mappings for vocabulary

## State Persistence

Student progress is stored in `student_state.json` in the project root.

## Scheduling Algorithm

The scheduler balances three factors:
1. **Review urgency** (70% weight) - prioritizes items with lower mastery
2. **Frontier expansion** (30% weight) - introduces new items when prerequisites are met
3. **Interleaving bonus** - alternates between vocabulary and grammar

Key constants in scheduler.py:
- MASTERY_THRESHOLD = 0.8
- DECAY_RATE_PER_WEEK = 0.05
