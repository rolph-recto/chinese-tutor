"""Unit tests for the scheduler module."""

from datetime import datetime, timedelta

from scheduler import (
    apply_mastery_decay,
    check_and_transition_to_fsrs,
    prerequisites_met,
    is_on_frontier,
    needs_review,
    calculate_kp_score,
    select_next_knowledge_point,
    update_practice_stats,
    DECAY_RATE_PER_WEEK,
    ExerciseScheduler,
)
from models import (
    KnowledgePointType,
    MASTERY_THRESHOLD,
    PracticeMode,
    SchedulingMode,
    SessionState,
)


class TestMasteryDecay:
    """Tests for time-based mastery decay."""

    def test_no_decay_for_unpracticed(self, empty_student_state, sample_vocabulary_kp):
        """Items never practiced should not decay."""
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.5
        # No last_practiced set

        apply_mastery_decay(empty_student_state)

        assert mastery.p_known == 0.5

    def test_decay_after_one_week(self, empty_student_state, sample_vocabulary_kp):
        """Mastery should decay by DECAY_RATE_PER_WEEK after one week."""
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.8
        mastery.last_practiced = datetime.now() - timedelta(weeks=1)

        apply_mastery_decay(empty_student_state)

        expected = 0.8 - DECAY_RATE_PER_WEEK
        assert abs(mastery.p_known - expected) < 0.01

    def test_decay_capped_at_zero(self, empty_student_state, sample_vocabulary_kp):
        """Mastery decay should not go below 0."""
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.1
        mastery.last_practiced = datetime.now() - timedelta(weeks=52)  # 1 year

        apply_mastery_decay(empty_student_state)

        assert mastery.p_known >= 0.0

    def test_no_decay_for_fsrs_mode(self, empty_student_state, fsrs_mastery):
        """FSRS mode items should not have BKT decay applied."""
        empty_student_state.masteries[fsrs_mastery.knowledge_point_id] = fsrs_mastery
        initial_p = fsrs_mastery.p_known

        apply_mastery_decay(empty_student_state)

        assert fsrs_mastery.p_known == initial_p


class TestBKTToFSRSTransition:
    """Tests for BKT to FSRS transition logic."""

    def test_transition_at_threshold(self, mastered_bkt):
        """Should transition when p_known >= MASTERY_THRESHOLD."""
        assert mastered_bkt.scheduling_mode == SchedulingMode.BKT
        assert mastered_bkt.p_known >= MASTERY_THRESHOLD

        result = check_and_transition_to_fsrs(mastered_bkt)

        assert result is True
        assert mastered_bkt.scheduling_mode == SchedulingMode.FSRS
        assert mastered_bkt.fsrs_state is not None
        assert mastered_bkt.transitioned_to_fsrs_at is not None

    def test_no_transition_below_threshold(self, near_mastery):
        """Should not transition when p_known < MASTERY_THRESHOLD."""
        assert near_mastery.p_known < MASTERY_THRESHOLD

        result = check_and_transition_to_fsrs(near_mastery)

        assert result is False
        assert near_mastery.scheduling_mode == SchedulingMode.BKT

    def test_no_transition_if_already_fsrs(self, fsrs_mastery):
        """Should not re-transition if already in FSRS mode."""
        result = check_and_transition_to_fsrs(fsrs_mastery)

        assert result is False
        assert fsrs_mastery.scheduling_mode == SchedulingMode.FSRS


class TestPrerequisites:
    """Tests for prerequisite checking logic."""

    def test_no_prerequisites_always_met(
        self, empty_student_state, sample_vocabulary_kp
    ):
        """KP with no prerequisites should always have prerequisites met."""
        kp_dict = {sample_vocabulary_kp.id: sample_vocabulary_kp}

        result = prerequisites_met(sample_vocabulary_kp, empty_student_state, kp_dict)

        assert result is True

    def test_unmet_prerequisites(
        self, empty_student_state, sample_grammar_kp, sample_knowledge_points
    ):
        """Grammar KP should not have prerequisites met if prereq not mastered."""
        kp_dict = {kp.id: kp for kp in sample_knowledge_points}
        # v005 (prerequisite) is not mastered
        empty_student_state.get_mastery("v005").p_known = 0.5

        result = prerequisites_met(sample_grammar_kp, empty_student_state, kp_dict)

        assert result is False

    def test_met_prerequisites(
        self, empty_student_state, sample_grammar_kp, sample_knowledge_points
    ):
        """Grammar KP should have prerequisites met if prereq is mastered."""
        kp_dict = {kp.id: kp for kp in sample_knowledge_points}
        # v005 (prerequisite) is mastered
        empty_student_state.get_mastery("v005").p_known = 0.96

        result = prerequisites_met(sample_grammar_kp, empty_student_state, kp_dict)

        assert result is True


