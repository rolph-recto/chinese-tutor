"""Database migration utilities for dynamic schema conversion."""

import json
import sqlite3
from pathlib import Path

from .connection import get_connection, DEFAULT_DB_PATH, init_schema


def migrate_to_dynamic_schema(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Migrate existing fixed tables to dynamic schema format.

    This migration:
    1. Migrates student_mastery to use composite keys (if needed)
    2. Creates new dynamic schema tables if they don't exist
    3. Migrates knowledge_points to user_tables/user_rows
    4. Migrates minimal_pairs to user_tables/user_rows
    5. Migrates cloze_templates to user_tables/user_rows

    The migration is idempotent - running it multiple times is safe.

    Args:
        db_path: Path to the SQLite database file.
    """
    # First, ensure student_mastery table has new schema BEFORE init_schema
    # This is needed because init_schema creates indexes on new columns
    conn = get_connection(db_path)
    try:
        _ensure_student_mastery_table(conn)
        conn.commit()
    finally:
        conn.close()

    # Now it's safe to run init_schema (creates user_tables, user_rows, etc.)
    init_schema(db_path)

    conn = get_connection(db_path)
    try:
        # Check if migration is needed
        if _is_migrated(conn):
            return

        # Migrate in order (knowledge_points first since others reference it)
        _migrate_knowledge_points(conn)
        _migrate_minimal_pairs(conn)
        _migrate_cloze_templates(conn)

        conn.commit()
    finally:
        conn.close()


def _is_migrated(conn: sqlite3.Connection) -> bool:
    """Check if migration has already been performed.

    Returns True if knowledge_points table has been migrated to user_tables.
    """
    cursor = conn.execute(
        "SELECT 1 FROM user_tables WHERE table_id = 'knowledge_points'"
    )
    return cursor.fetchone() is not None


def _migrate_knowledge_points(conn: sqlite3.Connection) -> None:
    """Migrate knowledge_points table to user_tables/user_rows."""
    # Check if source table has data
    cursor = conn.execute("SELECT COUNT(*) FROM knowledge_points")
    count = cursor.fetchone()[0]
    if count == 0:
        return

    # Create table definition
    columns = [
        {"name": "id", "type": "TEXT", "required": True, "default": None},
        {"name": "type", "type": "TEXT", "required": True, "default": None},
        {"name": "chinese", "type": "TEXT", "required": True, "default": None},
        {"name": "pinyin", "type": "TEXT", "required": True, "default": None},
        {"name": "english", "type": "TEXT", "required": True, "default": None},
        {"name": "tags", "type": "JSON", "required": False, "default": []},
    ]

    conn.execute(
        """INSERT OR IGNORE INTO user_tables (table_id, table_name, columns)
        VALUES (?, ?, ?)""",
        ("knowledge_points", "Knowledge Points", json.dumps(columns)),
    )

    # Migrate rows
    cursor = conn.execute("SELECT * FROM knowledge_points")
    for row in cursor.fetchall():
        row_values = {
            "id": row["id"],
            "type": row["type"],
            "chinese": row["chinese"],
            "pinyin": row["pinyin"],
            "english": row["english"],
            "tags": json.loads(row["tags"]),
        }
        conn.execute(
            """INSERT OR IGNORE INTO user_rows (table_id, row_id, row_values)
            VALUES (?, ?, ?)""",
            ("knowledge_points", row["id"], json.dumps(row_values)),
        )


def _migrate_minimal_pairs(conn: sqlite3.Connection) -> None:
    """Migrate minimal_pairs table to user_tables/user_rows."""
    # Check if source table has data
    cursor = conn.execute("SELECT COUNT(*) FROM minimal_pairs")
    count = cursor.fetchone()[0]
    if count == 0:
        return

    # Create table definition
    columns = [
        {"name": "id", "type": "INTEGER", "required": True, "default": None},
        {"name": "target_id", "type": "TEXT", "required": True, "default": None},
        {
            "name": "distractor_chinese",
            "type": "TEXT",
            "required": True,
            "default": None,
        },
        {
            "name": "distractor_pinyin",
            "type": "TEXT",
            "required": True,
            "default": None,
        },
        {
            "name": "distractor_english",
            "type": "TEXT",
            "required": True,
            "default": None,
        },
        {"name": "reason", "type": "TEXT", "required": False, "default": None},
    ]

    conn.execute(
        """INSERT OR IGNORE INTO user_tables (table_id, table_name, columns)
        VALUES (?, ?, ?)""",
        ("minimal_pairs", "Minimal Pairs", json.dumps(columns)),
    )

    # Migrate rows
    cursor = conn.execute("SELECT * FROM minimal_pairs")
    for row in cursor.fetchall():
        row_id = str(row["id"])
        row_values = {
            "id": row["id"],
            "target_id": row["target_id"],
            "distractor_chinese": row["distractor_chinese"],
            "distractor_pinyin": row["distractor_pinyin"],
            "distractor_english": row["distractor_english"],
            "reason": row["reason"],
        }
        conn.execute(
            """INSERT OR IGNORE INTO user_rows (table_id, row_id, row_values)
            VALUES (?, ?, ?)""",
            ("minimal_pairs", row_id, json.dumps(row_values)),
        )


def _migrate_cloze_templates(conn: sqlite3.Connection) -> None:
    """Migrate cloze_templates table to user_tables/user_rows."""
    # Check if source table has data
    cursor = conn.execute("SELECT COUNT(*) FROM cloze_templates")
    count = cursor.fetchone()[0]
    if count == 0:
        return

    # Create table definition
    columns = [
        {"name": "id", "type": "TEXT", "required": True, "default": None},
        {"name": "chinese", "type": "TEXT", "required": True, "default": None},
        {"name": "english", "type": "TEXT", "required": True, "default": None},
        {"name": "target_vocab_id", "type": "TEXT", "required": True, "default": None},
        {"name": "tags", "type": "JSON", "required": False, "default": []},
    ]

    conn.execute(
        """INSERT OR IGNORE INTO user_tables (table_id, table_name, columns)
        VALUES (?, ?, ?)""",
        ("cloze_templates", "Cloze Templates", json.dumps(columns)),
    )

    # Migrate rows
    cursor = conn.execute("SELECT * FROM cloze_templates")
    for row in cursor.fetchall():
        row_values = {
            "id": row["id"],
            "chinese": row["chinese"],
            "english": row["english"],
            "target_vocab_id": row["target_vocab_id"],
            "tags": json.loads(row["tags"]),
        }
        conn.execute(
            """INSERT OR IGNORE INTO user_rows (table_id, row_id, row_values)
            VALUES (?, ?, ?)""",
            ("cloze_templates", row["id"], json.dumps(row_values)),
        )


def _ensure_student_mastery_table(conn: sqlite3.Connection) -> None:
    """Ensure student_mastery table exists with the new schema.

    This handles three cases:
    1. Table doesn't exist - create it with new schema
    2. Table exists with old schema (knowledge_point_id) - migrate it
    3. Table exists with new schema (table_id, row_id) - do nothing
    """
    # Check if table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='student_mastery'"
    )
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # Case 1: Create new table with new schema
        conn.execute(
            """
            CREATE TABLE student_mastery (
                table_id TEXT NOT NULL,
                row_id TEXT NOT NULL,
                stability REAL,
                difficulty REAL,
                due TEXT,
                last_review TEXT,
                state INTEGER NOT NULL DEFAULT 1,
                step INTEGER,
                PRIMARY KEY (table_id, row_id)
            )
        """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_student_mastery_due ON student_mastery(due)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_student_mastery_table ON student_mastery(table_id)"
        )
        return

    # Check current schema
    cursor = conn.execute("PRAGMA table_info(student_mastery)")
    columns = {row[1] for row in cursor.fetchall()}

    if "table_id" in columns and "row_id" in columns:
        # Case 3: Already using new schema
        return

    if "knowledge_point_id" in columns:
        # Case 2: Migrate from old schema
        _migrate_student_mastery_data(conn)


def _migrate_student_mastery_data(conn: sqlite3.Connection) -> None:
    """Migrate student_mastery data from old schema to new schema."""
    # Create temporary table with new schema
    conn.execute(
        """
        CREATE TABLE student_mastery_new (
            table_id TEXT NOT NULL,
            row_id TEXT NOT NULL,
            stability REAL,
            difficulty REAL,
            due TEXT,
            last_review TEXT,
            state INTEGER NOT NULL DEFAULT 1,
            step INTEGER,
            PRIMARY KEY (table_id, row_id)
        )
    """
    )

    # Migrate data - old knowledge_point_id becomes row_id with table_id='knowledge_points'
    conn.execute(
        """
        INSERT INTO student_mastery_new
        (table_id, row_id, stability, difficulty, due, last_review, state, step)
        SELECT 'knowledge_points', knowledge_point_id, stability, difficulty,
               due, last_review, state, step
        FROM student_mastery
    """
    )

    # Swap tables
    conn.execute("DROP TABLE student_mastery")
    conn.execute("ALTER TABLE student_mastery_new RENAME TO student_mastery")

    # Recreate indexes
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_student_mastery_due ON student_mastery(due)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_student_mastery_table ON student_mastery(table_id)"
    )


def check_migration_status(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Check the current migration status of the database.

    Returns:
        Dictionary with migration status information.
    """
    conn = get_connection(db_path)
    try:
        result = {
            "is_migrated": _is_migrated(conn),
            "tables_migrated": [],
            "legacy_data_exists": False,
        }

        # Check which tables have been migrated
        cursor = conn.execute("SELECT table_id FROM user_tables")
        result["tables_migrated"] = [row[0] for row in cursor.fetchall()]

        # Check if legacy data exists
        for table in ["knowledge_points", "minimal_pairs", "cloze_templates"]:
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                if cursor.fetchone()[0] > 0:
                    result["legacy_data_exists"] = True
                    break
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

        return result
    finally:
        conn.close()
