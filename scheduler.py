"""
Exercise Scheduler implementing FSRS-based spaced repetition.

This module handles:
- Knowledge point selection based on FSRS retrievability
- Session composition
- Multi-skill exercise handling
- Prerequisite checking
"""

from datetime import datetime, timezone
from models import (
    KnowledgePoint,
    KnowledgePointType,
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
        mastery = self.student_state.get_mastery(kp_id, kp_type)

        # Initialize FSRS state for new items
        if mastery.fsrs_state is None:
            mastery.initialize_fsrs()

        return mastery

    # =========================================================================
    # Session Composition
    # =========================================================================

    def compose_session_queue(self, session_size: int | None = None) -> list[str]:
        """
        Compose exercise queue based on FSRS scheduling.
        Only includes items that are currently due.
        Prioritizes items with lowest retrievability (most overdue).
        """
        # Get all KPs with met prerequisites
        eligible = [
            kp_id for kp_id in self.knowledge_points
            if self._prerequisites_met(kp_id)
        ]

        if not eligible:
            return []

        # Filter to only due items
        due_items: list[str] = []
        for kp_id in eligible:
            mastery = self._get_mastery_for_kp(kp_id)
            if mastery.is_due:
                due_items.append(kp_id)

        if not due_items:
            return []

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
        is_correct: bool,
    ) -> None:
        """
        Update all skills associated with a multi-skill exercise.
        """
        for kp_id in kp_ids:
            mastery = self._get_mastery_for_kp(kp_id)
            mastery.process_review(is_correct)
            update_practice_stats(mastery, is_correct)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _prerequisites_met(self, kp_id: str) -> bool:
        """Check if all prerequisites for a KP are mastered."""
        kp = self.knowledge_points.get(kp_id)
        if not kp:
            return False

        for prereq_id in kp.prerequisites:
            prereq_mastery = self._get_mastery_for_kp(prereq_id)
            if not prereq_mastery.is_mastered:
                return False

        return True

    def get_next_due_time(self) -> datetime | None:
        """Get the earliest due time among all eligible knowledge points."""
        earliest_due: datetime | None = None
        for kp_id in self.knowledge_points:
            if not self._prerequisites_met(kp_id):
                continue
            mastery = self._get_mastery_for_kp(kp_id)
            if mastery.due_date is not None:
                if earliest_due is None or mastery.due_date < earliest_due:
                    earliest_due = mastery.due_date
        return earliest_due


# =========================================================================
# Standalone Functions (for backward compatibility)
# =========================================================================


def prerequisites_met(
    kp: KnowledgePoint,
    student_state: StudentState,
    kp_dict: dict[str, KnowledgePoint],
) -> bool:
    """
    Check if all prerequisites for a knowledge point are mastered.
    """
    for prereq_id in kp.prerequisites:
        if prereq_id not in kp_dict:
            continue
        prereq_kp = kp_dict[prereq_id]
        mastery = student_state.get_mastery(prereq_id, prereq_kp.type)
        # Initialize FSRS if needed
        if mastery.fsrs_state is None:
            mastery.initialize_fsrs()
        if not mastery.is_mastered:
            return False
    return True


def calculate_kp_score(
    kp: KnowledgePoint,
    student_state: StudentState,
    prefer_type: KnowledgePointType | None,
) -> float:
    """
    Calculate a priority score for a knowledge point.
    Higher score = higher priority for selection.
    Based on FSRS retrievability and due date.
    """
    mastery = student_state.get_mastery(kp.id, kp.type)

    # Initialize FSRS if needed
    if mastery.fsrs_state is None:
        mastery.initialize_fsrs()

    score = 0.0

    # Score based on due date
    if mastery.due_date is not None:
        now = datetime.now(timezone.utc)
        if mastery.due_date.tzinfo is None:
            due_utc = mastery.due_date.replace(tzinfo=timezone.utc)
        else:
            due_utc = mastery.due_date

        if now >= due_utc:
            # Overdue: higher score for more overdue items
            overdue_hours = (now - due_utc).total_seconds() / 3600
            # Cap at 168 hours (1 week) to avoid extreme values
            score = min(overdue_hours / 168, 1.0) * 0.7 + 0.5
        else:
            # Not yet due: minimal score (can still be selected if nothing else)
            hours_until_due = (due_utc - now).total_seconds() / 3600
            score = max(0.0, 0.1 - hours_until_due / 1000)

    # Interleaving bonus: prefer the opposite type for variety
    if prefer_type is not None and kp.type == prefer_type:
        score += 0.1  # Small bonus for variety

    return score


def select_next_knowledge_point(
    student_state: StudentState,
    knowledge_points: list[KnowledgePoint],
) -> KnowledgePoint | None:
    """
    Select the next knowledge point to test using FSRS scheduling.

    Algorithm:
    1. Score all knowledge points based on FSRS retrievability
    2. Apply interleaving bonus
    3. Select the highest scoring knowledge point
    """
    if not knowledge_points:
        return None

    # Build KP dictionary for prerequisite lookups
    kp_dict = {kp.id: kp for kp in knowledge_points}

    # Determine preferred type for interleaving (opposite of last)
    prefer_type: KnowledgePointType | None = None
    if student_state.last_kp_type == KnowledgePointType.VOCABULARY:
        prefer_type = KnowledgePointType.GRAMMAR
    elif student_state.last_kp_type == KnowledgePointType.GRAMMAR:
        prefer_type = KnowledgePointType.VOCABULARY

    # Score all knowledge points
    scored_kps: list[tuple[float, KnowledgePoint]] = []
    for kp in knowledge_points:
        # Check prerequisites
        if not prerequisites_met(kp, student_state, kp_dict):
            continue

        score = calculate_kp_score(kp, student_state, prefer_type)
        scored_kps.append((score, kp))

    if not scored_kps:
        # Fallback: return any KP without checking prerequisites
        for kp in knowledge_points:
            mastery = student_state.get_mastery(kp.id, kp.type)
            if not mastery.is_mastered:
                return kp
        return knowledge_points[0] if knowledge_points else None

    # Select highest scoring KP
    scored_kps.sort(key=lambda x: x[0], reverse=True)
    return scored_kps[0][1]


def update_practice_stats(
    mastery: StudentMastery,
    correct: bool,
) -> None:
    """
    Update practice statistics after an exercise.
    """
    mastery.last_practiced = datetime.now()
    mastery.practice_count += 1

    if correct:
        mastery.correct_count += 1
        mastery.consecutive_correct += 1
    else:
        mastery.consecutive_correct = 0
