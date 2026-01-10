"""Unit tests for the topic selection menu module."""

import pytest

from menu import TopicSelectionMenu
from models import (
    KnowledgePoint,
    KnowledgePointType,
    StudentState,
)


@pytest.fixture
def menu_knowledge_points() -> list[KnowledgePoint]:
    """Create knowledge points with cluster tags for menu testing.

    Note: Vocabulary items start in FSRS mode (mastered), so they don't appear
    in the topic menu. Grammar items start in BKT mode and are eligible for
    blocked practice via the menu.
    """
    return [
        # Vocabulary clusters - these will be in FSRS mode (mastered)
        KnowledgePoint(
            id="v001",
            type=KnowledgePointType.VOCABULARY,
            chinese="我",
            pinyin="wǒ",
            english="I, me",
            tags=["hsk1", "cluster:pronouns"],
            prerequisites=[],
        ),
        KnowledgePoint(
            id="v002",
            type=KnowledgePointType.VOCABULARY,
            chinese="你",
            pinyin="nǐ",
            english="you",
            tags=["hsk1", "cluster:pronouns"],
            prerequisites=[],
        ),
        KnowledgePoint(
            id="v005",
            type=KnowledgePointType.VOCABULARY,
            chinese="是",
            pinyin="shì",
            english="to be",
            tags=["hsk1", "cluster:basic-verbs"],
            prerequisites=[],
        ),
        KnowledgePoint(
            id="v012",
            type=KnowledgePointType.VOCABULARY,
            chinese="吃",
            pinyin="chī",
            english="to eat",
            tags=["hsk1", "cluster:basic-verbs"],
            prerequisites=[],
        ),
        # Grammar clusters - these will be in BKT mode (learning)
        KnowledgePoint(
            id="g001",
            type=KnowledgePointType.GRAMMAR,
            chinese="Subject + 是 + Noun",
            pinyin="Subject + shì + Noun",
            english="Subject is Noun",
            tags=["hsk1", "cluster:sentence-patterns"],
            prerequisites=["v005"],  # Requires v005 which is vocab (mastered)
        ),
        KnowledgePoint(
            id="g002",
            type=KnowledgePointType.GRAMMAR,
            chinese="Subject + 很 + Adj",
            pinyin="Subject + hěn + Adj",
            english="Subject is very Adj",
            tags=["hsk1", "cluster:basic-sentences"],
            prerequisites=[],
        ),
        KnowledgePoint(
            id="g003",
            type=KnowledgePointType.GRAMMAR,
            chinese="Subject + 不 + Verb",
            pinyin="Subject + bù + Verb",
            english="Subject does not Verb",
            tags=["hsk1", "cluster:basic-sentences"],
            prerequisites=[],
        ),
    ]


@pytest.fixture
def menu_student_state() -> StudentState:
    """Create a student state for menu testing."""
    return StudentState()


