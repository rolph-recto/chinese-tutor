"""Unit tests for Bayesian Knowledge Tracing (BKT) algorithm."""

from bkt import update_mastery
from models import StudentMastery, SchedulingMode


class TestBKTUpdateMastery:
    """Tests for the BKT update_mastery function."""

    def test_correct_answer_increases_mastery(self, fresh_mastery):
        """Correct answer should increase p_known from initial state."""
        initial_p = fresh_mastery.p_known
        new_p = update_mastery(fresh_mastery, correct=True)

        assert new_p > initial_p
        assert fresh_mastery.p_known == new_p
        assert 0.0 <= new_p <= 1.0

    def test_incorrect_answer_effect_on_low_mastery(self, fresh_mastery):
        """Incorrect answer on low mastery should have minimal negative effect."""
        new_p = update_mastery(fresh_mastery, correct=False)

        # With p_known=0, incorrect answer shouldn't go negative
        assert new_p >= 0.0
        assert fresh_mastery.p_known == new_p

    def test_incorrect_answer_on_partial_mastery(self, partial_mastery):
        """Incorrect answer on partial mastery updates appropriately."""
        new_p = update_mastery(partial_mastery, correct=False)

        # Should return a valid probability
        assert 0.0 <= new_p <= 1.0
        assert partial_mastery.p_known == new_p

    def test_mastery_bounded_between_0_and_1(self, partial_mastery):
        """P_known should always remain in [0, 1] range."""
        # Many correct answers
        for _ in range(50):
            update_mastery(partial_mastery, correct=True)
        assert 0.0 <= partial_mastery.p_known <= 1.0

        # Many incorrect answers
        for _ in range(50):
            update_mastery(partial_mastery, correct=False)
        assert 0.0 <= partial_mastery.p_known <= 1.0

    def test_learning_progression(self, fresh_mastery):
        """Consecutive correct answers should show learning progression."""
        p_values = [fresh_mastery.p_known]

        for _ in range(10):
            update_mastery(fresh_mastery, correct=True)
            p_values.append(fresh_mastery.p_known)

        # Each value should be >= previous (learning)
        for i in range(1, len(p_values)):
            assert p_values[i] >= p_values[i - 1], f"Learning stalled at step {i}"

    def test_bkt_parameters_affect_update(self):
        """Different BKT parameters should produce different update behaviors."""
        # High transit probability (fast learner)
        fast_mastery = StudentMastery(
            knowledge_point_id="test",
            p_known=0.3,
            p_transit=0.5,  # High
            p_slip=0.1,
            p_guess=0.2,
        )

        # Low transit probability (slow learner)
        slow_mastery = StudentMastery(
            knowledge_point_id="test",
            p_known=0.3,
            p_transit=0.1,  # Low
            p_slip=0.1,
            p_guess=0.2,
        )

        fast_result = update_mastery(fast_mastery, correct=True)
        slow_result = update_mastery(slow_mastery, correct=True)

        # Fast learner should progress more
        assert fast_result > slow_result

    def test_slip_and_guess_affect_update(self):
        """Slip and guess rates should affect the update calculation."""
        # Low slip/guess (reliable student)
        reliable = StudentMastery(
            knowledge_point_id="test",
            p_known=0.5,
            p_transit=0.3,
            p_slip=0.05,
            p_guess=0.1,
        )

        # High slip/guess (unreliable student)
        unreliable = StudentMastery(
            knowledge_point_id="test",
            p_known=0.5,
            p_transit=0.3,
            p_slip=0.2,
            p_guess=0.4,
        )

        # Update both with correct answer
        reliable_result = update_mastery(reliable, correct=True)
        unreliable_result = update_mastery(unreliable, correct=True)

        # Results should differ due to different parameters
        assert reliable_result != unreliable_result


class TestBKTEdgeCases:
    """Edge case tests for BKT algorithm."""

    def test_zero_initial_mastery(self):
        """Handle edge case where p_known starts at 0."""
        mastery = StudentMastery(
            knowledge_point_id="test",
            p_known=0.0,
            p_transit=0.3,
            p_slip=0.1,
            p_guess=0.2,
        )
        result = update_mastery(mastery, correct=True)
        assert 0.0 <= result <= 1.0
        assert result > 0.0  # Should have learned something

    def test_high_mastery_correct(self):
        """Test with p_known already high."""
        mastery = StudentMastery(
            knowledge_point_id="test",
            p_known=0.95,
        )
        result = update_mastery(mastery, correct=True)
        assert result <= 1.0
        assert result >= 0.95  # Should stay high

    def test_low_guess_rate(self):
        """Test with very low guess rate."""
        mastery = StudentMastery(
            knowledge_point_id="test",
            p_known=0.5,
            p_transit=0.3,
            p_slip=0.1,
            p_guess=0.01,  # Very low guess rate
        )
        result = update_mastery(mastery, correct=True)
        assert 0.0 <= result <= 1.0


class TestFSRSModeInBKT:
    """Tests for FSRS mode handling in update_mastery."""

    def test_fsrs_mode_delegates_to_fsrs(self, fsrs_mastery):
        """FSRS mode should use FSRS scheduler instead of BKT."""
        result = update_mastery(fsrs_mastery, correct=True)

        # Should return a retrievability value
        assert 0.0 <= result <= 1.0
        # FSRS state should still exist
        assert fsrs_mastery.fsrs_state is not None

    def test_fsrs_mode_handles_incorrect(self, fsrs_mastery):
        """FSRS mode should handle incorrect answers."""
        result = update_mastery(fsrs_mastery, correct=False)

        assert 0.0 <= result <= 1.0
        assert fsrs_mastery.scheduling_mode == SchedulingMode.FSRS
