"""Integration tests for run_interactive() in main.py.

These tests simulate user input through stdin by mocking Console.input().
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

import main
from models import StudentState, StudentMastery, FSRSState


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


@pytest.fixture
def knowledge_points():
    """Load actual knowledge points from data files."""
    return main.load_knowledge_points()


@pytest.fixture
def interactive_runner(tmp_path, monkeypatch, knowledge_points):
    """Fixture providing a patched run_interactive runner.

    Patches:
    - main.STATE_FILE to use temp file (uses real DATA_DIR for knowledge points)
    - Console.input to use provided InputSequence
    - Console.clear to no-op (avoid terminal issues)
    - signal.signal to no-op (avoid handler issues in tests)

    Returns a callable that takes an InputSequence and runs the session.
    The callable returns the state file path for assertions.
    """
    state_file = tmp_path / "student_state.json"

    # Patch STATE_FILE to use temp file (keep real DATA_DIR for knowledge points)
    monkeypatch.setattr(main, "STATE_FILE", state_file)

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
            Path to the state file for assertions
        """
        random.seed(seed)

        # Write initial state if provided
        if initial_state is not None:
            state_file.write_text(initial_state.model_dump_json(indent=2))

        # Patch Console.input to use our sequence
        monkeypatch.setattr(Console, "input", input_sequence)

        try:
            main.run_interactive()
        except StopIteration:
            pass  # Expected when inputs exhausted
        except SystemExit:
            pass  # Expected on quit

        return state_file

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

        state_file = interactive_runner(inputs, seed=42)

        # Verify state was saved
        assert state_file.exists()

        # Verify mastery was updated
        state = StudentState.model_validate_json(state_file.read_text())
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

        state_file = interactive_runner(inputs, seed=42)

        assert state_file.exists()
        state = StudentState.model_validate_json(state_file.read_text())

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

        state_file = interactive_runner(inputs, seed=42)

        # State should be saved (creates empty state if none existed)
        assert state_file.exists()


class TestInteractiveStatePersistence:
    """Tests for state loading and saving."""

    def test_state_persisted_after_exercise(
        self,
        interactive_runner,
    ):
        """Should persist mastery updates to student_state.json."""
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

        state_file = interactive_runner(inputs, seed=42)

        # Read the saved state
        state = StudentState.model_validate_json(state_file.read_text())

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
        knowledge_points,
    ):
        """Should show 'all caught up' message when no items are due."""
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

        state_file = interactive_runner(inputs, seed=42, initial_state=initial_state)

        # Session should complete without errors
        assert state_file.exists()

        # State should still have our pre-set masteries
        state = StudentState.model_validate_json(state_file.read_text())
        assert len(state.masteries) == len(knowledge_points)
