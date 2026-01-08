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
    """Create knowledge points with cluster tags for menu testing."""
    return [
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
        KnowledgePoint(
            id="g001",
            type=KnowledgePointType.GRAMMAR,
            chinese="Subject + 是 + Noun",
            pinyin="Subject + shì + Noun",
            english="Subject is Noun",
            tags=["hsk1", "cluster:sentence-patterns"],
            prerequisites=["v005"],
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
        assert len(cluster_tags) == 3

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

    def test_returns_empty_for_unknown_tag(self, menu_knowledge_points, menu_student_state):
        """Should return empty list for unknown cluster tag."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        result = menu.get_kps_for_cluster("cluster:nonexistent")

        assert result == []


class TestEligibleClusters:
    """Tests for determining eligible clusters for selection."""

    def test_all_clusters_eligible_initially(self, menu_knowledge_points, menu_student_state):
        """All clusters should be eligible when student is fresh (except those with unmet prereqs)."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        eligible = menu.get_eligible_clusters()

        # pronouns and basic-verbs should be eligible (no prerequisites)
        assert "cluster:pronouns" in eligible
        assert "cluster:basic-verbs" in eligible
        # sentence-patterns requires v005 which is not mastered
        assert "cluster:sentence-patterns" not in eligible

    def test_excludes_fully_mastered_clusters(self, menu_knowledge_points, menu_student_state):
        """Clusters with all skills mastered should not appear."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # Master all pronouns
        menu_student_state.get_mastery("v001").p_known = 0.96
        menu_student_state.get_mastery("v002").p_known = 0.96

        eligible = menu.get_eligible_clusters()

        assert "cluster:pronouns" not in eligible
        assert "cluster:basic-verbs" in eligible

    def test_includes_partially_mastered_clusters(self, menu_knowledge_points, menu_student_state):
        """Clusters with some mastered skills should appear."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # Master only one pronoun
        menu_student_state.get_mastery("v001").p_known = 0.96

        eligible = menu.get_eligible_clusters()

        assert "cluster:pronouns" in eligible

    def test_requires_prerequisites_mastered(self, menu_knowledge_points, menu_student_state):
        """Clusters with unmet prerequisites should not appear."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # v005 is a prerequisite for sentence-patterns, but not mastered

        eligible = menu.get_eligible_clusters()

        assert "cluster:sentence-patterns" not in eligible

    def test_includes_when_prerequisites_met(self, menu_knowledge_points, menu_student_state):
        """Clusters should appear when prerequisites are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        # Master v005 (prerequisite for sentence-patterns)
        menu_student_state.get_mastery("v005").p_known = 0.96

        eligible = menu.get_eligible_clusters()

        assert "cluster:sentence-patterns" in eligible


class TestClusterFullyMastered:
    """Tests for checking if a cluster is fully mastered."""

    def test_returns_false_when_unmastered(self, menu_knowledge_points, menu_student_state):
        """Should return False when any skill is unmastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        menu_student_state.get_mastery("v001").p_known = 0.96
        menu_student_state.get_mastery("v002").p_known = 0.5

        result = menu.cluster_fully_mastered("cluster:pronouns")

        assert result is False

    def test_returns_true_when_all_mastered(self, menu_knowledge_points, menu_student_state):
        """Should return True when all skills are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        menu_student_state.get_mastery("v001").p_known = 0.96
        menu_student_state.get_mastery("v002").p_known = 0.96

        result = menu.cluster_fully_mastered("cluster:pronouns")

        assert result is True


class TestClusterDisplayName:
    """Tests for converting cluster tags to display names."""

    def test_removes_prefix(self, menu_knowledge_points, menu_student_state):
        """Should remove 'cluster:' prefix."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        name = menu.get_cluster_display_name("cluster:pronouns")

        assert name == "Pronouns"

    def test_replaces_hyphens_with_spaces(self, menu_knowledge_points, menu_student_state):
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
        """Should return 0.0 when no skills are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)

        progress = menu.get_cluster_progress("cluster:pronouns")

        assert progress == 0.0

    def test_full_progress_when_all_mastered(self, menu_knowledge_points, menu_student_state):
        """Should return 1.0 when all skills are mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        menu_student_state.get_mastery("v001").p_known = 0.96
        menu_student_state.get_mastery("v002").p_known = 0.96

        progress = menu.get_cluster_progress("cluster:pronouns")

        assert progress == 1.0

    def test_partial_progress(self, menu_knowledge_points, menu_student_state):
        """Should return correct fraction when partially mastered."""
        menu = TopicSelectionMenu(menu_knowledge_points, menu_student_state)
        menu_student_state.get_mastery("v001").p_known = 0.96
        menu_student_state.get_mastery("v002").p_known = 0.5

        progress = menu.get_cluster_progress("cluster:pronouns")

        assert progress == 0.5  # 1 out of 2 mastered
