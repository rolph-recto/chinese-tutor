"""Adapters for backwards compatibility with legacy code.

These adapters allow code written for the fixed schema (KnowledgePoint,
MinimalPairs, ClozeTemplates) to work with the dynamic schema system.
"""

from models import KnowledgePoint, KnowledgePointType, UserRow
from .base import UserRowRepository, KnowledgePointRepository


class KnowledgePointAdapter(KnowledgePointRepository):
    """Adapts UserRowRepository to provide KnowledgePoint interface.

    This adapter reads from the dynamic schema (user_rows table) and
    returns KnowledgePoint objects for backwards compatibility.
    """

    TABLE_ID = "knowledge_points"

    def __init__(self, row_repo: UserRowRepository):
        self.row_repo = row_repo

    def get_all(self) -> list[KnowledgePoint]:
        """Get all knowledge points (adapts from UserRows)."""
        rows = self.row_repo.get_all_rows(self.TABLE_ID)
        return [self._row_to_kp(row) for row in rows]

    def get_by_id(self, kp_id: str) -> KnowledgePoint | None:
        """Get knowledge point by ID."""
        row = self.row_repo.get_row(self.TABLE_ID, kp_id)
        return self._row_to_kp(row) if row else None

    def get_by_type(self, kp_type: str) -> list[KnowledgePoint]:
        """Get knowledge points by type."""
        rows = self.row_repo.query_rows(self.TABLE_ID, filters={"type": kp_type})
        return [self._row_to_kp(row) for row in rows]

    def _row_to_kp(self, row: UserRow) -> KnowledgePoint:
        """Convert UserRow to KnowledgePoint."""
        v = row.row_values
        return KnowledgePoint(
            id=v["id"],
            type=KnowledgePointType(v["type"]),
            chinese=v["chinese"],
            pinyin=v["pinyin"],
            english=v["english"],
            tags=v.get("tags", []),
        )


class MinimalPairsAdapter:
    """Adapts UserRowRepository to provide MinimalPairs interface.

    This adapter reads from the dynamic schema (user_rows table) and
    returns minimal pairs data for backwards compatibility.
    """

    TABLE_ID = "minimal_pairs"

    def __init__(self, row_repo: UserRowRepository):
        self.row_repo = row_repo

    def get_distractors(self, target_id: str) -> list[dict] | None:
        """Get distractors for a target knowledge point."""
        rows = self.row_repo.query_rows(self.TABLE_ID, filters={"target_id": target_id})
        if not rows:
            return None
        return [
            {
                "chinese": row.row_values["distractor_chinese"],
                "pinyin": row.row_values["distractor_pinyin"],
                "english": row.row_values["distractor_english"],
                "reason": row.row_values.get("reason"),
            }
            for row in rows
        ]

    def get_all_target_ids(self) -> set[str]:
        """Get all target IDs that have minimal pairs defined."""
        rows = self.row_repo.get_all_rows(self.TABLE_ID)
        return {row.row_values["target_id"] for row in rows}

    def get_all_as_dict(self) -> dict[str, list[dict]]:
        """Get all minimal pairs as a dictionary."""
        rows = self.row_repo.get_all_rows(self.TABLE_ID)
        result: dict[str, list[dict]] = {}
        for row in rows:
            target_id = row.row_values["target_id"]
            if target_id not in result:
                result[target_id] = []
            result[target_id].append(
                {
                    "chinese": row.row_values["distractor_chinese"],
                    "pinyin": row.row_values["distractor_pinyin"],
                    "english": row.row_values["distractor_english"],
                    "reason": row.row_values.get("reason"),
                }
            )
        return result


class ClozeTemplatesAdapter:
    """Adapts UserRowRepository to provide ClozeTemplates interface.

    This adapter reads from the dynamic schema (user_rows table) and
    returns cloze template data for backwards compatibility.
    """

    TABLE_ID = "cloze_templates"

    def __init__(self, row_repo: UserRowRepository):
        self.row_repo = row_repo

    def get_all(self) -> list[dict]:
        """Get all cloze templates."""
        rows = self.row_repo.get_all_rows(self.TABLE_ID)
        return [self._row_to_dict(row) for row in rows]

    def get_by_vocab_id(self, vocab_id: str) -> list[dict]:
        """Get templates for a specific vocabulary item."""
        rows = self.row_repo.query_rows(
            self.TABLE_ID, filters={"target_vocab_id": vocab_id}
        )
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: UserRow) -> dict:
        """Convert UserRow to template dictionary."""
        v = row.row_values
        return {
            "id": v["id"],
            "chinese": v["chinese"],
            "english": v["english"],
            "target_vocab_id": v["target_vocab_id"],
            "tags": v.get("tags", []),
        }
