"""
FSRS integration module for long-term retention scheduling.

This module provides functions to:
1. Convert between our FSRSState model and py-fsrs Card objects
2. Initialize FSRS cards when transitioning from BKT
3. Process reviews and update FSRS state
4. Calculate due dates and retrievability
"""

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State

from models import FSRSState, SchedulingMode, StudentMastery


# Global FSRS scheduler with default parameters
# desired_retention=0.9 means we aim for 90% recall probability
_scheduler = Scheduler()


def get_scheduler() -> Scheduler:
    """Get the global FSRS scheduler instance."""
    return _scheduler


def fsrs_state_to_card(fsrs_state: FSRSState) -> Card:
    """Convert our FSRSState model to a py-fsrs Card object."""
    card = Card()
    card.stability = fsrs_state.stability
    card.difficulty = fsrs_state.difficulty
    if fsrs_state.due:
        card.due = fsrs_state.due.replace(tzinfo=timezone.utc)
    if fsrs_state.last_review:
        card.last_review = fsrs_state.last_review.replace(tzinfo=timezone.utc)
    card.state = State(fsrs_state.state)
    card.step = fsrs_state.step
    return card


def card_to_fsrs_state(card: Card) -> FSRSState:
    """Convert a py-fsrs Card object to our FSRSState model."""
    return FSRSState(
        stability=card.stability,
        difficulty=card.difficulty,
        due=card.due.replace(tzinfo=None) if card.due else None,
        last_review=card.last_review.replace(tzinfo=None) if card.last_review else None,
        state=card.state.value,
        step=card.step,
    )


def initialize_fsrs_for_mastery(mastery: StudentMastery) -> None:
    """
    Initialize FSRS state when a knowledge point transitions from BKT.

    This is called when p_known >= MASTERY_THRESHOLD (0.8).
    The card starts fresh and we do an initial "Good" review to establish baseline.
    """
    # Create a new card and do an initial "Good" review to establish baseline
    card = Card()
    scheduler = get_scheduler()
    card, _ = scheduler.review_card(card, Rating.Good)

    # Store the FSRS state
    mastery.fsrs_state = card_to_fsrs_state(card)
    mastery.scheduling_mode = SchedulingMode.FSRS
    mastery.transitioned_to_fsrs_at = datetime.now()


def process_fsrs_review(mastery: StudentMastery, correct: bool) -> None:
    """
    Process a review for a knowledge point in FSRS mode.

    Maps the binary correct/incorrect to FSRS ratings:
    - Correct: Rating.Good (remembered)
    - Incorrect: Rating.Again (forgot)
    """
    if mastery.fsrs_state is None:
        raise ValueError("Cannot process FSRS review without FSRS state")

    # Convert stored state to Card
    card = fsrs_state_to_card(mastery.fsrs_state)

    # Map binary response to FSRS rating
    rating = Rating.Good if correct else Rating.Again

    # Process the review
    scheduler = get_scheduler()
    card, _ = scheduler.review_card(card, rating)

    # Update the stored state
    mastery.fsrs_state = card_to_fsrs_state(card)


def get_fsrs_due_date(mastery: StudentMastery) -> datetime | None:
    """
    Get the due date for an FSRS-scheduled knowledge point.
    Returns None if not in FSRS mode or no due date set.
    """
    if mastery.scheduling_mode != SchedulingMode.FSRS:
        return None
    if mastery.fsrs_state is None:
        return None
    return mastery.fsrs_state.due


def get_fsrs_retrievability(mastery: StudentMastery) -> float | None:
    """
    Get current retrievability (probability of recall) for an FSRS card.
    Returns None if not in FSRS mode.
    """
    if mastery.scheduling_mode != SchedulingMode.FSRS:
        return None
    if mastery.fsrs_state is None:
        return None

    card = fsrs_state_to_card(mastery.fsrs_state)
    scheduler = get_scheduler()
    return scheduler.get_card_retrievability(card)


def is_fsrs_due(mastery: StudentMastery) -> bool:
    """Check if an FSRS-scheduled knowledge point is due for review."""
    due = get_fsrs_due_date(mastery)
    if due is None:
        return False
    now = datetime.now(timezone.utc)
    due_utc = due.replace(tzinfo=timezone.utc) if due.tzinfo is None else due
    return now >= due_utc
