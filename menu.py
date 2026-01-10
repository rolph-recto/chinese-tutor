"""
Topic Selection Menu module for student-driven topic selection.

This module generates and manages the topic selection menu based on cluster tags,
dynamically discovering clusters from knowledge point tags.
"""

from models import (
    KnowledgePoint,
    StudentState,
)


CLUSTER_TAG_PREFIX = "cluster:"


class TopicSelectionMenu:
    """Generates and manages the topic selection menu based on tags."""

    def __init__(
        self,
        knowledge_points: list[KnowledgePoint],
        student_state: StudentState,
    ):
        self.knowledge_points = {kp.id: kp for kp in knowledge_points}
        self.student_state = student_state

    def get_all_cluster_tags(self) -> list[str]:
        """Extract all unique cluster tags from knowledge points."""
        cluster_tags: set[str] = set()
        for kp in self.knowledge_points.values():
            for tag in kp.tags:
                if tag.startswith(CLUSTER_TAG_PREFIX):
                    cluster_tags.add(tag)
        return sorted(cluster_tags)

    def get_kps_for_cluster(self, cluster_tag: str) -> list[KnowledgePoint]:
        """Get all knowledge points with a given cluster tag."""
        return [
            kp for kp in self.knowledge_points.values()
            if cluster_tag in kp.tags
        ]

    def get_eligible_clusters(self) -> list[str]:
        """
        Returns cluster tags eligible for selection.

        A cluster is eligible if:
        1. At least one skill has p_known < 0.95 (unmastered)
        2. All prerequisite skills for KPs in the cluster are mastered
        """
        eligible = []
        for cluster_tag in self.get_all_cluster_tags():
            if self._has_unmastered_skills(cluster_tag) and \
               self._prerequisites_mastered(cluster_tag):
                eligible.append(cluster_tag)
        return eligible

    def _has_unmastered_skills(self, cluster_tag: str) -> bool:
        """Check if cluster has at least one unmastered skill (in BKT mode)."""
        for kp in self.get_kps_for_cluster(cluster_tag):
            mastery = self.student_state.get_mastery(kp.id, kp.type)
            if not mastery.is_mastered:
                return True
        return False

    def _prerequisites_mastered(self, cluster_tag: str) -> bool:
        """Check if all prerequisite KPs for this cluster's skills are mastered."""
        for kp in self.get_kps_for_cluster(cluster_tag):
            for prereq_id in kp.prerequisites:
                prereq_kp = self.knowledge_points.get(prereq_id)
                prereq_type = prereq_kp.type if prereq_kp else None
                prereq_mastery = self.student_state.get_mastery(prereq_id, prereq_type)
                if not prereq_mastery.is_mastered:
                    return False
        return True

    def cluster_fully_mastered(self, cluster_tag: str) -> bool:
        """Check if all skills in cluster are mastered."""
        for kp in self.get_kps_for_cluster(cluster_tag):
            mastery = self.student_state.get_mastery(kp.id, kp.type)
            if not mastery.is_mastered:
                return False
        return True

    def get_cluster_display_name(self, cluster_tag: str) -> str:
        """Convert cluster tag to display name (e.g., 'cluster:pronouns' -> 'Pronouns')."""
        name = cluster_tag.removeprefix(CLUSTER_TAG_PREFIX)
        return name.replace("-", " ").title()

    def get_cluster_progress(self, cluster_tag: str) -> float:
        """Calculate percentage of skills mastered in cluster."""
        kps = self.get_kps_for_cluster(cluster_tag)
        if not kps:
            return 0.0
        mastered = sum(
            1 for kp in kps
            if self.student_state.get_mastery(kp.id, kp.type).is_mastered
        )
        return mastered / len(kps)

    def display_menu(self) -> list[str]:
        """
        Print the topic selection menu to stdout.

        Returns the list of eligible cluster tags (in display order).
        """
        eligible = self.get_eligible_clusters()

        print("\n" + "=" * 60)
        print("TOPIC SELECTION MENU")
        print("=" * 60)

        if not eligible:
            print("No new topics available. Continue with retention practice.")
            return eligible

        for i, cluster_tag in enumerate(eligible, 1):
            name = self.get_cluster_display_name(cluster_tag)
            progress = self.get_cluster_progress(cluster_tag)
            kp_count = len(self.get_kps_for_cluster(cluster_tag))
            print(f"\n{i}. {name}")
            print(f"   {kp_count} skills, {progress:.0%} mastered")

        print("\n" + "-" * 60)
        return eligible
