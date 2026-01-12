"""Shared pytest fixtures for the Chinese Tutor test suite."""

import json
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
    FSRSState,
)
from simulator_models import SimulatedStudentConfig
from storage import init_schema, get_connection


@pytest.fixture
def sample_vocabulary_kp() -> KnowledgePoint:
    """Create a sample vocabulary knowledge point."""
    return KnowledgePoint(
        id="v001",
        type=KnowledgePointType.VOCABULARY,
        chinese="我",
        pinyin="wǒ",
        english="I, me",
        tags=["hsk1", "cluster:pronouns"],
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
        tags=["hsk1", "cluster:sentence-patterns"],
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
            tags=["hsk1", "cluster:pronouns"],
        ),
        KnowledgePoint(
            id="v002",
            type=KnowledgePointType.VOCABULARY,
            chinese="你",
            pinyin="nǐ",
            english="you",
            tags=["hsk1", "cluster:pronouns"],
        ),
        KnowledgePoint(
            id="v005",
            type=KnowledgePointType.VOCABULARY,
            chinese="是",
            pinyin="shì",
            english="to be",
            tags=["hsk1", "cluster:basic-verbs"],
        ),
        KnowledgePoint(
            id="g001",
            type=KnowledgePointType.GRAMMAR,
            chinese="Subject + 是 + Noun",
            pinyin="Subject + shì + Noun",
            english="Subject is Noun",
            tags=["hsk1", "cluster:sentence-patterns"],
        ),
    ]


@pytest.fixture
def fsrs_mastery() -> StudentMastery:
    """Create a mastery record with FSRS state initialized."""
    return StudentMastery(
        knowledge_point_id="v001",
        fsrs_state=FSRSState(
            stability=10.0,
            difficulty=5.0,
            due=datetime.now() + timedelta(days=1),
            last_review=datetime.now(),
            state=2,  # Review state
            step=None,
        ),
    )


@pytest.fixture
def new_mastery() -> StudentMastery:
    """Create a new mastery record without FSRS state (not yet practiced)."""
    return StudentMastery(
        knowledge_point_id="v001",
    )


@pytest.fixture
def practiced_mastery() -> StudentMastery:
    """Create a mastery record that has been practiced multiple times."""
    return StudentMastery(
        knowledge_point_id="v001",
        fsrs_state=FSRSState(
            stability=5.0,
            difficulty=5.0,
            due=datetime.now() - timedelta(hours=2),  # Slightly overdue
            last_review=datetime.now() - timedelta(days=1),
            state=2,  # Review state
            step=None,
        ),
    )


@pytest.fixture
def empty_student_state() -> StudentState:
    """Create an empty student state."""
    return StudentState()


@pytest.fixture
def populated_student_state() -> StudentState:
    """Create a student state with some mastery records (all with FSRS state)."""
    state = StudentState()

    state.masteries["v001"] = StudentMastery(
        knowledge_point_id="v001",
        fsrs_state=FSRSState(
            stability=3.0,
            difficulty=5.0,
            due=datetime.now() - timedelta(hours=12),
            last_review=datetime.now(),
            state=2,
            step=None,
        ),
    )

    state.masteries["v002"] = StudentMastery(
        knowledge_point_id="v002",
        fsrs_state=FSRSState(
            stability=8.0,
            difficulty=4.5,
            due=datetime.now() - timedelta(days=2),
            last_review=datetime.now(),
            state=2,
            step=None,
        ),
    )

    state.masteries["v005"] = StudentMastery(
        knowledge_point_id="v005",
        fsrs_state=FSRSState(
            stability=15.0,
            difficulty=4.0,
            due=datetime.now() - timedelta(days=5),
            last_review=datetime.now(),
            state=2,
            step=None,
        ),
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


@pytest.fixture
def test_db_path(tmp_path) -> Path:
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_tutor.db"
    init_schema(db_path)
    return db_path


@pytest.fixture
def populated_test_db(test_db_path, sample_knowledge_points) -> Path:
    """Create a test database populated with sample data.

    Includes sample knowledge points, minimal pairs, and cloze templates.
    """
    conn = get_connection(test_db_path)
    try:
        # Insert knowledge points
        for kp in sample_knowledge_points:
            conn.execute(
                """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    kp.id,
                    kp.type.value,
                    kp.chinese,
                    kp.pinyin,
                    kp.english,
                    json.dumps(kp.tags),
                ),
            )

        # Insert minimal pairs for v001 (我)
        conn.execute(
            """INSERT INTO minimal_pairs
            (target_id, distractor_chinese, distractor_pinyin, distractor_english, reason)
            VALUES (?, ?, ?, ?, ?)""",
            ("v001", "找", "zhǎo", "to find", "Similar visual shape"),
        )

        # Insert cloze template
        conn.execute(
            """INSERT INTO cloze_templates (id, chinese, english, target_vocab_id, tags)
            VALUES (?, ?, ?, ?, ?)""",
            (
                "cloze001",
                "_____ 是学生。",
                "_____ am a student.",
                "v001",
                json.dumps(["hsk1"]),
            ),
        )

        conn.commit()
    finally:
        conn.close()

    return test_db_path
