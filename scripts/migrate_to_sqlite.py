#!/usr/bin/env python3
"""Migrate JSON data to SQLite database.

Usage:
    uv run python scripts/migrate_to_sqlite.py [--force]

Options:
    --force     Overwrite existing database
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.connection import init_schema, get_connection

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "tutor.db"
STATE_FILE = PROJECT_ROOT / "student_state.json"


def migrate_knowledge_points(conn, json_path: Path) -> int:
    """Migrate knowledge points from a JSON file.

    Args:
        conn: SQLite connection.
        json_path: Path to JSON file (vocabulary.json or grammar.json).

    Returns:
        Number of records migrated.
    """
    if not json_path.exists():
        print(f"  Skipping {json_path.name} (not found)")
        return 0

    with open(json_path) as f:
        items = json.load(f)

    for item in items:
        conn.execute(
            """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                item["id"],
                item["type"],
                item["chinese"],
                item["pinyin"],
                item["english"],
                json.dumps(item.get("tags", [])),
            ),
        )

    print(f"  Migrated {len(items)} records from {json_path.name}")
    return len(items)


def migrate_minimal_pairs(conn, json_path: Path) -> int:
    """Migrate minimal pairs from JSON file.

    Args:
        conn: SQLite connection.
        json_path: Path to minimal_pairs.json.

    Returns:
        Number of distractor records migrated.
    """
    if not json_path.exists():
        print(f"  Skipping {json_path.name} (not found)")
        return 0

    with open(json_path) as f:
        pairs = json.load(f)

    count = 0
    for pair in pairs:
        target_id = pair["target_id"]
        for distractor in pair["distractors"]:
            conn.execute(
                """INSERT INTO minimal_pairs
                (target_id, distractor_chinese, distractor_pinyin, distractor_english, reason)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    target_id,
                    distractor["chinese"],
                    distractor["pinyin"],
                    distractor["english"],
                    distractor.get("reason"),
                ),
            )
            count += 1

    print(f"  Migrated {count} distractors from {json_path.name}")
    return count


def migrate_cloze_templates(conn, json_path: Path) -> int:
    """Migrate cloze templates from JSON file.

    Args:
        conn: SQLite connection.
        json_path: Path to cloze_templates.json.

    Returns:
        Number of records migrated.
    """
    if not json_path.exists():
        print(f"  Skipping {json_path.name} (not found)")
        return 0

    with open(json_path) as f:
        templates = json.load(f)

    for template in templates:
        conn.execute(
            """INSERT INTO cloze_templates (id, chinese, english, target_vocab_id, tags)
            VALUES (?, ?, ?, ?, ?)""",
            (
                template["id"],
                template["chinese"],
                template["english"],
                template["target_vocab_id"],
                json.dumps(template.get("tags", [])),
            ),
        )

    print(f"  Migrated {len(templates)} records from {json_path.name}")
    return len(templates)


def migrate_student_state(conn, state_path: Path) -> int:
    """Migrate student state from JSON file.

    Args:
        conn: SQLite connection.
        state_path: Path to student_state.json.

    Returns:
        Number of mastery records migrated.
    """
    if not state_path.exists():
        print(f"  Skipping {state_path.name} (not found)")
        return 0

    with open(state_path) as f:
        state_data = json.load(f)

    masteries = state_data.get("masteries", {})
    for kp_id, mastery in masteries.items():
        fsrs = mastery.get("fsrs_state") or {}
        conn.execute(
            """INSERT INTO student_mastery
            (knowledge_point_id, stability, difficulty, due, last_review, state, step)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                kp_id,
                fsrs.get("stability"),
                fsrs.get("difficulty"),
                fsrs.get("due"),
                fsrs.get("last_review"),
                fsrs.get("state", 1),
                fsrs.get("step"),
            ),
        )

    print(f"  Migrated {len(masteries)} mastery records from {state_path.name}")
    return len(masteries)


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to SQLite database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database",
    )
    args = parser.parse_args()

    # Check if database exists
    if DB_PATH.exists():
        if not args.force:
            print(f"Database already exists at {DB_PATH}")
            print("Use --force to overwrite")
            sys.exit(1)
        else:
            print(f"Removing existing database: {DB_PATH}")
            DB_PATH.unlink()

    print(f"Creating database at {DB_PATH}")
    print()

    # Initialize schema
    init_schema(DB_PATH)
    print("Schema initialized")
    print()

    # Get connection for migrations
    conn = get_connection(DB_PATH)

    try:
        print("Migrating knowledge points...")
        migrate_knowledge_points(conn, DATA_DIR / "vocabulary.json")
        migrate_knowledge_points(conn, DATA_DIR / "grammar.json")
        print()

        print("Migrating exercise data...")
        migrate_minimal_pairs(conn, DATA_DIR / "minimal_pairs.json")
        migrate_cloze_templates(conn, DATA_DIR / "cloze_templates.json")
        print()

        print("Migrating student state...")
        migrate_student_state(conn, STATE_FILE)
        print()

        conn.commit()
        print(f"Migration complete: {DB_PATH}")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
