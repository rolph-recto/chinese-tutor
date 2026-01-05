from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class KnowledgePointType(str, Enum):
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"


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


class StudentMastery(BaseModel):
    knowledge_point_id: str
    p_known: float = Field(default=0.0, ge=0.0, le=1.0)
    p_transit: float = Field(default=0.3, ge=0.0, le=1.0)
    p_slip: float = Field(default=0.1, ge=0.0, le=1.0)
    p_guess: float = Field(default=0.2, ge=0.0, le=1.0)
    last_practiced: datetime | None = None
    practice_count: int = 0
    correct_count: int = 0
    consecutive_correct: int = 0


class StudentState(BaseModel):
    masteries: dict[str, StudentMastery] = Field(default_factory=dict)
    last_kp_type: KnowledgePointType | None = None

    def get_mastery(self, knowledge_point_id: str) -> StudentMastery:
        if knowledge_point_id not in self.masteries:
            self.masteries[knowledge_point_id] = StudentMastery(
                knowledge_point_id=knowledge_point_id
            )
        return self.masteries[knowledge_point_id]