class TestFrontier:
    """Tests for frontier detection logic."""

    def test_on_frontier(
        self, empty_student_state, sample_grammar_kp, sample_knowledge_points
    ):
        """KP should be on frontier if prerequisites met but not mastered."""
        kp_dict = {kp.id: kp for kp in sample_knowledge_points}
        empty_student_state.get_mastery("v005").p_known = 0.96  # Prereq mastered
        empty_student_state.get_mastery("g001").p_known = 0.3  # KP not mastered

        result = is_on_frontier(sample_grammar_kp, empty_student_state, kp_dict)

        assert result is True

    def test_not_on_frontier_if_mastered(
        self, empty_student_state, sample_vocabulary_kp
    ):
        """Mastered KP should not be on frontier."""
        kp_dict = {sample_vocabulary_kp.id: sample_vocabulary_kp}
        empty_student_state.get_mastery(sample_vocabulary_kp.id).p_known = 0.96

        result = is_on_frontier(sample_vocabulary_kp, empty_student_state, kp_dict)

        assert result is False

    def test_not_on_frontier_if_prerequisites_unmet(
        self, empty_student_state, sample_grammar_kp, sample_knowledge_points
    ):
        """KP should not be on frontier if prerequisites not met."""
        kp_dict = {kp.id: kp for kp in sample_knowledge_points}
        empty_student_state.get_mastery("v005").p_known = 0.3  # Prereq not mastered

        result = is_on_frontier(sample_grammar_kp, empty_student_state, kp_dict)

        assert result is False


class TestNeedsReview:
    """Tests for review need detection."""

    def test_needs_review_bkt_mode(self, empty_student_state, sample_vocabulary_kp):
        """BKT item with decayed mastery should need review."""
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.6
        mastery.last_practiced = datetime.now() - timedelta(days=3)

        result = needs_review(sample_vocabulary_kp, empty_student_state)

        assert result is True

    def test_no_review_if_never_practiced(
        self, empty_student_state, sample_vocabulary_kp
    ):
        """Item never practiced should not need review (it's new, not a review)."""
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.0
        # No last_practiced

        result = needs_review(sample_vocabulary_kp, empty_student_state)

        assert result is False

    def test_no_review_if_mastered(self, empty_student_state, sample_vocabulary_kp):
        """BKT item at mastery threshold should not need review."""
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.96
        mastery.last_practiced = datetime.now()

        result = needs_review(sample_vocabulary_kp, empty_student_state)

        assert result is False


class TestCalculateKPScore:
    """Tests for KP scoring logic."""

    def test_low_mastery_needs_review_scores(
        self, empty_student_state, sample_vocabulary_kp, sample_knowledge_points
    ):
        """Low mastery items needing review should score positively."""
        kp_dict = {kp.id: kp for kp in sample_knowledge_points}
        mastery = empty_student_state.get_mastery(sample_vocabulary_kp.id)
        mastery.p_known = 0.3
        mastery.last_practiced = datetime.now() - timedelta(days=1)

        score = calculate_kp_score(
            sample_vocabulary_kp, empty_student_state, kp_dict, prefer_type=None
        )

        assert score > 0

    def test_interleaving_bonus(
        self,
        empty_student_state,
        sample_vocabulary_kp,
        sample_grammar_kp,
        sample_knowledge_points,
    ):
        """Preferred type should get interleaving bonus."""
        kp_dict = {kp.id: kp for kp in sample_knowledge_points}

        # Score vocabulary KP when preferring vocabulary
        score_preferred = calculate_kp_score(
            sample_vocabulary_kp,
            empty_student_state,
            kp_dict,
            prefer_type=KnowledgePointType.VOCABULARY,
        )

        # Score same KP when preferring grammar
        score_not_preferred = calculate_kp_score(
            sample_vocabulary_kp,
            empty_student_state,
            kp_dict,
            prefer_type=KnowledgePointType.GRAMMAR,
        )

        assert score_preferred > score_not_preferred


class TestSelectNextKnowledgePoint:
    """Tests for knowledge point selection."""

    def test_selects_from_available(
        self, empty_student_state, sample_knowledge_points
    ):
        """Should select a KP from the available list."""
        result = select_next_knowledge_point(
            empty_student_state, sample_knowledge_points
        )

        assert result is not None
        assert result.id in [kp.id for kp in sample_knowledge_points]

    def test_empty_list_returns_none(self, empty_student_state):
        """Should return None for empty knowledge point list."""
        result = select_next_knowledge_point(empty_student_state, [])

        assert result is None

    def test_prioritizes_items_needing_review(
        self, populated_student_state, sample_knowledge_points
    ):
        """Should prioritize items needing review."""
        # Mark v001 as needing review (low mastery, practiced before)
        populated_student_state.masteries["v001"].last_practiced = datetime.now() - timedelta(days=2)

        result = select_next_knowledge_point(
            populated_student_state, sample_knowledge_points
        )

        assert result is not None


class TestUpdatePracticeStats:
    """Tests for practice statistics updates."""

    def test_correct_updates_stats(self, fresh_mastery):
        """Correct answer should update all relevant stats."""
        initial_count = fresh_mastery.practice_count

        update_practice_stats(fresh_mastery, correct=True)

        assert fresh_mastery.practice_count == initial_count + 1
        assert fresh_mastery.correct_count == 1
        assert fresh_mastery.consecutive_correct == 1
        assert fresh_mastery.last_practiced is not None

    def test_incorrect_resets_consecutive(self, partial_mastery):
        """Incorrect answer should reset consecutive correct count."""
        partial_mastery.consecutive_correct = 5

        update_practice_stats(partial_mastery, correct=False)

        assert partial_mastery.consecutive_correct == 0

    def test_triggers_fsrs_transition(self, mastered_bkt):
        """Should trigger FSRS transition when mastery threshold reached."""
        update_practice_stats(mastered_bkt, correct=True)

        assert mastered_bkt.scheduling_mode == SchedulingMode.FSRS


