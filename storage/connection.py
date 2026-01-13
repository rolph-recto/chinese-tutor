"""Database connection management and schema initialization."""

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "tutor.db"

SCHEMA_SQL = """
-- ==========================================================================
-- Legacy tables (kept for migration support)
-- ==========================================================================

-- Knowledge points table (vocabulary and grammar)
CREATE TABLE IF NOT EXISTS knowledge_points (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('vocabulary', 'grammar')),
    chinese TEXT NOT NULL,
    pinyin TEXT NOT NULL,
    english TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_knowledge_points_type ON knowledge_points(type);

-- Minimal pairs for exercises (legacy)
CREATE TABLE IF NOT EXISTS minimal_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id TEXT NOT NULL,
    distractor_chinese TEXT NOT NULL,
    distractor_pinyin TEXT NOT NULL,
    distractor_english TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY (target_id) REFERENCES knowledge_points(id)
);

CREATE INDEX IF NOT EXISTS idx_minimal_pairs_target ON minimal_pairs(target_id);

-- Cloze deletion templates (legacy)
CREATE TABLE IF NOT EXISTS cloze_templates (
    id TEXT PRIMARY KEY,
    chinese TEXT NOT NULL,
    english TEXT NOT NULL,
    target_vocab_id TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (target_vocab_id) REFERENCES knowledge_points(id)
);

CREATE INDEX IF NOT EXISTS idx_cloze_templates_target ON cloze_templates(target_vocab_id);

-- ==========================================================================
-- Dynamic schema tables
-- ==========================================================================

-- User-defined table metadata
CREATE TABLE IF NOT EXISTS user_tables (
    table_id TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    columns TEXT NOT NULL  -- JSON array of column definitions
);

CREATE INDEX IF NOT EXISTS idx_user_tables_name ON user_tables(table_name);

-- User-defined table rows
CREATE TABLE IF NOT EXISTS user_rows (
    table_id TEXT NOT NULL,
    row_id TEXT NOT NULL,
    row_values TEXT NOT NULL,  -- JSON object of column values
    PRIMARY KEY (table_id, row_id),
    FOREIGN KEY (table_id) REFERENCES user_tables(table_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_rows_table ON user_rows(table_id);

-- Student mastery table with composite key (references user_rows)
-- Note: For existing databases with the old schema (knowledge_point_id),
-- run migrate_to_dynamic_schema() to convert to the new schema.
CREATE TABLE IF NOT EXISTS student_mastery (
    table_id TEXT NOT NULL,
    row_id TEXT NOT NULL,
    stability REAL,
    difficulty REAL,
    due TEXT,
    last_review TEXT,
    state INTEGER NOT NULL DEFAULT 1,
    step INTEGER,
    PRIMARY KEY (table_id, row_id)
);

CREATE INDEX IF NOT EXISTS idx_student_mastery_due ON student_mastery(due);
CREATE INDEX IF NOT EXISTS idx_student_mastery_table ON student_mastery(table_id);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a database connection with appropriate settings.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A configured sqlite3 Connection object.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initialize the database schema if it doesn't exist.

    Args:
        db_path: Path to the SQLite database file.
    """
    # Ensure the parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
