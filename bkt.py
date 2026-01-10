from fsrs_scheduler import get_fsrs_retrievability, process_fsrs_review
from models import KnowledgePoint, SchedulingMode, StudentMastery, StudentState


def update_mastery(mastery: StudentMastery, correct: bool) -> float:
    """
    Update mastery based on the scheduling mode.

    - BKT mode: Uses Bayesian Knowledge Tracing update equations
    - FSRS mode: Delegates to FSRS scheduler

    Returns the updated p_known value (or retrievability for FSRS).
    """
    if mastery.scheduling_mode == SchedulingMode.FSRS:
        # Process FSRS review
        process_fsrs_review(mastery, correct)
        # Return retrievability as equivalent to p_known
        retrievability = get_fsrs_retrievability(mastery)
        return retrievability if retrievability is not None else 1.0

    # BKT mode: requires BKT parameters to be set
    if mastery.p_known is None:
        raise ValueError(
            f"Cannot update BKT for mastery {mastery.knowledge_point_id} "
            "without BKT state (p_known is None)"
        )

    p_l = mastery.p_known
    p_t = mastery.p_transit if mastery.p_transit is not None else 0.3
    p_s = mastery.p_slip if mastery.p_slip is not None else 0.1
    p_g = mastery.p_guess if mastery.p_guess is not None else 0.2

    if correct:
        p_correct = p_l * (1 - p_s) + (1 - p_l) * p_g
        p_l_given_obs = (p_l * (1 - p_s)) / p_correct if p_correct > 0 else p_l
    else:
        p_incorrect = p_l * p_s + (1 - p_l) * (1 - p_g)
        p_l_given_obs = (p_l * p_s) / p_incorrect if p_incorrect > 0 else p_l

    # Apply learning transition
    p_l_new = p_l_given_obs + (1 - p_l_given_obs) * p_t

    mastery.p_known = p_l_new
    return p_l_new


def select_next_knowledge_point(
    student_state: StudentState, knowledge_points: list[KnowledgePoint]
) -> KnowledgePoint | None:
    """
    Select the next knowledge point to test.

    Strategy: Pick the knowledge point with mastery closest to 0.5,
    as this provides the most informative assessment.
    For FSRS items (vocabulary), use 0.5 as default since they don't have p_known.
    """
    if not knowledge_points:
        return None

    def mastery_score(kp: KnowledgePoint) -> float:
        mastery = student_state.get_mastery(kp.id, kp.type)
        # FSRS items don't have p_known, use 0.5 (neutral)
        p_known = mastery.p_known if mastery.p_known is not None else 0.5
        # Distance from 0.5 - lower is better (more informative)
        return abs(p_known - 0.5)

    return min(knowledge_points, key=mastery_score)
