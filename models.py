from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


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