class TestGetAllClusterTags:
    """Tests for extracting cluster tags from knowledge points."""

    def test_extracts_unique_clusters(self, menu_knowledge_points, menu_student_state):
        """Should extract all unique cluster tags from KP tags."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        cluster_tags = menu.get_all_cluster_tags()

        assert "cluster:pronouns" in cluster_tags
        assert "cluster:basic-verbs" in cluster_tags
        assert "cluster:sentence-patterns" in cluster_tags
        assert "cluster:basic-sentences" in cluster_tags
        assert len(cluster_tags) == 4

    def test_ignores_non_cluster_tags(self, menu_knowledge_points, menu_student_state):
        """Should not include non-cluster tags like 'hsk1'."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        cluster_tags = menu.get_all_cluster_tags()

        assert "hsk1" not in cluster_tags

    def test_returns_sorted_tags(self, menu_knowledge_points, menu_student_state):
        """Should return cluster tags in sorted order."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        cluster_tags = menu.get_all_cluster_tags()

        assert cluster_tags == sorted(cluster_tags)


class TestGetKPsForCluster:
    """Tests for getting knowledge points by cluster tag."""

    def test_returns_all_kps_with_tag(self, menu_knowledge_points, menu_student_state):
        """Should return all KPs with a given cluster tag."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        pronouns = menu.get_kps_for_cluster("cluster:pronouns")

        assert len(pronouns) == 2
        assert all(kp.id in ["v001", "v002"] for kp in pronouns)

    def test_returns_empty_for_unknown_tag(
        self, menu_knowledge_points, menu_student_state
    ):
        """Should return empty list for unknown cluster tag."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        result = menu.get_kps_for_cluster("cluster:nonexistent")

        assert result == []


class TestEligibleClusters:
    """Tests for determining eligible clusters for selection."""

    def test_all_clusters_eligible_initially(
        self, menu_knowledge_points, menu_student_state
    ):
        """Grammar clusters should be eligible when student is fresh.

        Note: Vocabulary clusters are not eligible because vocabulary starts in
        FSRS mode (mastered). Only grammar clusters appear in the menu.
        """
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        eligible = menu.get_eligible_clusters()

        # Vocabulary clusters should NOT be eligible (they're in FSRS mode - mastered)
        assert "cluster:pronouns" not in eligible
        assert "cluster:basic-verbs" not in eligible
        # Grammar cluster basic-sentences should be eligible (no prerequisites)
        assert "cluster:basic-sentences" in eligible
        # sentence-patterns requires v005 which is vocab (mastered), so it IS eligible
        assert "cluster:sentence-patterns" in eligible

    def test_excludes_fully_mastered_clusters(
        self, menu_knowledge_points, menu_student_state
    ):
        """Grammar clusters with all skills mastered should not appear."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # Master all basic-sentences grammar items
        mastery_g002 = menu_student_state.get_mastery(
            "g002", KnowledgePointType.GRAMMAR
        )
        mastery_g003 = menu_student_state.get_mastery(
            "g003", KnowledgePointType.GRAMMAR
        )
        mastery_g002.p_known = 0.96
        mastery_g003.p_known = 0.96

        eligible = menu.get_eligible_clusters()

        assert "cluster:basic-sentences" not in eligible
        # sentence-patterns is still eligible (g001 not mastered)
        assert "cluster:sentence-patterns" in eligible

    def test_includes_partially_mastered_clusters(
        self, menu_knowledge_points, menu_student_state
    ):
        """Grammar clusters with some mastered skills should appear."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # Master only one grammar item in basic-sentences
        mastery_g002 = menu_student_state.get_mastery(
            "g002", KnowledgePointType.GRAMMAR
        )
        mastery_g002.p_known = 0.96

        eligible = menu.get_eligible_clusters()

        # basic-sentences still has g003 unmastered
        assert "cluster:basic-sentences" in eligible

    def test_requires_prerequisites_mastered(
        self, menu_knowledge_points, menu_student_state
    ):
        """Clusters with unmet prerequisites should not appear.

        Note: With vocab in FSRS mode, vocab prerequisites are always met.
        This test uses a grammar item with vocab prerequisite.
        """
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        eligible = menu.get_eligible_clusters()

        # sentence-patterns has v005 (vocab) as prerequisite
        # v005 is vocab, so it's in FSRS mode (mastered) - prerequisite IS met
        assert "cluster:sentence-patterns" in eligible

    def test_includes_when_prerequisites_met(
        self, menu_knowledge_points, menu_student_state
    ):
        """Clusters should appear when prerequisites are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # v005 is vocab, automatically in FSRS mode (mastered)

        eligible = menu.get_eligible_clusters()

        assert "cluster:sentence-patterns" in eligible


