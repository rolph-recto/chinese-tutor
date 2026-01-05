from models import StudentMastery, StudentState, KnowledgePoint


def update_mastery(mastery: StudentMastery, correct: bool) -> float:
    """
    Update the probability that the student knows the skill using Bayesian Knowledge Tracing.

    Uses the standard BKT update equations:
    - If correct: P(L|correct) = P(L) * (1 - P(S)) / P(correct)
    - If incorrect: P(L|incorrect) = P(L) * P(S) / P(incorrect)

    Then applies the learning/transition probability.
    """
    p_l = mastery.p_known
    p_t = mastery.p_transit
    p_s = mastery.p_slip
    p_g = mastery.p_guess

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
    """
    if not knowledge_points:
        return None

    def mastery_score(kp: KnowledgePoint) -> float:
        mastery = student_state.get_mastery(kp.id)
        # Distance from 0.5 - lower is better (more informative)
        return abs(mastery.p_known - 0.5)

    return min(knowledge_points, key=mastery_score)
