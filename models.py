from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class KnowledgePointType(str, Enum):
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"


class SchedulingMode(str, Enum):
    """Tracks which scheduling algorithm is active for a knowledge point."""
    BKT = "bkt"       # Initial learning phase
    FSRS = "fsrs"     # Long-term retention phase


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
    hsk_level: int = Field(ge=1, le=6)
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


class StudentMastery(BaseModel):
    knowledge_point_id: str

    # BKT parameters (used during initial learning)
    p_known: float = Field(default=0.0, ge=0.0, le=1.0)
    p_transit: float = Field(default=0.3, ge=0.0, le=1.0)
    p_slip: float = Field(default=0.1, ge=0.0, le=1.0)
    p_guess: float = Field(default=0.2, ge=0.0, le=1.0)

    # Common practice stats
    last_practiced: datetime | None = None
    practice_count: int = 0
    correct_count: int = 0
    consecutive_correct: int = 0

    # Scheduling mode tracking
    scheduling_mode: SchedulingMode = SchedulingMode.BKT

    # FSRS state (populated when scheduling_mode == FSRS)
    fsrs_state: FSRSState | None = None

    # Timestamp when transitioned to FSRS
    transitioned_to_fsrs_at: datetime | None = None


class StudentState(BaseModel):
    masteries: dict[str, StudentMastery] = Field(default_factory=dict)
    last_kp_type: KnowledgePointType | None = None

    def get_mastery(self, knowledge_point_id: str) -> StudentMastery:
        if knowledge_point_id not in self.masteries:
            self.masteries[knowledge_point_id] = StudentMastery(
                knowledge_point_id=knowledge_point_id
            )
        return self.masteries[knowledge_point_id]