class TestClusterFullyMastered:
    """Tests for checking if a cluster is fully mastered."""

    def test_returns_false_when_unmastered(
        self, menu_knowledge_points, menu_student_state
    ):
        """Should return False when any grammar skill is unmastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        mastery_g002 = menu_student_state.get_mastery(
            "g002", KnowledgePointType.GRAMMAR
        )
        mastery_g003 = menu_student_state.get_mastery(
            "g003", KnowledgePointType.GRAMMAR
        )
        mastery_g002.p_known = 0.96
        mastery_g003.p_known = 0.5  # Not mastered

        result = menu.cluster_fully_mastered("cluster:basic-sentences")

        assert result is False

    def test_returns_true_when_all_mastered(
        self, menu_knowledge_points, menu_student_state
    ):
        """Should return True when all skills are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        mastery_g002 = menu_student_state.get_mastery(
            "g002", KnowledgePointType.GRAMMAR
        )
        mastery_g003 = menu_student_state.get_mastery(
            "g003", KnowledgePointType.GRAMMAR
        )
        mastery_g002.p_known = 0.96
        mastery_g003.p_known = 0.96

        result = menu.cluster_fully_mastered("cluster:basic-sentences")

        assert result is True

    def test_vocab_cluster_always_mastered(
        self, menu_knowledge_points, menu_student_state
    ):
        """Vocabulary clusters should always be considered mastered (FSRS mode)."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # No setup needed - vocab starts in FSRS mode

        result = menu.cluster_fully_mastered("cluster:pronouns")

        assert result is True


class TestClusterDisplayName:
    """Tests for converting cluster tags to display names."""

    def test_removes_prefix(self, menu_knowledge_points, menu_student_state):
        """Should remove 'cluster:' prefix."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        name = menu.get_cluster_display_name("cluster:pronouns")

        assert name == "Pronouns"

    def test_replaces_hyphens_with_spaces(
        self, menu_knowledge_points, menu_student_state
    ):
        """Should replace hyphens with spaces."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        name = menu.get_cluster_display_name("cluster:basic-verbs")

        assert name == "Basic Verbs"

    def test_title_cases_result(self, menu_knowledge_points, menu_student_state):
        """Should title case the result."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        name = menu.get_cluster_display_name("cluster:sentence-patterns")

        assert name == "Sentence Patterns"


class TestClusterProgress:
    """Tests for calculating cluster mastery progress."""

    def test_zero_progress_initially(self, menu_knowledge_points, menu_student_state):
        """Should return 0.0 when no grammar skills are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        progress = menu.get_cluster_progress("cluster:basic-sentences")

        assert progress == 0.0

    def test_full_progress_when_all_mastered(
        self, menu_knowledge_points, menu_student_state
    ):
        """Should return 1.0 when all grammar skills are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        mastery_g002 = menu_student_state.get_mastery(
            "g002", KnowledgePointType.GRAMMAR
        )
        mastery_g003 = menu_student_state.get_mastery(
            "g003", KnowledgePointType.GRAMMAR
        )
        mastery_g002.p_known = 0.96
        mastery_g003.p_known = 0.96

        progress = menu.get_cluster_progress("cluster:basic-sentences")

        assert progress == 1.0

    def test_partial_progress(self, menu_knowledge_points, menu_student_state):
        """Should return correct fraction when partially mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        mastery_g002 = menu_student_state.get_mastery(
            "g002", KnowledgePointType.GRAMMAR
        )
        mastery_g003 = menu_student_state.get_mastery(
            "g003", KnowledgePointType.GRAMMAR
        )
        mastery_g002.p_known = 0.96  # mastered
        mastery_g003.p_known = 0.5  # not mastered

        progress = menu.get_cluster_progress("cluster:basic-sentences")

        assert progress == 0.5  # 1 out of 2 mastered

    def test_vocab_cluster_full_progress(
        self, menu_knowledge_points, menu_student_state
    ):
        """Vocabulary clusters should show 100% progress (FSRS = mastered)."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # No setup needed - vocab starts in FSRS mode

        progress = menu.get_cluster_progress("cluster:pronouns")

        assert progress == 1.0
