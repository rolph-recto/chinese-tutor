"""Unit tests for FSRS scheduler integration."""

import pytest
from datetime import datetime, timedelta

from fsrs_scheduler import (
    fsrs_state_to_card,
    card_to_fsrs_state,
    initialize_fsrs_for_mastery,
    process_fsrs_review,
    get_fsrs_due_date,
    get_fsrs_retrievability,
    is_fsrs_due,
)
from models import StudentMastery, SchedulingMode, FSRSState


class TestFSRSStateConversion:
    """Tests for FSRS state conversion functions."""

    def test_roundtrip_conversion(self):
        """Converting state to card and back should preserve key data."""
        original = FSRSState(
            stability=10.0,
            difficulty=5.0,
            due=datetime.now(),
            last_review=datetime.now() - timedelta(days=1),
            state=2,
            step=None,
        )

        card = fsrs_state_to_card(original)
        result = card_to_fsrs_state(card)

        assert abs(result.stability - original.stability) < 0.01
        assert abs(result.difficulty - original.difficulty) < 0.01
        assert result.state == original.state

    def test_convert_learning_state(self):
        """Should handle learning card state conversion."""
        original = FSRSState(
            stability=None,
            difficulty=None,
            due=datetime.now(),
            last_review=None,
            state=1,  # Learning
            step=0,
        )

        card = fsrs_state_to_card(original)
        result = card_to_fsrs_state(card)

        assert result.state == original.state


class TestInitializeFSRS:
    """Tests for FSRS initialization."""

    def test_initializes_fsrs_state(self, mastered_bkt):
        """Should initialize FSRS state for a mastered BKT item."""
        assert mastered_bkt.fsrs_state is None

        initialize_fsrs_for_mastery(mastered_bkt)

        assert mastered_bkt.scheduling_mode == SchedulingMode.FSRS
        assert mastered_bkt.fsrs_state is not None
        assert mastered_bkt.transitioned_to_fsrs_at is not None
        assert mastered_bkt.fsrs_state.due is not None

    def test_sets_initial_stability(self, mastered_bkt):
        """FSRS initialization should set initial stability."""
        initialize_fsrs_for_mastery(mastered_bkt)

        assert mastered_bkt.fsrs_state.stability is not None
        assert mastered_bkt.fsrs_state.stability > 0


class TestProcessFSRSReview:
    """Tests for FSRS review processing."""

    def test_correct_review_updates_state(self, fsrs_mastery):
        """Correct review should update FSRS state."""
        initial_due = fsrs_mastery.fsrs_state.due

        process_fsrs_review(fsrs_mastery, correct=True)

        # Due date should change after review
        assert fsrs_mastery.fsrs_state.due != initial_due

    def test_incorrect_review_updates_state(self, fsrs_mastery):
        """Incorrect review should update FSRS state."""
        process_fsrs_review(fsrs_mastery, correct=False)

        assert fsrs_mastery.fsrs_state is not None

    def test_raises_without_fsrs_state(self, fresh_mastery):
        """Should raise error if no FSRS state exists."""
        fresh_mastery.scheduling_mode = SchedulingMode.FSRS
        # fsrs_state is None

        with pytest.raises(ValueError):
            process_fsrs_review(fresh_mastery, correct=True)

    def test_correct_increases_stability(self, fsrs_mastery):
        """Correct review should generally increase stability."""
        initial_stability = fsrs_mastery.fsrs_state.stability

        process_fsrs_review(fsrs_mastery, correct=True)

        # Stability should increase or stay similar for correct answers
        assert fsrs_mastery.fsrs_state.stability >= initial_stability * 0.9


class TestFSRSDueDate:
    """Tests for FSRS due date functions."""

    def test_get_due_date(self, fsrs_mastery):
        """Should return due date for FSRS item."""
        result = get_fsrs_due_date(fsrs_mastery)

        assert result is not None
        assert isinstance(result, datetime)

    def test_none_for_bkt_mode(self, partial_mastery):
        """Should return None for BKT mode items."""
        result = get_fsrs_due_date(partial_mastery)

        assert result is None

    def test_is_fsrs_due_past(self, fsrs_mastery):
        """Should return True if past due date."""
        fsrs_mastery.fsrs_state.due = datetime.now() - timedelta(hours=1)

        result = is_fsrs_due(fsrs_mastery)

        assert result is True

    def test_is_fsrs_due_future(self, fsrs_mastery):
        """Should return False if due date is in future."""
        fsrs_mastery.fsrs_state.due = datetime.now() + timedelta(days=7)

        result = is_fsrs_due(fsrs_mastery)

        assert result is False

    def test_is_fsrs_due_none_state(self, fresh_mastery):
        """Should return False if no FSRS state."""
        result = is_fsrs_due(fresh_mastery)

        assert result is False


class TestFSRSRetrievability:
    """Tests for FSRS retrievability calculation."""

    def test_retrievability_range(self, fsrs_mastery):
        """Retrievability should be between 0 and 1."""
        result = get_fsrs_retrievability(fsrs_mastery)

        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_none_for_bkt_mode(self, partial_mastery):
        """Should return None for BKT mode items."""
        result = get_fsrs_retrievability(partial_mastery)

        assert result is None

    def test_none_without_fsrs_state(self):
        """Should return None if FSRS mode but no state."""
        mastery = StudentMastery(
            knowledge_point_id="test",
            scheduling_mode=SchedulingMode.FSRS,
            fsrs_state=None,
        )

        result = get_fsrs_retrievability(mastery)

        assert result is None
