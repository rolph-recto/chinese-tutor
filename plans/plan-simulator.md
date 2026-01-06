# Student Simulator Implementation Plan

## Overview
Create a `simulate` subcommand for `main.py` that models a student's learning trajectory over time, generating statistics about exercises, performance, and BKT/FSRS parameter trajectories.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `simulator_models.py` | **Create** | Data models for simulation |
| `simulate.py` | **Create** | Core simulation logic |
| `main.py` | **Modify** | Add CLI subcommand routing |

## CLI Interface

```bash
# Run simulation with defaults (30 days, 10 exercises/day)
uv run python main.py simulate

# Configure simulation parameters
uv run python main.py simulate --days 60 --exercises-per-day 15

# Configure student behavior
uv run python main.py simulate \
  --learning-rate 0.4 \      # How fast student learns (0.0-1.0, default: 0.3)
  --retention-rate 0.9 \     # Memory retention (0.0-1.0, default: 0.85)
  --slip-rate 0.05 \         # Error rate when knowing (0.0-0.5, default: 0.1)
  --guess-rate 0.2           # Correct guess rate (0.0-0.5, default: 0.25)

# Output options
uv run python main.py simulate --output results.json --verbose --seed 42
```

## Implementation Steps

### Step 1: Create `simulator_models.py`

Define Pydantic models:

1. **SimulatedStudentConfig** - Configurable student parameters
   - `learning_rate`, `retention_rate`, `slip_rate`, `guess_rate`

2. **SimulatedStudent** - Tracks "true" knowledge state
   - `true_knowledge: dict[str, float]` - Ground truth per KP
   - `first_encounter: dict[str, datetime]` - When each KP first seen
   - Methods: `get_true_knowledge()`, `update_true_knowledge()`, `apply_forgetting()`

3. **ExerciseResult** - Single exercise outcome
   - timestamp, day, exercise_number, exercise_type, is_correct
   - `true_knowledge_before/after`, `bkt_p_known_before/after`
   - `scheduling_modes` per KP

4. **DailySummary** - Aggregated daily stats
   - total_exercises, correct_count, accuracy
   - exercise type breakdown (segmented_translation vs minimal_pair)
   - kps_practiced, kps_transitioned_to_fsrs
   - avg_true_knowledge, avg_bkt_p_known

5. **KnowledgePointSnapshot/Trajectory** - Per-KP progression
   - Snapshots: true_knowledge, bkt_p_known, scheduling_mode, practice_count
   - FSRS state when applicable (stability, difficulty)

6. **SimulationResults** - Complete output
   - config, simulation params, summary stats
   - daily_summaries, exercise_results, kp_trajectories

### Step 2: Create `simulate.py`

Core classes:

1. **ResponseGenerator** - Generates simulated student responses
   ```python
   def generate_response(self, exercise: Exercise) -> bool:
       # Calculate P(correct) based on:
       # - Average true knowledge of exercise KPs
       # - Exercise difficulty
       # - Slip/guess rates
       p_correct = effective_knowledge * (1 - slip_rate) + (1 - effective_knowledge) * guess_rate
       return random.random() < p_correct
   ```

2. **Simulator** - Main orchestrator
   - `run(days, exercises_per_day)` - Main entry point
   - `_simulate_day()` - Run one day of exercises
   - `_generate_exercise()` - Create exercise (reuses existing generators)
   - `_process_exercise_result()` - Update BKT/FSRS + true knowledge
   - `_apply_daily_forgetting()` - Apply retention decay
   - `_record_kp_snapshots()` - Track trajectories

3. **Output functions**
   - `print_console_summary()` - Formatted terminal output
   - `save_json_results()` - JSON export

### Step 3: Modify `main.py`

1. Add `argparse` with subcommands:
   - Default: `interactive` (existing behavior)
   - New: `simulate` with all CLI flags

2. Refactor existing `main()` into `run_interactive()`

3. Add `run_simulation(args)` function that:
   - Creates SimulatedStudentConfig from args
   - Loads knowledge points
   - Runs simulation
   - Prints summary and saves JSON

## Output Format

### Console Summary
```
================================================================================
                        SIMULATION COMPLETE
================================================================================

Configuration:
  Days simulated:     30
  Exercises per day:  10
  Total exercises:    300

Student Parameters:
  Learning rate:      0.30
  Retention rate:     0.85

================================================================================
                        OVERALL RESULTS
================================================================================

Total correct:        237 / 300 (79.0%)

By exercise type:
  Segmented Translation:  142 / 178 (79.8%)
  Minimal Pairs:           95 / 122 (77.9%)

Knowledge Points:
  Total KPs encountered:     20
  KPs mastered (p >= 0.8):   12
  KPs in FSRS mode:           8

================================================================================
                        DAILY BREAKDOWN
================================================================================

Day   Exercises  Correct  Accuracy  FSRS Transitions
----  ---------  -------  --------  ----------------
  1        10        6     60.0%            0
  2        10        7     70.0%            0
 ...

================================================================================
                        BKT vs TRUE KNOWLEDGE
================================================================================

KP ID   Chinese   True Knowledge   BKT p_known   Mode    Practices
------  -------   --------------   -----------   -----   ---------
v001    我        0.92             0.88          FSRS    15
...

Results saved to: simulation_results.json
```

### JSON Structure
```json
{
  "config": { "learning_rate": 0.3, ... },
  "simulation_params": { "days_simulated": 30, ... },
  "summary": {
    "total_exercises": 300,
    "overall_accuracy": 0.79,
    "exercise_type_breakdown": { ... },
    "knowledge_points": { "mastered": 12, "in_fsrs_mode": 8 }
  },
  "daily_summaries": [ ... ],
  "kp_trajectories": { "v001": { "snapshots": [ ... ] } },
  "exercise_log": [ ... ]
}
```

## Key Design Decisions

1. **Separate true knowledge from BKT p_known** - Allows validating how well BKT tracks actual student state

2. **Reuse existing exercise generators** - Tests actual system, no duplicate code

3. **Per-exercise snapshots** - Enables detailed trajectory analysis

4. **argparse for CLI** - Minimizes dependencies (stdlib only)

5. **Forgetting model** - Exponential decay: `k_new = k * retention_rate^days_elapsed`

## Dependencies
No new dependencies required - uses existing pydantic and fsrs.
