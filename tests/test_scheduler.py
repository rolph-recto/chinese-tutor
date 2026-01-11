"""Unit tests for the scheduler module."""

from datetime import datetime, timedelta, timezone

import fsrs

from scheduler import ExerciseScheduler
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

    def test_update_multi_skill_exercise(
        self, sample_knowledge_points, empty_student_state
    ):
        """Should update FSRS state for multiple KPs."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )

        kp_ids = ["v001", "v002"]
        scheduler.update_multi_skill_exercise(kp_ids, rating=fsrs.Rating.Good)

        # Check that both were updated with FSRS state
        for kp_id in kp_ids:
            mastery = empty_student_state.masteries[kp_id]
            assert mastery.fsrs_state is not None
            assert mastery.due_date is not None
