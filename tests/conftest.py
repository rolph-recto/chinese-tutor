"""Shared pytest fixtures for the Chinese Tutor test suite."""

import pytest
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    KnowledgePoint,
    KnowledgePointType,
    StudentMastery,
    StudentState,
    SchedulingMode,
    FSRSState,
)
from simulator_models import SimulatedStudentConfig


@pytest.fixture
def sample_vocabulary_kp() -> KnowledgePoint:
    """Create a sample vocabulary knowledge point."""
    return KnowledgePoint(
        id="v001",
        type=KnowledgePointType.VOCABULARY,
        chinese="我",
        pinyin="wǒ",
        english="I, me",
        hsk_level=1,
        prerequisites=[],
    )


@pytest.fixture
def sample_grammar_kp() -> KnowledgePoint:
    """Create a sample grammar knowledge point with prerequisites."""
    return KnowledgePoint(
        id="g001",
        type=KnowledgePointType.GRAMMAR,
        chinese="Subject + 是 + Noun",
        pinyin="Subject + shì + Noun",
        english="Subject is Noun (using 是)",
        hsk_level=1,
        prerequisites=["v005"],
    )


@pytest.fixture
def sample_knowledge_points() -> list[KnowledgePoint]:
    """Create a minimal set of knowledge points for testing."""
    return [
        KnowledgePoint(
            id="v001",
            type=KnowledgePointType.VOCABULARY,
            chinese="我",
            pinyin="wǒ",
            english="I, me",
            hsk_level=1,
            prerequisites=[],
        ),
        KnowledgePoint(
            id="v002",
            type=KnowledgePointType.VOCABULARY,
            chinese="你",
            pinyin="nǐ",
            english="you",
            hsk_level=1,
            prerequisites=[],
        ),
        KnowledgePoint(
            id="v005",
            type=KnowledgePointType.VOCABULARY,
            chinese="是",
            pinyin="shì",
            english="to be",
            hsk_level=1,
            prerequisites=[],
        ),
        KnowledgePoint(
            id="g001",
            type=KnowledgePointType.GRAMMAR,
            chinese="Subject + 是 + Noun",
            pinyin="Subject + shì + Noun",
            english="Subject is Noun",
            hsk_level=1,
            prerequisites=["v005"],
        ),
    ]


@pytest.fixture
def fresh_mastery() -> StudentMastery:
    """Create a fresh (unlearned) mastery record."""
    return StudentMastery(
        knowledge_point_id="v001",
        p_known=0.0,
        p_transit=0.3,
        p_slip=0.1,
        p_guess=0.2,
    )


@pytest.fixture
def partial_mastery() -> StudentMastery:
    """Create a partially learned mastery record (p_known=0.5)."""
    return StudentMastery(
        knowledge_point_id="v001",
        p_known=0.5,
        p_transit=0.3,
        p_slip=0.1,
        p_guess=0.2,
        last_practiced=datetime.now() - timedelta(days=1),
        practice_count=5,
        correct_count=3,
    )


@pytest.fixture
def near_mastery() -> StudentMastery:
    """Create a near-mastered record (p_known=0.75, just below threshold)."""
    return StudentMastery(
        knowledge_point_id="v001",
        p_known=0.75,
        p_transit=0.3,
        p_slip=0.1,
        p_guess=0.2,
        last_practiced=datetime.now(),
        practice_count=10,
        correct_count=8,
    )


@pytest.fixture
def mastered_bkt() -> StudentMastery:
    """Create a mastered BKT record (p_known=0.85, above threshold)."""
    return StudentMastery(
        knowledge_point_id="v001",
        p_known=0.85,
        p_transit=0.3,
        p_slip=0.1,
        p_guess=0.2,
        scheduling_mode=SchedulingMode.BKT,
        last_practiced=datetime.now(),
        practice_count=15,
        correct_count=13,
    )


@pytest.fixture
def fsrs_mastery() -> StudentMastery:
    """Create a mastery record in FSRS mode."""
    return StudentMastery(
        knowledge_point_id="v001",
        p_known=0.9,
        scheduling_mode=SchedulingMode.FSRS,
        fsrs_state=FSRSState(
            stability=10.0,
            difficulty=5.0,
            due=datetime.now() + timedelta(days=1),
            last_review=datetime.now(),
            state=2,  # Review state
            step=None,
        ),
        transitioned_to_fsrs_at=datetime.now() - timedelta(days=7),
        last_practiced=datetime.now(),
        practice_count=20,
        correct_count=18,
    )


@pytest.fixture
def empty_student_state() -> StudentState:
    """Create an empty student state."""
    return StudentState()


@pytest.fixture
def populated_student_state() -> StudentState:
    """Create a student state with some mastery records."""
    state = StudentState()
    state.masteries["v001"] = StudentMastery(
        knowledge_point_id="v001", p_known=0.3
    )
    state.masteries["v002"] = StudentMastery(
        knowledge_point_id="v002", p_known=0.7
    )
    state.masteries["v005"] = StudentMastery(
        knowledge_point_id="v005", p_known=0.85  # Mastered
    )
    return state


@pytest.fixture
def default_simulator_config() -> SimulatedStudentConfig:
    """Create a default simulator configuration."""
    return SimulatedStudentConfig(
        learning_rate=0.3,
        retention_rate=0.85,
        slip_rate=0.1,
        guess_rate=0.25,
    )


@pytest.fixture
def fast_learner_config() -> SimulatedStudentConfig:
    """Create a fast learner simulator configuration."""
    return SimulatedStudentConfig(
        learning_rate=0.5,
        retention_rate=0.95,
        slip_rate=0.05,
        guess_rate=0.2,
    )


@pytest.fixture
def slow_learner_config() -> SimulatedStudentConfig:
    """Create a slow learner simulator configuration."""
    return SimulatedStudentConfig(
        learning_rate=0.15,
        retention_rate=0.7,
        slip_rate=0.15,
        guess_rate=0.3,
    )
