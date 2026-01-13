from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

import fsrs

_scheduler = fsrs.Scheduler()


def get_scheduler() -> fsrs.Scheduler:
    """Get the global FSRS scheduler instance."""
    return _scheduler


class KnowledgePointType(str, Enum):
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"


# ============================================================================
# Dynamic Schema Models
# ============================================================================


class ColumnType(str, Enum):
    """Supported column types for user-defined tables."""

    TEXT = "TEXT"
    INTEGER = "INTEGER"
    REAL = "REAL"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"
    DATE = "DATE"
    DATETIME = "DATETIME"


class ColumnDefinition(BaseModel):
    """Definition of a column in a user-defined table."""

    name: str
    type: ColumnType
    required: bool = True
    default: Any = None


class UserTableMeta(BaseModel):
    """Metadata about a user-defined table."""

    table_id: str
    table_name: str
    columns: list[ColumnDefinition]

    def get_column(self, name: str) -> ColumnDefinition | None:
        """Get a column definition by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def validate_row(self, row_values: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate row values against column definitions.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: list[str] = []

        for col in self.columns:
            if col.name not in row_values:
                if col.required and col.default is None:
                    errors.append(f"Missing required column: {col.name}")
                continue

            value = row_values[col.name]
            if value is None:
                if col.required:
                    errors.append(f"Column {col.name} cannot be null")
                continue

            # Type validation
            if not self._validate_type(value, col.type):
                errors.append(
                    f"Column {col.name}: expected {col.type.value}, "
                    f"got {type(value).__name__}"
                )

        return len(errors) == 0, errors

    def _validate_type(self, value: Any, col_type: ColumnType) -> bool:
        """Validate a value against a column type."""
        if col_type == ColumnType.TEXT:
            return isinstance(value, str)
        elif col_type == ColumnType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif col_type == ColumnType.REAL:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif col_type == ColumnType.BOOLEAN:
            return isinstance(value, bool)
        elif col_type == ColumnType.JSON:
            return isinstance(value, (dict, list))
        elif col_type == ColumnType.DATE:
            # Accept ISO date strings or date objects
            if isinstance(value, str):
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                    return True
                except ValueError:
                    return False
            return False
        elif col_type == ColumnType.DATETIME:
            # Accept ISO datetime strings or datetime objects
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value)
                    return True
                except ValueError:
                    return False
            return False
        return False


class UserRow(BaseModel):
    """A row in a user-defined table."""

    table_id: str
    row_id: str
    row_values: dict[str, Any]


class RowReference(BaseModel):
    """Reference to a specific row in a user-defined table."""

    table_id: str
    row_id: str


# ============================================================================
# FSRS and Mastery Models
# ============================================================================


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
            last_review=card.last_review.replace(tzinfo=None)
            if card.last_review
            else None,
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


class StudentMastery(BaseModel):
    # Composite key for dynamic schema
    table_id: str
    row_id: str

    # FSRS state for spaced repetition scheduling
    fsrs_state: FSRSState | None = None

    @property
    def knowledge_point_id(self) -> str:
        """Backwards compatibility: returns row_id for legacy code."""
        return self.row_id

    @property
    def reference(self) -> RowReference:
        """Get a reference to the row this mastery tracks."""
        return RowReference(table_id=self.table_id, row_id=self.row_id)

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

    def initialize_fsrs(self, rating: fsrs.Rating) -> None:
        """
        Initialize FSRS state for a new knowledge point.

        Creates a fresh card and does an initial "Good" review to establish baseline
        scheduling parameters.
        """
        # Create a new card and do an initial "Good" review to establish baseline
        card = fsrs.Card()
        scheduler = get_scheduler()
        card, _ = scheduler.review_card(card, rating)

        # Store the FSRS state
        self.fsrs_state = FSRSState.from_fsrs_card(card)

    def process_review(self, rating: fsrs.Rating) -> fsrs.ReviewLog:
        """
        Process a review for a knowledge point in FSRS mode.

        The rating is passed in directly from the caller:
        - Incorrect answers: Rating.Again
        - Correct answers: User chooses from Again, Hard, Good, or Easy
        """
        self.initialize_fsrs(rating)
        assert self.fsrs_state is not None

        # Convert stored state to Card
        card = self.fsrs_state.to_card()

        # Process the review
        scheduler = get_scheduler()
        card, review_log = scheduler.review_card(card, rating)

        # Update the stored state
        self.fsrs_state = FSRSState.from_fsrs_card(card)
        return review_log


class StudentState(BaseModel):
    masteries: dict[str, StudentMastery] = Field(default_factory=dict)

    # Default table ID for backwards compatibility with knowledge_points
    DEFAULT_TABLE_ID: str = "knowledge_points"

    @staticmethod
    def _make_key(table_id: str, row_id: str) -> str:
        """Create composite key for masteries dict."""
        return f"{table_id}:{row_id}"

    def get_mastery(
        self,
        row_id: str,
        kp_type: KnowledgePointType | None = None,  # kept for API compatibility
        *,
        table_id: str | None = None,
    ) -> StudentMastery:
        """
        Get or create mastery for a knowledge point.

        Args:
            row_id: The row ID (knowledge point ID for legacy code).
            kp_type: The type of knowledge point (unused, kept for API compatibility).
            table_id: The table ID (keyword-only, defaults to 'knowledge_points').

        Returns:
            The StudentMastery object for this row.
        """
        _ = kp_type  # Explicitly mark as unused
        if table_id is None:
            table_id = self.DEFAULT_TABLE_ID

        key = self._make_key(table_id, row_id)
        if key not in self.masteries:
            # All items use FSRS - FSRS state will be initialized by caller
            mastery = StudentMastery(table_id=table_id, row_id=row_id)
            self.masteries[key] = mastery
        return self.masteries[key]


class SessionState(BaseModel):
    """Tracks the current session's scheduling state."""

    exercises_completed: int = 0
