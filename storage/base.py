"""Abstract repository interfaces for the storage layer."""

from abc import ABC, abstractmethod
from typing import Any

from models import (
    KnowledgePoint,
    StudentState,
    StudentMastery,
    UserTableMeta,
    UserRow,
)


class KnowledgePointRepository(ABC):
    """Abstract interface for knowledge point storage."""

    @abstractmethod
    def get_all(self) -> list[KnowledgePoint]:
        """Load all knowledge points.

        Returns:
            List of all knowledge points in the repository.
        """
        pass

    @abstractmethod
    def get_by_id(self, kp_id: str) -> KnowledgePoint | None:
        """Load a single knowledge point by ID.

        Args:
            kp_id: The knowledge point ID.

        Returns:
            The knowledge point, or None if not found.
        """
        pass

    @abstractmethod
    def get_by_type(self, kp_type: str) -> list[KnowledgePoint]:
        """Load knowledge points by type.

        Args:
            kp_type: The type ('vocabulary' or 'grammar').

        Returns:
            List of knowledge points matching the type.
        """
        pass


class StudentStateRepository(ABC):
    """Abstract interface for student state storage."""

    @abstractmethod
    def load(self) -> StudentState:
        """Load the complete student state.

        Returns:
            The student state with all masteries.
        """
        pass

    @abstractmethod
    def save(self, state: StudentState) -> None:
        """Save the complete student state.

        Args:
            state: The student state to save.
        """
        pass

    @abstractmethod
    def get_mastery(self, table_id: str, row_id: str) -> StudentMastery | None:
        """Get mastery for a single row.

        Args:
            table_id: The table ID.
            row_id: The row ID.

        Returns:
            The student mastery, or None if not found.
        """
        pass

    @abstractmethod
    def save_mastery(self, mastery: StudentMastery) -> None:
        """Save/update mastery for a single row.

        Args:
            mastery: The student mastery to save.
        """
        pass


class MinimalPairsRepository(ABC):
    """Abstract interface for minimal pairs storage."""

    @abstractmethod
    def get_distractors(self, target_id: str) -> list[dict] | None:
        """Get distractors for a target knowledge point.

        Args:
            target_id: The target knowledge point ID.

        Returns:
            List of distractor dictionaries, or None if no pairs defined.
        """
        pass

    @abstractmethod
    def get_all_target_ids(self) -> set[str]:
        """Get all target IDs that have minimal pairs defined.

        Returns:
            Set of target knowledge point IDs.
        """
        pass

    @abstractmethod
    def get_all_as_dict(self) -> dict[str, list[dict]]:
        """Get all minimal pairs as a dictionary.

        Returns:
            Dictionary mapping target_id to list of distractors.
        """
        pass


class ClozeTemplatesRepository(ABC):
    """Abstract interface for cloze template storage."""

    @abstractmethod
    def get_all(self) -> list[dict]:
        """Get all cloze templates.

        Returns:
            List of template dictionaries.
        """
        pass

    @abstractmethod
    def get_by_vocab_id(self, vocab_id: str) -> list[dict]:
        """Get templates for a specific vocabulary item.

        Args:
            vocab_id: The target vocabulary ID.

        Returns:
            List of template dictionaries for that vocabulary.
        """
        pass


# ============================================================================
# Dynamic Schema Repositories
# ============================================================================


class UserTableRepository(ABC):
    """Abstract interface for user-defined table metadata storage."""

    @abstractmethod
    def create_table(self, table_meta: UserTableMeta) -> None:
        """Create a new user table definition.

        Args:
            table_meta: The table metadata to create.

        Raises:
            ValueError: If table with same ID already exists.
        """
        pass

    @abstractmethod
    def get_table(self, table_id: str) -> UserTableMeta | None:
        """Get table metadata by ID.

        Args:
            table_id: The table ID.

        Returns:
            The table metadata, or None if not found.
        """
        pass

    @abstractmethod
    def get_all_tables(self) -> list[UserTableMeta]:
        """Get all table definitions.

        Returns:
            List of all table metadata.
        """
        pass

    @abstractmethod
    def delete_table(self, table_id: str) -> None:
        """Delete a table and all its rows.

        Args:
            table_id: The table ID to delete.
        """
        pass


class UserRowRepository(ABC):
    """Abstract interface for user-defined table row storage."""

    @abstractmethod
    def insert_row(self, row: UserRow) -> None:
        """Insert a new row (validates against table schema).

        Args:
            row: The row to insert.

        Raises:
            ValueError: If table doesn't exist or validation fails.
        """
        pass

    @abstractmethod
    def get_row(self, table_id: str, row_id: str) -> UserRow | None:
        """Get a specific row.

        Args:
            table_id: The table ID.
            row_id: The row ID.

        Returns:
            The row, or None if not found.
        """
        pass

    @abstractmethod
    def get_all_rows(self, table_id: str) -> list[UserRow]:
        """Get all rows for a table.

        Args:
            table_id: The table ID.

        Returns:
            List of all rows in the table.
        """
        pass

    @abstractmethod
    def query_rows(
        self,
        table_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[UserRow]:
        """Query rows with optional filtering.

        Args:
            table_id: The table ID.
            filters: Optional dict of column_name -> value to filter by.

        Returns:
            List of matching rows.
        """
        pass

    @abstractmethod
    def update_row(self, row: UserRow) -> None:
        """Update an existing row.

        Args:
            row: The row to update.

        Raises:
            ValueError: If row doesn't exist or validation fails.
        """
        pass

    @abstractmethod
    def delete_row(self, table_id: str, row_id: str) -> None:
        """Delete a row.

        Args:
            table_id: The table ID.
            row_id: The row ID.
        """
        pass