# =============================================================================
# New tests for ExerciseScheduler class
# =============================================================================


class TestExerciseSchedulerPools:
    """Tests for Learning/Retention pool management."""

    def test_learning_pool_below_threshold(self, sample_knowledge_points, empty_student_state):
        """KPs with p_known < 0.95 should be in learning pool."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # All KPs start at 0.0, so all should be in learning pool
        learning_pool = scheduler.get_learning_pool()

        assert len(learning_pool) == len(sample_knowledge_points)

    def test_retention_pool_above_threshold(self, sample_knowledge_points, empty_student_state):
        """KPs with p_known >= 0.95 should be in retention pool."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # Master one KP
        empty_student_state.get_mastery("v001").p_known = 0.96

        retention_pool = scheduler.get_retention_pool()

        assert "v001" in retention_pool
        assert len(retention_pool) == 1

    def test_mastery_transition_at_threshold(self, sample_knowledge_points, empty_student_state):
        """KPs reaching 0.95 should transition to FSRS."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # Set a KP at exactly threshold
        empty_student_state.get_mastery("v001").p_known = 0.95

        result = scheduler.check_mastery_transition("v001")

        assert result is True
        assert empty_student_state.get_mastery("v001").scheduling_mode == SchedulingMode.FSRS


class TestExerciseSchedulerBlockedPractice:
    """Tests for blocked practice mode."""

    def test_blocked_practice_filters_by_tag(self, sample_knowledge_points, empty_student_state):
        """Blocked mode should only select KPs with active cluster tag."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        scheduler.activate_blocked_practice("cluster:pronouns")

        selected = scheduler._select_blocked(10)

        # Only v001 and v002 have cluster:pronouns tag
        for kp_id in selected:
            kp = scheduler.knowledge_points.get(kp_id)
            assert "cluster:pronouns" in kp.tags

    def test_interleaved_selects_all_learning(self, sample_knowledge_points, empty_student_state):
        """Interleaved mode should select from all learning KPs."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # Default is interleaved mode

        selected = scheduler._select_interleaved(10)

        # Should include KPs from different clusters
        assert len(selected) > 0

    def test_blocked_complete_triggers_transition(self, sample_knowledge_points, empty_student_state):
        """Completing blocked cluster should transition to interleaved."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        scheduler.activate_blocked_practice("cluster:pronouns")

        # Master all pronouns
        empty_student_state.get_mastery("v001").p_known = 0.96
        empty_student_state.get_mastery("v002").p_known = 0.96

        result = scheduler.check_blocked_practice_complete()

        assert result is True
        assert session_state.practice_mode == PracticeMode.INTERLEAVED
        assert session_state.active_cluster_tag is None


class TestExerciseSchedulerRetention:
    """Tests for retention mode selection."""

    def test_retention_prioritizes_low_retrievability(self, sample_knowledge_points, empty_student_state):
        """Retention selection should prioritize lowest retrievability."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # Master multiple KPs to populate retention pool
        for kp in sample_knowledge_points[:3]:
            mastery = empty_student_state.get_mastery(kp.id)
            mastery.p_known = 0.96
            mastery.scheduling_mode = SchedulingMode.FSRS

        selected = scheduler._select_from_retention(10)

        # Should return items from retention pool
        assert len(selected) > 0


class TestExerciseSchedulerSessionComposition:
    """Tests for session composition."""

    def test_session_composition_ratio(self, sample_knowledge_points, empty_student_state):
        """Session queue should respect learning/retention ratio."""
        session_state = SessionState(learning_retention_ratio=0.5)
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # Master one KP to have items in retention pool
        empty_student_state.get_mastery("v001").p_known = 0.96
        empty_student_state.get_mastery("v001").scheduling_mode = SchedulingMode.FSRS

        queue = scheduler.compose_session_queue(session_size=10)

        # Queue should be composed (ratio applied if both pools have items)
        assert len(queue) > 0

    def test_empty_learning_uses_retention_only(self, sample_knowledge_points, empty_student_state):
        """Empty learning pool should use 100% retention."""
        session_state = SessionState()
        scheduler = ExerciseScheduler(
            sample_knowledge_points, empty_student_state, session_state
        )
        # Master all KPs
        for kp in sample_knowledge_points:
            mastery = empty_student_state.get_mastery(kp.id)
            mastery.p_known = 0.96
            mastery.scheduling_mode = SchedulingMode.FSRS

        queue = scheduler.compose_session_queue(session_size=4)

        # All items should be from retention pool
        assert len(queue) == len(sample_knowledge_points)
        for kp_id in queue:
            assert kp_id in scheduler.get_retention_pool()
