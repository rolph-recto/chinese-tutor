# Plan: Fancy Terminal UI for Chinese Tutor

## Overview
Enhance the Chinese tutor app's terminal UI from plain text to a polished, colorful interface using the **Rich** library (Python's most popular terminal styling library).

## Current State
- Plain `print()` and `input()` calls
- No colors, styling, or visual hierarchy
- Basic progress information

## Target Features (inspired by opencode's polished look)

### 1. **Startup Screen**
- Styled banner with app title
- Color-coded welcome message
- Session statistics at a glance

### 2. **Exercise Display**
- Colored panels/boxes for exercise content
- Color-coded feedback (green for correct, red for incorrect)
- Progress indicators showing session completion

### 3. **Rating Interface**
- Styled difficulty rating prompt with icons
- Visual hierarchy for options

### 4. **Mastery Updates**
- Formatted table showing knowledge point progress
- Color-coded retrievability percentages
- Progress bar for mastery levels

### 5. **Session Progress**
- Live progress bar during exercises
- Session statistics sidebar

### 6. **Exit/Quit Messages**
- Styled goodbye messages
- Save confirmation with timestamp

## Implementation Plan

### Phase 1: Foundation
1. Add `rich` to dependencies in `pyproject.toml`
2. Create `ui/` module with:
   - `styles.py` - Color schemes and theme configuration
   - `components.py` - Reusable UI components (panels, tables, progress)
   - `app.py` - Main UI orchestrator class

### Phase 2: Core UI Components
1. **Style Configuration** (`ui/styles.py`)
   - Define color palette (Chinese tutor theme - red/gold accents)
   - Create style constants for different message types
   - Theme support (light/dark terminal compatibility)

2. **UI Components** (`ui/components.py`)
   - `Banner` - ASCII art or styled title
   - `ExercisePanel` - Box for displaying exercises
   - `ProgressBar` - Session progress indicator
   - `StatsTable` - Formatted table for mastery data
   - `RatingMenu` - Styled rating selection
   - `FeedbackCard` - Result display with colors

3. **UI Orchestrator** (`ui/app.py`)
   - `TutorUI` class wrapping all Rich components
   - Methods for each screen: `show_welcome()`, `show_exercise()`, `show_feedback()`, etc.
   - State management for progress tracking

### Phase 3: Integration
1. Update `main.py` to use `TutorUI` instead of raw `print()`/`input()`
2. Modify exercise handlers to return styled content
3. Update `prompt_for_rating()` with styled menu
4. Add progress bar to session loop

### Phase 4: Polish
1. Loading animations during exercise generation
2. Keyboard shortcuts (Ctrl+C handling already exists)
3. Configuration file for UI preferences
4. Accessibility (terminal detection, colorblind-friendly options)

## File Changes Summary

```
pyproject.toml           # Add 'rich' dependency
ui/
  __init__.py
  styles.py              # Color palette and styles
  components.py          # Reusable UI components
  app.py                 # Main TutorUI class
main.py                  # Integrate new UI
exercises/               # Optional: enhance exercise presentation
```

## Dependencies to Add

```toml
[project.optional-dependencies]
ui = ["rich>=13.0.0"]
```

## Recommended Color Scheme

| Element | Color | Purpose |
|---------|-------|---------|
| Primary | #E74C3C (Red) | Chinese cultural theme |
| Secondary | #F1C40F (Gold) | Accents and highlights |
| Success | #27AE60 (Green) | Correct answers |
| Error | #C0392B (Dark Red) | Incorrect answers |
| Info | #3498DB (Blue) | General information |
| Muted | #7F8C8D (Gray) | Secondary text |

## Example Transformations

**Before:**
```
What is the English for "你好"?
  A. Hello
  B. Goodbye
  C. Thank you
  D. Please
Enter your choice (A/B/C/D):
```

**After:**
```
┌─────────────────────────────────────────────────────┐
│  Exercise 5/20                                      │
│  Progress: [████░░░░░░░░░░░░░░] 25%                  │
├─────────────────────────────────────────────────────┤
│  What is the English for                            │
│                                                     │
│    [bold cyan]你好[/bold cyan]                              │
│                                                     │
│  [yellow]A.[/yellow] [white]Hello[/white]                                   │
│  [yellow]B.[/yellow] [white]Goodbye[/white]                                 │
│  [yellow]C.[/yellow] [white]Thank you[/white]                               │
│  [yellow]D.[/yellow] [white]Please[/white]                                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```
