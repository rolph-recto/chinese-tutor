# Plan: Ask Student for FSRS Rating After Correct Answer

## Goal
After a student answers an exercise correctly, prompt them to rate how easy/difficult the recall was using FSRS ratings (Again, Hard, Good, Easy). Incorrect answers automatically get "Again" rating. Also remove practice stats (practice_count, correct_count, consecutive_correct) as they are redundant with FSRS.

## Files to Modify
- `main.py` - Add rating prompt after correct answer, pass rating to `process_review()`, remove practice stats calls
- `models.py` - Modify `process_review()` to accept a rating, remove practice stats fields from `StudentMastery`
- `scheduler.py` - Remove `update_practice_stats()` function and calls
- `tests/` - Update tests to use ratings and remove practice stats assertions

## Current Behavior
- User answers exercise → `is_correct: bool` returned
- `mastery.process_review(is_correct)` maps: correct → Good, incorrect → Again
- `update_practice_stats()` tracks practice_count, correct_count, consecutive_correct
- User never sees or chooses the FSRS rating

## New Behavior
- User answers exercise → `is_correct: bool` returned
- If **incorrect**: automatically use `Rating.Again`
- If **correct**: prompt user "How easy was that? (1) Again (2) Hard (3) Good (4) Easy"
- Pass the chosen rating to `process_review(rating)`
- Remove all practice stats tracking

## Required Changes

### File: `main.py`

#### 1. Add fsrs import
```python
import fsrs
```

#### 2. Add rating prompt function
```python
def prompt_for_rating() -> fsrs.Rating:
    """Prompt the user to rate the difficulty of recall."""
    print("\nHow easy was that?")
    print("  1) Again - I forgot / got lucky")
    print("  2) Hard  - Difficult to recall")
    print("  3) Good  - Correct with some effort")
    print("  4) Easy  - Effortless recall")

    while True:
        choice = input("Rating (1-4): ").strip()
        if choice == "1":
            return fsrs.Rating.Again
        elif choice == "2":
            return fsrs.Rating.Hard
        elif choice == "3":
            return fsrs.Rating.Good
        elif choice == "4":
            return fsrs.Rating.Easy
        else:
            print("Please enter 1, 2, 3, or 4.")
```

#### 3. Modify mastery update section (around line 282)
Before:
```python
mastery.process_review(is_correct)
update_practice_stats(mastery, is_correct)
```

After:
```python
if is_correct:
    rating = prompt_for_rating()
else:
    rating = fsrs.Rating.Again
mastery.process_review(rating)
```

#### 4. Remove import of `update_practice_stats` from scheduler

### File: `models.py`

#### 1. Remove practice stats fields from `StudentMastery`
Remove:
```python
last_practiced: datetime | None = None
practice_count: int = 0
correct_count: int = 0
consecutive_correct: int = 0
```

#### 2. Modify `process_review()` signature
Before:
```python
def process_review(self, correct: bool) -> fsrs.ReviewLog:
    rating = fsrs.Rating.Good if correct else fsrs.Rating.Again
    ...
```

After:
```python
def process_review(self, rating: fsrs.Rating) -> fsrs.ReviewLog:
    # Rating is now passed in directly (no mapping)
    ...
```

### File: `scheduler.py`

#### 1. Remove `update_practice_stats()` function entirely
Delete this function:
```python
def update_practice_stats(mastery: StudentMastery, correct: bool) -> None:
    ...
```

#### 2. Update `update_multi_skill_exercise()`
Change signature and remove practice stats call:

Before:
```python
def update_multi_skill_exercise(self, kp_ids: list[str], is_correct: bool) -> None:
    for kp_id in kp_ids:
        mastery = self._get_mastery_for_kp(kp_id)
        mastery.process_review(is_correct)
        update_practice_stats(mastery, is_correct)
```

After:
```python
def update_multi_skill_exercise(self, kp_ids: list[str], rating: fsrs.Rating) -> None:
    for kp_id in kp_ids:
        mastery = self._get_mastery_for_kp(kp_id)
        mastery.process_review(rating)
```

### File: `simulate.py`

Update simulator to use ratings instead of boolean correct/incorrect.

### File: `tests/test_scheduler.py`

- Update `test_update_multi_skill_exercise` to pass rating instead of boolean
- Remove `TestUpdatePracticeStats` test class entirely

### File: `tests/test_integration_simulator.py`

Update tests that check practice stats to check FSRS state instead.

## Testing
```
uv run pytest -v
```

Manual test:
1. Run `uv run python main.py`
2. Answer correctly → verify rating prompt appears
3. Answer incorrectly → verify no prompt, auto-Again
4. Check each rating option updates due date correctly
