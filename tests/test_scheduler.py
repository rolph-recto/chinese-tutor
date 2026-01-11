"""Unit tests for the scheduler module."""

from datetime import datetime, timedelta, timezone

import fsrs

from scheduler import (
    update_practice_stats,
    ExerciseScheduler,
)
from models import (
    SessionState,
    StudentMastery,
)


def make_due_now(mastery: StudentMastery):
    """Helper to make a mastery item due now (set due date to the past)."""
    mastery.initialize_fsrs(fsrs.Rating.Good)
    assert mastery.fsrs_state is not None

    # Set the due date to 1 hour in the past
    mastery.fsrs_state.due = datetime.now(timezone.utc) - timedelta(hours=1)

class TestUpdatePracticeStats:
    """Tests for practice statistics updates."""

    def test_correct_updates_stats(self, new_mastery):
        """Correct answer should update all relevant stats."""
        initial_count = new_mastery.practice_count

        update_practice_stats(new_mastery, correct=True)

        assert new_mastery.practice_count == initial_count + 1
        assert new_mastery.correct_count == 1
        assert new_mastery.consecutive_correct == 1
        assert new_mastery.last_practiced is not None

    def test_incorrect_resets_consecutive(self, practiced_mastery):
        """Incorrect answer should reset consecutive correct count."""
        practiced_mastery.consecutive_correct = 5

        update_practice_stats(practiced_mastery, correct=False)

        assert practiced_mastery.consecutive_correct == 0


# =============================================================================
# Tests for ExerciseScheduler class
# =============================================================================


class TestExerciseScheduler:
    """Tests for the ExerciseScheduler class."""

    def test_compose_session_queue(self, sample_knowledge_points, empty_student_state):
        """Should compose a session queue with due items."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )

        # Make some items due
        for kp in sample_knowledge_points[:3]:
            mastery = empty_student_state.get_mastery(kp.id, kp.type)
            make_due_now(mastery)

        queue = scheduler.compose_session_queue(session_size=4)

        # Should have items that are due
        assert len(queue) > 0
        assert len(queue) <= 4

    def test_update_multi_skill_exercise(self, sample_knowledge_points, empty_student_state):
        """Should update practice stats for multiple KPs."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )

        kp_ids = ["v001", "v002"]
        scheduler.update_multi_skill_exercise(kp_ids, is_correct=True)

        # Check that both were updated
        for kp_id in kp_ids:
            mastery = empty_student_state.masteries[kp_id]
            assert mastery.practice_count == 1
            assert mastery.correct_count == 1
