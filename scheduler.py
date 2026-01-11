"""
Exercise Scheduler implementing FSRS-based spaced repetition.

This module handles:
- Knowledge point selection based on FSRS retrievability
- Session composition
- Multi-skill exercise handling
- Prerequisite checking
"""

from datetime import datetime

import fsrs

from models import (
    KnowledgePoint,
    SessionState,
    StudentMastery,
    StudentState,
)


class ExerciseScheduler:
    """
    Main scheduler implementing FSRS-based spaced repetition.
    """

    def __init__(
        self,
        knowledge_points: list[KnowledgePoint],
        student_state: StudentState,
        session_state: SessionState,
    ):
        self.knowledge_points = {kp.id: kp for kp in knowledge_points}
        self.knowledge_points_list = knowledge_points
        self.student_state = student_state
        self.session_state = session_state

    def _get_mastery_for_kp(self, kp_id: str) -> StudentMastery:
        """
        Get mastery for a knowledge point, initializing FSRS state if needed.
        """
        kp = self.knowledge_points.get(kp_id)
        kp_type = kp.type if kp else None
        return self.student_state.get_mastery(kp_id, kp_type)

    # =========================================================================
    # Session Composition
    # =========================================================================

    def compose_session_queue(self, session_size: int | None = None) -> list[str]:
        """
        Compose exercise queue based on FSRS scheduling.
        Only includes items that are currently due.
        Prioritizes items with lowest retrievability (most overdue).
        """
        # Filter to only due items
        due_items: list[str] = []
        for kp_id in self.knowledge_points:
            mastery = self._get_mastery_for_kp(kp_id)
            if mastery.is_due or mastery.due_date is None:
                due_items.append(kp_id)

        print(f"items due: {len(due_items)}")

        # Score and select based on FSRS retrievability
        scored: list[tuple[str, float]] = []
        for kp_id in due_items:
            mastery = self._get_mastery_for_kp(kp_id)
            if mastery.retrievability is not None:
                # Lower retrievability = higher priority (more overdue)
                scored.append((kp_id, 1.0 - mastery.retrievability))
            else:
                # No retrievability yet, give medium priority
                scored.append((kp_id, 0.5))

        scored.sort(key=lambda x: x[1], reverse=True)

        if session_size is not None:
            scored = scored[:session_size]

        return [kp_id for kp_id, _ in scored]

    # =========================================================================
    # Multi-Skill Exercise Handling
    # =========================================================================

    def update_multi_skill_exercise(
        self,
        kp_ids: list[str],
        rating: fsrs.Rating,
    ) -> None:
        """
        Update all skills associated with a multi-skill exercise.
        """
        for kp_id in kp_ids:
            mastery = self._get_mastery_for_kp(kp_id)
            mastery.process_review(rating)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def get_next_due_time(self) -> datetime | None:
        """Get the earliest due time among all eligible knowledge points."""
        earliest_due: datetime | None = None
        for kp_id in self.knowledge_points:
            mastery = self._get_mastery_for_kp(kp_id)
            if mastery.due_date is not None:
                if earliest_due is None or mastery.due_date < earliest_due:
                    earliest_due = mastery.due_date
        return earliest_due
