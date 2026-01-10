from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# Mastery threshold for transitioning from Learning Mode to Retention Mode
MASTERY_THRESHOLD = 0.95


class KnowledgePointType(str, Enum):
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"


class SchedulingMode(str, Enum):
    """Tracks which scheduling algorithm is active for a knowledge point."""
    BKT = "bkt"       # Initial learning phase
    FSRS = "fsrs"     # Long-term retention phase


class PracticeMode(str, Enum):
    """Current practice mode within Learning Mode."""
    BLOCKED = "blocked"          # Focused on single cluster
    INTERLEAVED = "interleaved"  # All Learning Mode skills


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

    # Scheduling mode determines which algorithm is active
    scheduling_mode: SchedulingMode = SchedulingMode.BKT

    # BKT parameters (only used when scheduling_mode == BKT)
    # None for FSRS-only items (vocabulary)
    p_known: float | None = Field(default=None, ge=0.0, le=1.0)
    p_transit: float | None = Field(default=None, ge=0.0, le=1.0)
    p_slip: float | None = Field(default=None, ge=0.0, le=1.0)
    p_guess: float | None = Field(default=None, ge=0.0, le=1.0)

    # Common practice stats (used by both modes)
    last_practiced: datetime | None = None
    practice_count: int = 0
    correct_count: int = 0
    consecutive_correct: int = 0

    # FSRS state (used when scheduling_mode == FSRS)
    fsrs_state: FSRSState | None = None

    # Timestamp when transitioned to FSRS
    transitioned_to_fsrs_at: datetime | None = None

    @property
    def is_mastered(self) -> bool:
        """Returns True if skill has reached mastery threshold."""
        if self.scheduling_mode == SchedulingMode.FSRS:
            return True  # FSRS items are always considered "mastered"
        return self.p_known is not None and self.p_known >= MASTERY_THRESHOLD


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
            kp_type: The type of knowledge point. Required when creating new mastery
                     to determine scheduling mode (VOCABULARY -> FSRS, GRAMMAR -> BKT).

        Returns:
            The StudentMastery object for this knowledge point.
        """
        if knowledge_point_id not in self.masteries:
            if kp_type == KnowledgePointType.VOCABULARY:
                # Vocabulary starts directly in FSRS mode (no BKT params)
                mastery = StudentMastery(
                    knowledge_point_id=knowledge_point_id,
                    scheduling_mode=SchedulingMode.FSRS,
                    # BKT params stay None
                )
                # Note: FSRS state will be initialized by the caller
                # to avoid circular imports with fsrs_scheduler
            else:
                # Grammar (and unknown types) start in BKT mode
                mastery = StudentMastery(
                    knowledge_point_id=knowledge_point_id,
                    scheduling_mode=SchedulingMode.BKT,
                    p_known=0.0,
                    p_transit=0.3,
                    p_slip=0.1,
                    p_guess=0.2,
                )
            self.masteries[knowledge_point_id] = mastery
        return self.masteries[knowledge_point_id]


class SessionState(BaseModel):
    """Tracks the current session's scheduling state."""
    practice_mode: PracticeMode = PracticeMode.INTERLEAVED
    active_cluster_tag: str | None = None  # e.g., "cluster:pronouns" during blocked practice
    learning_retention_ratio: float = 0.7  # 70% learning, 30% retention
    exercises_since_menu: int = 0
