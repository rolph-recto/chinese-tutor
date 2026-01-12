"""Integration tests for run_interactive() in main.py.

These tests simulate user input through stdin by mocking Console.input().
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

import main
from models import StudentState, StudentMastery, FSRSState
from storage import (
    init_schema,
    get_connection,
    get_student_state_repo,
    get_knowledge_point_repo,
)


class InputSequence:
    """Callable providing sequential inputs for mocked Console.input().

    Used in integration tests to simulate user input through stdin.
    Tracks all prompts received for debugging failed tests.
    """

    def __init__(self, inputs: list[str]):
        self.inputs = inputs
        self.index = 0
        self.call_history: list[tuple[int, Any]] = []

    def __call__(self, prompt: Any = "") -> str:
        """Return next input in sequence, tracking prompts received."""
        self.call_history.append((self.index, prompt))
        if self.index >= len(self.inputs):
            history = "\n".join(f"  {i}: {p}" for i, p in self.call_history)
            raise StopIteration(
                f"Ran out of inputs at call {self.index}.\n"
                f"Prompt: {prompt}\n"
                f"History:\n{history}"
            )
        result = self.inputs[self.index]
        self.index += 1
        return result

    @property
    def remaining(self) -> int:
        """Number of unused inputs remaining."""
        return len(self.inputs) - self.index


def _populate_test_db_from_json(db_path: Path, data_dir: Path) -> None:
    """Populate test database from JSON data files."""
    conn = get_connection(db_path)
    try:
        # Migrate vocabulary
        vocab_file = data_dir / "vocabulary.json"
        if vocab_file.exists():
            with open(vocab_file) as f:
                items = json.load(f)
            for item in items:
                conn.execute(
                    """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"],
                        item["type"],
                        item["chinese"],
                        item["pinyin"],
                        item["english"],
                        json.dumps(item.get("tags", [])),
                    ),
                )

        # Migrate grammar
        grammar_file = data_dir / "grammar.json"
        if grammar_file.exists():
            with open(grammar_file) as f:
                items = json.load(f)
            for item in items:
                conn.execute(
                    """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"],
                        item["type"],
                        item["chinese"],
                        item["pinyin"],
                        item["english"],
                        json.dumps(item.get("tags", [])),
                    ),
                )

        # Migrate minimal pairs
        pairs_file = data_dir / "minimal_pairs.json"
        if pairs_file.exists():
            with open(pairs_file) as f:
                pairs = json.load(f)
            for pair in pairs:
                target_id = pair["target_id"]
                for distractor in pair["distractors"]:
                    conn.execute(
                        """INSERT INTO minimal_pairs
                        (target_id, distractor_chinese, distractor_pinyin, distractor_english, reason)
                        VALUES (?, ?, ?, ?, ?)""",
                        (
                            target_id,
                            distractor["chinese"],
                            distractor["pinyin"],
                            distractor["english"],
                            distractor.get("reason"),
                        ),
                    )

        # Migrate cloze templates
        cloze_file = data_dir / "cloze_templates.json"
        if cloze_file.exists():
            with open(cloze_file) as f:
                templates = json.load(f)
            for template in templates:
                conn.execute(
                    """INSERT INTO cloze_templates (id, chinese, english, target_vocab_id, tags)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        template["id"],
                        template["chinese"],
                        template["english"],
                        template["target_vocab_id"],
                        json.dumps(template.get("tags", [])),
                    ),
                )

        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def knowledge_points():
    """Load actual knowledge points from data files."""
    return main.load_knowledge_points()


@pytest.fixture
def interactive_runner(tmp_path, monkeypatch):
    """Fixture providing a patched run_interactive runner.

    Patches:
    - main.DB_PATH to use temp database (migrated from real data files)
    - Console.input to use provided InputSequence
    - Console.clear to no-op (avoid terminal issues)
    - signal.signal to no-op (avoid handler issues in tests)

    Returns a callable that takes an InputSequence and runs the session.
    The callable returns the database path for assertions.
    """
    test_db_path = tmp_path / "test_tutor.db"

    # Initialize schema and populate from real data files
    init_schema(test_db_path)
    _populate_test_db_from_json(test_db_path, main.DATA_DIR)

    # Patch DB_PATH to use test database
    monkeypatch.setattr(main, "DB_PATH", test_db_path)

    # Disable signal handler (can cause issues in tests)
    monkeypatch.setattr("signal.signal", lambda *args, **kwargs: None)

    # Patch Console.clear to avoid terminal manipulation
    monkeypatch.setattr(Console, "clear", lambda self: None)

    def runner(
        input_sequence: InputSequence,
        seed: int = 42,
        initial_state: StudentState | None = None,
    ) -> Path:
        """Run interactive session with given inputs.

        Args:
            input_sequence: Sequence of inputs to provide
            seed: Random seed for deterministic exercise selection
            initial_state: Optional initial student state to load

        Returns:
            Path to the database for assertions
        """
        random.seed(seed)

        # Save initial state to database if provided
        if initial_state is not None:
            repo = get_student_state_repo(test_db_path)
            repo.save(initial_state)

        # Patch Console.input to use our sequence
        monkeypatch.setattr(Console, "input", input_sequence)

        try:
            main.run_interactive()
        except StopIteration:
            pass  # Expected when inputs exhausted
        except SystemExit:
            pass  # Expected on quit

        return test_db_path

    return runner


