from datetime import datetime, timezone

from fsrs_scheduler import (
    get_fsrs_due_date,
    initialize_fsrs_for_mastery,
    is_fsrs_due,
)
from models import (
    KnowledgePoint,
    KnowledgePointType,
    SchedulingMode,
    StudentMastery,
    StudentState,
)


# Constants
MASTERY_THRESHOLD = 0.8      # KP considered "mastered" (80%)
FRONTIER_THRESHOLD = 0.3     # KP on frontier if below this
REVIEW_WEIGHT = 0.7          # 70% weight for review items
FRONTIER_WEIGHT = 0.3        # 30% weight for new learning
DECAY_RATE_PER_WEEK = 0.05   # 5% mastery decay per week of inactivity


def apply_mastery_decay(student_state: StudentState) -> None:
    """
    Apply time-based decay to BKT mastery values only.
    FSRS items use the FSRS algorithm for scheduling (no manual decay).
    """
    now = datetime.now()
    for mastery in student_state.masteries.values():
        # Only apply decay to BKT-mode items
        if mastery.scheduling_mode != SchedulingMode.BKT:
            continue

        if mastery.last_practiced is None:
            continue

        time_since_practice = now - mastery.last_practiced
        weeks_elapsed = time_since_practice.total_seconds() / (7 * 24 * 3600)

        if weeks_elapsed > 0:
            decay = DECAY_RATE_PER_WEEK * weeks_elapsed
            mastery.p_known = max(0.0, mastery.p_known - decay)


def check_and_transition_to_fsrs(mastery: StudentMastery) -> bool:
    """
    Check if a knowledge point should transition from BKT to FSRS.

    Transition occurs when:
    - Currently in BKT mode
    - p_known >= MASTERY_THRESHOLD

    Returns True if transition occurred.
    """
    if mastery.scheduling_mode == SchedulingMode.FSRS:
        return False  # Already in FSRS

    if mastery.p_known >= MASTERY_THRESHOLD:
        initialize_fsrs_for_mastery(mastery)
        return True

    return False


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
        mastery = student_state.get_mastery(prereq_id)
        if mastery.p_known < MASTERY_THRESHOLD:
            return False
    return True


def is_on_frontier(
    kp: KnowledgePoint,
    student_state: StudentState,
    kp_dict: dict[str, KnowledgePoint],
) -> bool:
    """
    A knowledge point is on the frontier if:
    - All its prerequisites are mastered (p_known >= MASTERY_THRESHOLD)
    - The KP itself is not yet mastered (p_known < MASTERY_THRESHOLD)
    """
    mastery = student_state.get_mastery(kp.id)
    if mastery.p_known >= MASTERY_THRESHOLD:
        return False
    return prerequisites_met(kp, student_state, kp_dict)


def needs_review(kp: KnowledgePoint, student_state: StudentState) -> bool:
    """
    A knowledge point needs review if:
    - BKT mode: was previously practiced but mastery dropped below threshold
    - FSRS mode: is past its due date
    """
    mastery = student_state.get_mastery(kp.id)

    if mastery.scheduling_mode == SchedulingMode.FSRS:
        return is_fsrs_due(mastery)

    # BKT mode
    return (
        mastery.last_practiced is not None
        and mastery.p_known < MASTERY_THRESHOLD
    )


def calculate_kp_score(
    kp: KnowledgePoint,
    student_state: StudentState,
    kp_dict: dict[str, KnowledgePoint],
    prefer_type: KnowledgePointType | None,
) -> float:
    """
    Calculate a priority score for a knowledge point.
    Higher score = higher priority for selection.

    Handles both BKT and FSRS modes:
    - BKT: Uses mastery-based scoring (original logic)
    - FSRS: Prioritizes overdue items based on how overdue they are
    """
    mastery = student_state.get_mastery(kp.id)
    score = 0.0

    if mastery.scheduling_mode == SchedulingMode.FSRS:
        # FSRS mode: score based on due date
        due = get_fsrs_due_date(mastery)
        if due is not None:
            now = datetime.now(timezone.utc)
            due_utc = due.replace(tzinfo=timezone.utc) if due.tzinfo is None else due

            if now >= due_utc:
                # Overdue: higher score for more overdue items
                overdue_hours = (now - due_utc).total_seconds() / 3600
                # Cap at 168 hours (1 week) to avoid extreme values
                score = min(overdue_hours / 168, 1.0) * REVIEW_WEIGHT + 0.5
            else:
                # Not yet due: minimal score (can still be selected if nothing else)
                hours_until_due = (due_utc - now).total_seconds() / 3600
                score = max(0.0, 0.1 - hours_until_due / 1000)
    else:
        # BKT mode: original scoring logic
        # Review component: lower mastery = higher priority
        if needs_review(kp, student_state):
            score += REVIEW_WEIGHT * (1 - mastery.p_known)

        # Frontier component: new learnable items get bonus
        if is_on_frontier(kp, student_state, kp_dict):
            score += FRONTIER_WEIGHT

    # Interleaving bonus: prefer the opposite type for variety (applies to both modes)
    if prefer_type is not None and kp.type == prefer_type:
        score += 0.1  # Small bonus for variety

    return score


def select_next_knowledge_point(
    student_state: StudentState,
    knowledge_points: list[KnowledgePoint],
) -> KnowledgePoint | None:
    """
    Select the next knowledge point to test using comprehensive scheduling.

    Algorithm:
    1. Apply time decay to all masteries
    2. Score all knowledge points based on:
       - Review urgency (70% weight)
       - Frontier expansion (30% weight)
       - Interleaving bonus
    3. Select the highest scoring knowledge point
    """
    if not knowledge_points:
        return None

    # Apply time decay
    apply_mastery_decay(student_state)

    # Build KP dictionary for prerequisite lookups
    kp_dict = {kp.id: kp for kp in knowledge_points}

    # Determine preferred type for interleaving (opposite of last)
    prefer_type: KnowledgePointType | None = None
    if student_state.last_kp_type == KnowledgePointType.VOCABULARY:
        prefer_type = KnowledgePointType.GRAMMAR
    elif student_state.last_kp_type == KnowledgePointType.GRAMMAR:
        prefer_type = KnowledgePointType.VOCABULARY

    # Score all knowledge points
    scored_kps = []
    for kp in knowledge_points:
        mastery = student_state.get_mastery(kp.id)

        # For BKT items, check prerequisites
        # For FSRS items, prerequisites are already satisfied (was mastered)
        if mastery.scheduling_mode == SchedulingMode.BKT:
            if not prerequisites_met(kp, student_state, kp_dict):
                continue

        score = calculate_kp_score(kp, student_state, kp_dict, prefer_type)
        scored_kps.append((score, kp))

    if not scored_kps:
        # Fallback: return any unmastered KP without checking prerequisites
        for kp in knowledge_points:
            mastery = student_state.get_mastery(kp.id)
            if mastery.p_known < MASTERY_THRESHOLD:
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
    Also checks for BKT -> FSRS transition after stats are updated.
    """
    mastery.last_practiced = datetime.now()
    mastery.practice_count += 1

    if correct:
        mastery.correct_count += 1
        mastery.consecutive_correct += 1
    else:
        mastery.consecutive_correct = 0

    # Check for transition to FSRS after updating stats
    check_and_transition_to_fsrs(mastery)
