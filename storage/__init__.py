"""Storage layer for Chinese Tutor application.

Provides repository interfaces and SQLite implementations for persisting
knowledge points and student state.
"""

from pathlib import Path

from .base import (
    KnowledgePointRepository,
    StudentStateRepository,
    MinimalPairsRepository,
    ClozeTemplatesRepository,
)
from .sqlite import (
    SQLiteKnowledgePointRepository,
    SQLiteStudentStateRepository,
    SQLiteMinimalPairsRepository,
    SQLiteClozeTemplatesRepository,
)
from .connection import get_connection, init_schema, DEFAULT_DB_PATH

__all__ = [
    # Abstract interfaces
    "KnowledgePointRepository",
    "StudentStateRepository",
    "MinimalPairsRepository",
    "ClozeTemplatesRepository",
    # SQLite implementations
    "SQLiteKnowledgePointRepository",
    "SQLiteStudentStateRepository",
    "SQLiteMinimalPairsRepository",
    "SQLiteClozeTemplatesRepository",
    # Connection utilities
    "get_connection",
    "init_schema",
    "DEFAULT_DB_PATH",
    # Factory functions
    "get_knowledge_point_repo",
    "get_student_state_repo",
    "get_minimal_pairs_repo",
    "get_cloze_templates_repo",
]


def get_knowledge_point_repo(
    db_path: Path = DEFAULT_DB_PATH,
) -> KnowledgePointRepository:
    """Get a KnowledgePointRepository instance."""
    return SQLiteKnowledgePointRepository(db_path)


def get_student_state_repo(db_path: Path = DEFAULT_DB_PATH) -> StudentStateRepository:
    """Get a StudentStateRepository instance."""
    return SQLiteStudentStateRepository(db_path)


def get_minimal_pairs_repo(db_path: Path = DEFAULT_DB_PATH) -> MinimalPairsRepository:
    """Get a MinimalPairsRepository instance."""
    return SQLiteMinimalPairsRepository(db_path)


def get_cloze_templates_repo(
    db_path: Path = DEFAULT_DB_PATH,
) -> ClozeTemplatesRepository:
    """Get a ClozeTemplatesRepository instance."""
    return SQLiteClozeTemplatesRepository(db_path)
