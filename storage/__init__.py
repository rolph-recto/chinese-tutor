"""Storage layer for Chinese Tutor application.

Provides repository interfaces and SQLite implementations for persisting
knowledge points and student state. Supports both legacy fixed schema and
new dynamic schema systems.
"""

from pathlib import Path

from .base import (
    KnowledgePointRepository,
    StudentStateRepository,
    MinimalPairsRepository,
    ClozeTemplatesRepository,
    UserTableRepository,
    UserRowRepository,
)
from .sqlite import (
    SQLiteKnowledgePointRepository,
    SQLiteStudentStateRepository,
    SQLiteMinimalPairsRepository,
    SQLiteClozeTemplatesRepository,
    SQLiteUserTableRepository,
    SQLiteUserRowRepository,
)
from .adapters import (
    KnowledgePointAdapter,
    MinimalPairsAdapter,
    ClozeTemplatesAdapter,
)
from .connection import get_connection, init_schema, DEFAULT_DB_PATH

__all__ = [
    # Abstract interfaces
    "KnowledgePointRepository",
    "StudentStateRepository",
    "MinimalPairsRepository",
    "ClozeTemplatesRepository",
    "UserTableRepository",
    "UserRowRepository",
    # SQLite implementations
    "SQLiteKnowledgePointRepository",
    "SQLiteStudentStateRepository",
    "SQLiteMinimalPairsRepository",
    "SQLiteClozeTemplatesRepository",
    "SQLiteUserTableRepository",
    "SQLiteUserRowRepository",
    # Adapters for backwards compatibility
    "KnowledgePointAdapter",
    "MinimalPairsAdapter",
    "ClozeTemplatesAdapter",
    # Connection utilities
    "get_connection",
    "init_schema",
    "DEFAULT_DB_PATH",
    # Factory functions (legacy)
    "get_knowledge_point_repo",
    "get_student_state_repo",
    "get_minimal_pairs_repo",
    "get_cloze_templates_repo",
    # Factory functions (dynamic schema)
    "get_user_table_repo",
    "get_user_row_repo",
    # Factory functions (adapters)
    "get_knowledge_point_adapter",
    "get_minimal_pairs_adapter",
    "get_cloze_templates_adapter",
]


# ============================================================================
# Legacy Factory Functions (use SQLite implementations directly)
# ============================================================================


def get_knowledge_point_repo(
    db_path: Path = DEFAULT_DB_PATH,
) -> KnowledgePointRepository:
    """Get a KnowledgePointRepository instance (legacy, reads from fixed schema)."""
    return SQLiteKnowledgePointRepository(db_path)


def get_student_state_repo(db_path: Path = DEFAULT_DB_PATH) -> StudentStateRepository:
    """Get a StudentStateRepository instance."""
    return SQLiteStudentStateRepository(db_path)


def get_minimal_pairs_repo(db_path: Path = DEFAULT_DB_PATH) -> MinimalPairsRepository:
    """Get a MinimalPairsRepository instance (legacy, reads from fixed schema)."""
    return SQLiteMinimalPairsRepository(db_path)


def get_cloze_templates_repo(
    db_path: Path = DEFAULT_DB_PATH,
) -> ClozeTemplatesRepository:
    """Get a ClozeTemplatesRepository instance (legacy, reads from fixed schema)."""
    return SQLiteClozeTemplatesRepository(db_path)


# ============================================================================
# Dynamic Schema Factory Functions
# ============================================================================


def get_user_table_repo(db_path: Path = DEFAULT_DB_PATH) -> UserTableRepository:
    """Get a UserTableRepository instance for managing dynamic table metadata."""
    return SQLiteUserTableRepository(db_path)


def get_user_row_repo(db_path: Path = DEFAULT_DB_PATH) -> UserRowRepository:
    """Get a UserRowRepository instance for managing dynamic table rows."""
    return SQLiteUserRowRepository(db_path)


# ============================================================================
# Adapter Factory Functions (for migrated databases)
# ============================================================================


def get_knowledge_point_adapter(
    db_path: Path = DEFAULT_DB_PATH,
) -> KnowledgePointAdapter:
    """Get a KnowledgePointAdapter that reads from dynamic schema.

    Use this after migration to read knowledge points from user_rows table
    while maintaining the KnowledgePoint interface.
    """
    row_repo = SQLiteUserRowRepository(db_path)
    return KnowledgePointAdapter(row_repo)


def get_minimal_pairs_adapter(db_path: Path = DEFAULT_DB_PATH) -> MinimalPairsAdapter:
    """Get a MinimalPairsAdapter that reads from dynamic schema.

    Use this after migration to read minimal pairs from user_rows table.
    """
    row_repo = SQLiteUserRowRepository(db_path)
    return MinimalPairsAdapter(row_repo)


def get_cloze_templates_adapter(
    db_path: Path = DEFAULT_DB_PATH,
) -> ClozeTemplatesAdapter:
    """Get a ClozeTemplatesAdapter that reads from dynamic schema.

    Use this after migration to read cloze templates from user_rows table.
    """
    row_repo = SQLiteUserRowRepository(db_path)
    return ClozeTemplatesAdapter(row_repo)