class TestInteractiveBasicFlow:
    """Tests for basic interactive session flow."""

    def test_complete_session_correct_answer(
        self,
        interactive_runner,
    ):
        """Should complete a session with a correct answer and update mastery."""
        # Input sequence:
        # With seed=42, first exercise is segmented_translation (ordering mode)
        # The exercise is "he is a teacher" -> 他是老师
        # Options are: 1. 是  2. 老师  3. 他
        # Correct order is: 3 1 2 (他 是 老师)

        inputs = InputSequence(
            [
                "",  # Welcome - press Enter
                "3 1 2",  # Correct ordering answer
                "3",  # Rate as "Good"
            ]
        )

        db_path = interactive_runner(inputs, seed=42)

        # Verify database exists
        assert db_path.exists()

        # Verify mastery was updated
        repo = get_student_state_repo(db_path)
        state = repo.load()
        assert len(state.masteries) > 0

        # At least one mastery should have FSRS state initialized
        has_fsrs = any(m.fsrs_state is not None for m in state.masteries.values())
        assert has_fsrs, "Expected at least one mastery to have FSRS state"

    def test_complete_session_incorrect_answer(
        self,
        interactive_runner,
    ):
        """Should handle incorrect answer with Rating.Again."""
        # With seed=42, first exercise is segmented_translation (ordering mode)
        # Give a wrong order to trigger incorrect answer path

        inputs = InputSequence(
            [
                "",  # Welcome
                "1 2 3",  # Wrong order (correct is 3 1 2)
                "",  # Continue after feedback (Rating.Again applied automatically)
            ]
        )

        db_path = interactive_runner(inputs, seed=42)

        assert db_path.exists()
        repo = get_student_state_repo(db_path)
        state = repo.load()

        # State should have been saved with mastery updated
        assert len(state.masteries) > 0


class TestInteractiveQuitHandling:
    """Tests for quit behavior."""

    def test_quit_at_exercise_prompt(
        self,
        interactive_runner,
    ):
        """Should save state and exit cleanly when user quits at exercise prompt."""
        inputs = InputSequence(
            [
                "",  # Welcome
                "q",  # Quit at exercise
            ]
        )

        db_path = interactive_runner(inputs, seed=42)

        # Database should exist
        assert db_path.exists()


class TestInteractiveStatePersistence:
    """Tests for state loading and saving."""

    def test_state_persisted_after_exercise(
        self,
        interactive_runner,
    ):
        """Should persist mastery updates to database."""
        # With seed=42, first exercise is segmented_translation (ordering mode)
        # The exercise is "he is a teacher" -> 他是老师
        # Options: 1. 是  2. 老师  3. 他  -> Correct order: 3 1 2

        inputs = InputSequence(
            [
                "",  # Welcome
                "3 1 2",  # Correct ordering answer
                "3",  # Rate as Good
            ]
        )

        db_path = interactive_runner(inputs, seed=42)

        # Read the saved state from database
        repo = get_student_state_repo(db_path)
        state = repo.load()

        # Should have at least one mastery record
        assert len(state.masteries) > 0

        # The mastery should have FSRS scheduling data
        for mastery in state.masteries.values():
            if mastery.fsrs_state is not None:
                # Should have a due date set
                assert mastery.fsrs_state.due is not None
                break
        else:
            pytest.fail("Expected at least one mastery with FSRS state")


class TestInteractiveEdgeCases:
    """Tests for edge cases."""

    def test_no_knowledge_points_due(
        self,
        interactive_runner,
        tmp_path,
        monkeypatch,
    ):
        """Should show 'all caught up' message when no items are due."""
        # Load knowledge points from the test database (main.DB_PATH is already patched)
        kp_repo = get_knowledge_point_repo(main.DB_PATH)
        knowledge_points = kp_repo.get_all()

        # Create a state where all items have future due dates
        future_due = datetime.now() + timedelta(days=7)
        initial_state = StudentState()

        for kp in knowledge_points:
            initial_state.masteries[kp.id] = StudentMastery(
                knowledge_point_id=kp.id,
                fsrs_state=FSRSState(
                    stability=10.0,
                    difficulty=5.0,
                    due=future_due,
                    last_review=datetime.now(),
                    state=2,  # Review state
                    step=None,
                ),
            )

        # Only need welcome input - session ends immediately when nothing is due
        inputs = InputSequence(
            [
                "",  # Welcome
            ]
        )

        db_path = interactive_runner(inputs, seed=42, initial_state=initial_state)

        # Session should complete without errors
        assert db_path.exists()

        # State should still have our pre-set masteries
        repo = get_student_state_repo(db_path)
        state = repo.load()
        assert len(state.masteries) == len(knowledge_points)
