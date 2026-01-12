"""Database connection management and schema initialization."""

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "tutor.db"

SCHEMA_SQL = """
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

-- Student mastery table (flattened FSRS state)
CREATE TABLE IF NOT EXISTS student_mastery (
    knowledge_point_id TEXT PRIMARY KEY,
    stability REAL,
    difficulty REAL,
    due TEXT,
    last_review TEXT,
    state INTEGER NOT NULL DEFAULT 1,
    step INTEGER,
    FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
);

CREATE INDEX IF NOT EXISTS idx_student_mastery_due ON student_mastery(due);

-- Minimal pairs for exercises
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

-- Cloze deletion templates
CREATE TABLE IF NOT EXISTS cloze_templates (
    id TEXT PRIMARY KEY,
    chinese TEXT NOT NULL,
    english TEXT NOT NULL,
    target_vocab_id TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (target_vocab_id) REFERENCES knowledge_points(id)
);

CREATE INDEX IF NOT EXISTS idx_cloze_templates_target ON cloze_templates(target_vocab_id);
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
