"""SQLite implementations of repository interfaces."""

import json
from datetime import datetime
from pathlib import Path

from .base import (
    KnowledgePointRepository,
    StudentStateRepository,
    MinimalPairsRepository,
    ClozeTemplatesRepository,
)
from .connection import get_connection, DEFAULT_DB_PATH
from models import (
    KnowledgePoint,
    KnowledgePointType,
    StudentState,
    StudentMastery,
    FSRSState,
)


class SQLiteKnowledgePointRepository(KnowledgePointRepository):
    """SQLite implementation of KnowledgePointRepository."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_all(self) -> list[KnowledgePoint]:
        """Load all knowledge points."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM knowledge_points")
            return [self._row_to_model(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_by_id(self, kp_id: str) -> KnowledgePoint | None:
        """Load a single knowledge point by ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM knowledge_points WHERE id = ?", (kp_id,)
            )
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def get_by_type(self, kp_type: str) -> list[KnowledgePoint]:
        """Load knowledge points by type."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM knowledge_points WHERE type = ?", (kp_type,)
            )
            return [self._row_to_model(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _row_to_model(self, row) -> KnowledgePoint:
        """Convert a database row to a KnowledgePoint model."""
        return KnowledgePoint(
            id=row["id"],
            type=KnowledgePointType(row["type"]),
            chinese=row["chinese"],
            pinyin=row["pinyin"],
            english=row["english"],
            tags=json.loads(row["tags"]),
        )


class SQLiteStudentStateRepository(StudentStateRepository):
    """SQLite implementation of StudentStateRepository."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    def load(self) -> StudentState:
        """Load the complete student state."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM student_mastery")
            masteries = {}
            for row in cursor.fetchall():
                mastery = self._row_to_mastery(row)
                masteries[mastery.knowledge_point_id] = mastery
            return StudentState(masteries=masteries)
        finally:
            conn.close()

    def save(self, state: StudentState) -> None:
        """Save the complete student state."""
        conn = get_connection(self.db_path)
        try:
            # Clear existing masteries and insert all
            conn.execute("DELETE FROM student_mastery")
            for mastery in state.masteries.values():
                self._insert_mastery(conn, mastery)
            conn.commit()
        finally:
            conn.close()

    def get_mastery(self, kp_id: str) -> StudentMastery | None:
        """Get mastery for a single knowledge point."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM student_mastery WHERE knowledge_point_id = ?", (kp_id,)
            )
            row = cursor.fetchone()
            return self._row_to_mastery(row) if row else None
        finally:
            conn.close()

    def save_mastery(self, mastery: StudentMastery) -> None:
        """Save/update mastery for a single knowledge point."""
        conn = get_connection(self.db_path)
        try:
            # Use INSERT OR REPLACE for upsert behavior
            self._insert_mastery(conn, mastery, replace=True)
            conn.commit()
        finally:
            conn.close()

    def _row_to_mastery(self, row) -> StudentMastery:
        """Convert a database row to a StudentMastery model."""
        fsrs_state = None
        # Only create FSRSState if we have any FSRS data
        if row["stability"] is not None or row["due"] is not None:
            fsrs_state = FSRSState(
                stability=row["stability"],
                difficulty=row["difficulty"],
                due=datetime.fromisoformat(row["due"]) if row["due"] else None,
                last_review=datetime.fromisoformat(row["last_review"])
                if row["last_review"]
                else None,
                state=row["state"],
                step=row["step"],
            )
        return StudentMastery(
            knowledge_point_id=row["knowledge_point_id"],
            fsrs_state=fsrs_state,
        )

    def _insert_mastery(
        self, conn, mastery: StudentMastery, replace: bool = False
    ) -> None:
        """Insert a mastery record into the database."""
        fsrs = mastery.fsrs_state
        sql = "INSERT OR REPLACE" if replace else "INSERT"
        conn.execute(
            f"""{sql} INTO student_mastery
            (knowledge_point_id, stability, difficulty, due, last_review, state, step)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                mastery.knowledge_point_id,
                fsrs.stability if fsrs else None,
                fsrs.difficulty if fsrs else None,
                fsrs.due.isoformat() if fsrs and fsrs.due else None,
                fsrs.last_review.isoformat() if fsrs and fsrs.last_review else None,
                fsrs.state if fsrs else 1,
                fsrs.step if fsrs else None,
            ),
        )


class SQLiteMinimalPairsRepository(MinimalPairsRepository):
    """SQLite implementation of MinimalPairsRepository."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_distractors(self, target_id: str) -> list[dict] | None:
        """Get distractors for a target knowledge point."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                """SELECT distractor_chinese, distractor_pinyin, distractor_english, reason
                FROM minimal_pairs WHERE target_id = ?""",
                (target_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            return [
                {
                    "chinese": row["distractor_chinese"],
                    "pinyin": row["distractor_pinyin"],
                    "english": row["distractor_english"],
                    "reason": row["reason"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_all_target_ids(self) -> set[str]:
        """Get all target IDs that have minimal pairs defined."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT DISTINCT target_id FROM minimal_pairs")
            return {row["target_id"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_all_as_dict(self) -> dict[str, list[dict]]:
        """Get all minimal pairs as a dictionary."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                """SELECT target_id, distractor_chinese, distractor_pinyin,
                distractor_english, reason FROM minimal_pairs"""
            )
            result: dict[str, list[dict]] = {}
            for row in cursor.fetchall():
                target_id = row["target_id"]
                if target_id not in result:
                    result[target_id] = []
                result[target_id].append(
                    {
                        "chinese": row["distractor_chinese"],
                        "pinyin": row["distractor_pinyin"],
                        "english": row["distractor_english"],
                        "reason": row["reason"],
                    }
                )
            return result
        finally:
            conn.close()


class SQLiteClozeTemplatesRepository(ClozeTemplatesRepository):
    """SQLite implementation of ClozeTemplatesRepository."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_all(self) -> list[dict]:
        """Get all cloze templates."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM cloze_templates")
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_by_vocab_id(self, vocab_id: str) -> list[dict]:
        """Get templates for a specific vocabulary item."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM cloze_templates WHERE target_vocab_id = ?", (vocab_id,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _row_to_dict(self, row) -> dict:
        """Convert a database row to a template dictionary."""
        return {
            "id": row["id"],
            "chinese": row["chinese"],
            "english": row["english"],
            "target_vocab_id": row["target_vocab_id"],
            "tags": json.loads(row["tags"]),
        }
