"""SQLite implementations of repository interfaces."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import (
    KnowledgePointRepository,
    StudentStateRepository,
    MinimalPairsRepository,
    ClozeTemplatesRepository,
    UserTableRepository,
    UserRowRepository,
)
from .connection import get_connection, DEFAULT_DB_PATH
from models import (
    KnowledgePoint,
    KnowledgePointType,
    StudentState,
    StudentMastery,
    FSRSState,
    UserTableMeta,
    UserRow,
    ColumnDefinition,
    ColumnType,
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
                key = StudentState._make_key(mastery.table_id, mastery.row_id)
                masteries[key] = mastery
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

    def get_mastery(self, table_id: str, row_id: str) -> StudentMastery | None:
        """Get mastery for a single row."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM student_mastery WHERE table_id = ? AND row_id = ?",
                (table_id, row_id),
            )
            row = cursor.fetchone()
            return self._row_to_mastery(row) if row else None
        finally:
            conn.close()

    def save_mastery(self, mastery: StudentMastery) -> None:
        """Save/update mastery for a single row."""
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
            table_id=row["table_id"],
            row_id=row["row_id"],
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
            (table_id, row_id, stability, difficulty, due, last_review, state, step)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mastery.table_id,
                mastery.row_id,
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


# ============================================================================
# Dynamic Schema Repository Implementations
# ============================================================================


class SQLiteUserTableRepository(UserTableRepository):
    """SQLite implementation of UserTableRepository."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    def create_table(self, table_meta: UserTableMeta) -> None:
        """Create a new user table definition."""
        conn = get_connection(self.db_path)
        try:
            # Check if table already exists
            cursor = conn.execute(
                "SELECT 1 FROM user_tables WHERE table_id = ?",
                (table_meta.table_id,),
            )
            if cursor.fetchone():
                raise ValueError(f"Table {table_meta.table_id} already exists")

            # Serialize columns to JSON
            columns_json = json.dumps(
                [
                    {
                        "name": col.name,
                        "type": col.type.value,
                        "required": col.required,
                        "default": col.default,
                    }
                    for col in table_meta.columns
                ]
            )

            conn.execute(
                """INSERT INTO user_tables (table_id, table_name, columns)
                VALUES (?, ?, ?)""",
                (table_meta.table_id, table_meta.table_name, columns_json),
            )
            conn.commit()
        finally:
            conn.close()

    def get_table(self, table_id: str) -> UserTableMeta | None:
        """Get table metadata by ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM user_tables WHERE table_id = ?", (table_id,)
            )
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def get_all_tables(self) -> list[UserTableMeta]:
        """Get all table definitions."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM user_tables")
            return [self._row_to_model(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def delete_table(self, table_id: str) -> None:
        """Delete a table and all its rows."""
        conn = get_connection(self.db_path)
        try:
            # Delete rows first (foreign key constraint)
            conn.execute("DELETE FROM user_rows WHERE table_id = ?", (table_id,))
            conn.execute("DELETE FROM user_tables WHERE table_id = ?", (table_id,))
            conn.commit()
        finally:
            conn.close()

    def _row_to_model(self, row) -> UserTableMeta:
        """Convert a database row to a UserTableMeta model."""
        columns_data = json.loads(row["columns"])
        columns = [
            ColumnDefinition(
                name=col["name"],
                type=ColumnType(col["type"]),
                required=col.get("required", True),
                default=col.get("default"),
            )
            for col in columns_data
        ]
        return UserTableMeta(
            table_id=row["table_id"],
            table_name=row["table_name"],
            columns=columns,
        )


class SQLiteUserRowRepository(UserRowRepository):
    """SQLite implementation of UserRowRepository."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._table_repo = SQLiteUserTableRepository(db_path)

    def insert_row(self, row: UserRow) -> None:
        """Insert a new row (validates against table schema)."""
        # Validate against table schema
        table_meta = self._table_repo.get_table(row.table_id)
        if table_meta is None:
            raise ValueError(f"Table {row.table_id} does not exist")

        valid, errors = table_meta.validate_row(row.row_values)
        if not valid:
            raise ValueError(f"Row validation failed: {errors}")

        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """INSERT INTO user_rows (table_id, row_id, row_values)
                VALUES (?, ?, ?)""",
                (row.table_id, row.row_id, json.dumps(row.row_values)),
            )
            conn.commit()
        finally:
            conn.close()

    def get_row(self, table_id: str, row_id: str) -> UserRow | None:
        """Get a specific row."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM user_rows WHERE table_id = ? AND row_id = ?",
                (table_id, row_id),
            )
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def get_all_rows(self, table_id: str) -> list[UserRow]:
        """Get all rows for a table."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM user_rows WHERE table_id = ?", (table_id,)
            )
            return [self._row_to_model(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def query_rows(
        self,
        table_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[UserRow]:
        """Query rows with optional filtering.

        Note: Filtering is done in Python since SQLite JSON support varies.
        For large datasets, consider using JSON1 extension queries.
        """
        rows = self.get_all_rows(table_id)

        if filters is None:
            return rows

        # Filter in Python
        result = []
        for row in rows:
            match = True
            for key, value in filters.items():
                if row.row_values.get(key) != value:
                    match = False
                    break
            if match:
                result.append(row)

        return result

    def update_row(self, row: UserRow) -> None:
        """Update an existing row."""
        # Validate against table schema
        table_meta = self._table_repo.get_table(row.table_id)
        if table_meta is None:
            raise ValueError(f"Table {row.table_id} does not exist")

        valid, errors = table_meta.validate_row(row.row_values)
        if not valid:
            raise ValueError(f"Row validation failed: {errors}")

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                """UPDATE user_rows SET row_values = ?
                WHERE table_id = ? AND row_id = ?""",
                (json.dumps(row.row_values), row.table_id, row.row_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    f"Row {row.row_id} in table {row.table_id} does not exist"
                )
            conn.commit()
        finally:
            conn.close()

    def delete_row(self, table_id: str, row_id: str) -> None:
        """Delete a row."""
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                "DELETE FROM user_rows WHERE table_id = ? AND row_id = ?",
                (table_id, row_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_model(self, row) -> UserRow:
        """Convert a database row to a UserRow model."""
        return UserRow(
            table_id=row["table_id"],
            row_id=row["row_id"],
            row_values=json.loads(row["row_values"]),
        )
