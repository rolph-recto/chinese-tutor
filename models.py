from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

import fsrs

_scheduler = fsrs.Scheduler()

def get_scheduler() -> fsrs.Scheduler:
    """Get the global FSRS scheduler instance."""
    return _scheduler

class KnowledgePointType(str, Enum):
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"

class FSRSState(BaseModel):
    """
    Stores FSRS card state. These fields mirror the py-fsrs Card class
    but are stored as primitives for JSON serialization with Pydantic.
    """
    stability: float | None = None
    difficulty: float | None = None
    due: datetime | None = None
    last_review: datetime | None = None
    state: int = 1  # 0=New, 1=Learning, 2=Review, 3=Relearning
    step: int | None = 0  # Learning step (None when in Review state)

    def to_card(self) -> fsrs.Card:
        """Convert our FSRSState model to a py-fsrs Card object."""
        card = fsrs.Card()
        card.stability = self.stability
        card.difficulty = self.difficulty
        if self.due:
            card.due = self.due.replace(tzinfo=timezone.utc)

        if self.last_review:
            card.last_review = self.last_review.replace(tzinfo=timezone.utc)

        card.state = fsrs.State(self.state)
        card.step = self.step
        return card

    @classmethod
    def from_fsrs_card(_cls, card: fsrs.Card) -> FSRSState:
        """Convert a py-fsrs Card object to our FSRSState model."""
        return FSRSState(
            stability=card.stability,
            difficulty=card.difficulty,
            due=card.due.replace(tzinfo=None) if card.due else None,
            last_review=card.last_review.replace(tzinfo=None) if card.last_review else None,
            state=card.state.value,
            step=card.step,
        )

class KnowledgePoint(BaseModel):
    id: str
    type: KnowledgePointType
    chinese: str
    pinyin: str
    english: str
    tags: list[str] = Field(default_factory=list)  # e.g., ["hsk1", "cluster:pronouns"]
    prerequisites: list[str] = Field(default_factory=list)


class Exercise(BaseModel):
    id: str
    knowledge_point_ids: list[str]
    difficulty: float = Field(ge=0.0, le=1.0)


class SegmentedTranslationExercise(Exercise):
    english_sentence: str
    chinese_chunks: list[str]
    correct_order: list[int]


class MinimalPairOption(BaseModel):
    chinese: str
    pinyin: str
    english: str


class MinimalPairExercise(Exercise):
    target_chinese: str
    target_pinyin: str
    target_english: str
    options: list[MinimalPairOption]
    correct_index: int


class MultipleChoiceVocabExercise(Exercise):
    """Multiple choice vocabulary exercise (both directions)."""
    direction: str  # "chinese_to_english" or "english_to_chinese"
    prompt: str  # The word being asked about
    prompt_pinyin: str  # Pinyin (shown when prompt is Chinese)
    options: list[str]  # 4 answer choices
    correct_index: int  # Index of correct answer (0-3)


class StudentMastery(BaseModel):
    knowledge_point_id: str

    # Practice stats
    last_practiced: datetime | None = None
    practice_count: int = 0
    correct_count: int = 0
    consecutive_correct: int = 0

    # FSRS state for spaced repetition scheduling
    fsrs_state: FSRSState | None = None

    @property
    def is_mastered(self) -> bool:
        """Returns True if skill has been practiced (has FSRS state)."""
        return self.fsrs_state is not None

    @property
    def due_date(self) -> datetime | None:
        """
        Get the due date for a knowledge point.
        Returns None if FSRS state not initialized.
        """
        if self.fsrs_state is None:
            return None

        return self.fsrs_state.due

    @property
    def is_due(self) -> bool:
        """Check if an FSRS-scheduled knowledge point is due for review."""
        if self.due_date is None:
            return False

        now = datetime.now(timezone.utc)
        if self.due_date.tzinfo is None:
            due_utc = self.due_date.replace(tzinfo=timezone.utc)

        else:
            due_utc = self.due_date

        return now >= due_utc

    @property
    def retrievability(self) -> float | None:
        """
        Get current retrievability (probability of recall) for a knowledge point.
        Returns None if FSRS state not initialized.
        """
        if self.fsrs_state is None:
            return None

        card = self.fsrs_state.to_card()
        scheduler = get_scheduler()
        return scheduler.get_card_retrievability(card)

    def initialize_fsrs(self) -> None:
        """
        Initialize FSRS state for a new knowledge point.

        Creates a fresh card and does an initial "Good" review to establish baseline
        scheduling parameters.
        """
        # Create a new card and do an initial "Good" review to establish baseline
        card = fsrs.Card()
        scheduler = get_scheduler()
        card, _ = scheduler.review_card(card, fsrs.Rating.Good)

        # Store the FSRS state
        self.fsrs_state = FSRSState.from_fsrs_card(card)

    def process_review(self, correct: bool) -> fsrs.ReviewLog:
        """
        Process a review for a knowledge point in FSRS mode.

        Maps the binary correct/incorrect to FSRS ratings:
        - Correct: Rating.Good (remembered)
        - Incorrect: Rating.Again (forgot)
        """
        if self.fsrs_state is None:
            raise ValueError("Cannot process FSRS review without FSRS state")

        # Convert stored state to Card
        card = self.fsrs_state.to_card()

        # Map binary response to FSRS rating
        rating = fsrs.Rating.Good if correct else fsrs.Rating.Again

        # Process the review
        scheduler = get_scheduler()
        card, review_log = scheduler.review_card(card, rating)

        # Update the stored state
        self.fsrs_state = FSRSState.from_fsrs_card(card)
        return review_log

class StudentState(BaseModel):
    masteries: dict[str, StudentMastery] = Field(default_factory=dict)
    last_kp_type: KnowledgePointType | None = None

    def get_mastery(
        self,
        knowledge_point_id: str,
        kp_type: KnowledgePointType | None = None,
    ) -> StudentMastery:
        """
        Get or create mastery for a knowledge point.

        Args:
            knowledge_point_id: The ID of the knowledge point.
            kp_type: The type of knowledge point (unused, kept for API compatibility).

        Returns:
            The StudentMastery object for this knowledge point.
        """
        if knowledge_point_id not in self.masteries:
            # All items use FSRS - FSRS state will be initialized by caller
            mastery = StudentMastery(knowledge_point_id=knowledge_point_id)
            self.masteries[knowledge_point_id] = mastery
        return self.masteries[knowledge_point_id]


class SessionState(BaseModel):
    """Tracks the current session's scheduling state."""
    exercises_completed: int = 0
