"""Data models for the student simulator."""

from datetime import datetime
from pydantic import BaseModel, Field


class SimulatedStudentConfig(BaseModel):
    """Configuration for a simulated student's learning behavior."""

    # Learning rate: how fast true knowledge increases per correct exercise
    # Higher = faster learner (0.1 = slow, 0.3 = average, 0.5 = fast)
    learning_rate: float = Field(default=0.3, ge=0.0, le=1.0)

    # Retention rate: probability of remembering learned material per day
    # Affects forgetting curve (0.9 = good memory, 0.85 = average, 0.7 = poor)
    retention_rate: float = Field(default=0.85, ge=0.0, le=1.0)

    # Base error rate: probability of slip even when "knowing" material
    # (0.05 = careful, 0.1 = average, 0.2 = careless)
    slip_rate: float = Field(default=0.1, ge=0.0, le=0.5)

    # Guess rate: probability of correct guess when not knowing
    guess_rate: float = Field(default=0.25, ge=0.0, le=0.5)


class SimulatedStudent(BaseModel):
    """Represents a simulated student with true knowledge state."""

    config: SimulatedStudentConfig

    # True knowledge per knowledge point (distinct from FSRS's estimate)
    # This is the "ground truth" that FSRS is trying to track
    true_knowledge: dict[str, float] = Field(default_factory=dict)

    # Track when each KP was first encountered (for learning curve analysis)
    first_encounter: dict[str, datetime] = Field(default_factory=dict)

    def get_true_knowledge(self, kp_id: str) -> float:
        """Get true knowledge for a KP (0.0 if never seen)."""
        return self.true_knowledge.get(kp_id, 0.0)

    def update_true_knowledge(
        self, kp_id: str, correct: bool, current_time: datetime
    ) -> None:
        """Update true knowledge after an exercise."""
        # Record first encounter
        if kp_id not in self.first_encounter:
            self.first_encounter[kp_id] = current_time

        current = self.get_true_knowledge(kp_id)

        if correct:
            # Learning: knowledge increases based on learning_rate
            # Formula: k_new = k + learning_rate * (1 - k)
            new_knowledge = current + self.config.learning_rate * (1.0 - current)
        else:
            # Incorrect response slightly decreases confidence
            new_knowledge = current * 0.95

        self.true_knowledge[kp_id] = min(1.0, max(0.0, new_knowledge))

    def apply_forgetting(self, kp_id: str, days_elapsed: float) -> None:
        """Apply forgetting curve based on retention_rate."""
        if kp_id not in self.true_knowledge:
            return

        current = self.true_knowledge[kp_id]
        # Exponential decay: k_new = k * retention_rate^days
        decay_factor = self.config.retention_rate**days_elapsed
        self.true_knowledge[kp_id] = current * decay_factor


class ExerciseResult(BaseModel):
    """Result of a single simulated exercise."""

    timestamp: datetime
    day: int  # Day number in simulation (1-indexed)
    exercise_number: int  # Exercise number within day
    exercise_type: str  # "segmented_translation" or "minimal_pair"
    knowledge_point_ids: list[str]
    is_correct: bool

    # Ground truth vs estimated knowledge
    true_knowledge_before: dict[str, float]  # kp_id -> true knowledge
    retrievability_before: dict[str, float]  # kp_id -> FSRS retrievability
    retrievability_after: dict[str, float]  # kp_id -> FSRS retrievability after update


class DailySummary(BaseModel):
    """Summary of a single simulated day."""

    day: int
    date: datetime
    total_exercises: int
    correct_count: int
    accuracy: float

    # Exercise type breakdown
    segmented_translation_count: int
    segmented_translation_correct: int
    minimal_pair_count: int
    minimal_pair_correct: int

    # Knowledge point stats
    kps_practiced: list[str]  # Unique KPs practiced this day

    # Aggregate knowledge states (snapshot at end of day)
    avg_true_knowledge: float
    avg_retrievability: float


class KnowledgePointSnapshot(BaseModel):
    """Point-in-time snapshot of a KP's state."""

    timestamp: datetime
    day: int
    exercise_number: int | None  # None for daily snapshots

    true_knowledge: float
    retrievability: float
    practice_count: int
    correct_count: int

    # FSRS state
    fsrs_stability: float | None = None
    fsrs_difficulty: float | None = None


class KnowledgePointTrajectory(BaseModel):
    """Complete trajectory of a knowledge point during simulation."""

    kp_id: str
    kp_chinese: str
    kp_english: str

    first_practiced: datetime | None = None

    # Snapshots taken after each exercise involving this KP
    snapshots: list[KnowledgePointSnapshot] = Field(default_factory=list)


class SimulationResults(BaseModel):
    """Complete results of a simulation run."""

    # Configuration
    config: SimulatedStudentConfig
    days_simulated: int
    exercises_per_day: int
    random_seed: int | None
    start_time: datetime
    end_time: datetime

    # Summary statistics
    total_exercises: int
    total_correct: int
    overall_accuracy: float

    # Detailed breakdowns
    daily_summaries: list[DailySummary]
    exercise_results: list[ExerciseResult]
    kp_trajectories: dict[str, KnowledgePointTrajectory]

    # Final state
    final_kps_practiced: int  # KPs that have been practiced at least once
