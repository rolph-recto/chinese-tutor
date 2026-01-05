from datetime import datetime, timedelta
from models import KnowledgePoint, KnowledgePointType, StudentMastery, StudentState


# Constants
MASTERY_THRESHOLD = 0.8      # KP considered "mastered" (80%)
FRONTIER_THRESHOLD = 0.3     # KP on frontier if below this
REVIEW_WEIGHT = 0.7          # 70% weight for review items
FRONTIER_WEIGHT = 0.3        # 30% weight for new learning
DECAY_RATE_PER_WEEK = 0.05   # 5% mastery decay per week of inactivity


def apply_mastery_decay(student_state: StudentState) -> None:
    """
    Apply time-based decay to all mastery values.
    Mastery decays by DECAY_RATE_PER_WEEK for each week since last practice.
    """
    now = datetime.now()
    for mastery in student_state.masteries.values():
        if mastery.last_practiced is None:
            continue

        time_since_practice = now - mastery.last_practiced
        weeks_elapsed = time_since_practice.total_seconds() / (7 * 24 * 3600)

        if weeks_elapsed > 0:
            decay = DECAY_RATE_PER_WEEK * weeks_elapsed
            mastery.p_known = max(0.0, mastery.p_known - decay)


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
    A knowledge point needs review if it was previously practiced
    but mastery has dropped below the threshold.
    """
    mastery = student_state.get_mastery(kp.id)
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
    """
    mastery = student_state.get_mastery(kp.id)
    score = 0.0

    # Review component: lower mastery = higher priority
    if needs_review(kp, student_state):
        score += REVIEW_WEIGHT * (1 - mastery.p_known)

    # Frontier component: new learnable items get bonus
    if is_on_frontier(kp, student_state, kp_dict):
        score += FRONTIER_WEIGHT

    # Interleaving bonus: prefer the opposite type for variety
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
        # Skip if prerequisites not met
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
    """
    mastery.last_practiced = datetime.now()
    mastery.practice_count += 1

    if correct:
        mastery.correct_count += 1
        mastery.consecutive_correct += 1
    else:
        mastery.consecutive_correct = 0
