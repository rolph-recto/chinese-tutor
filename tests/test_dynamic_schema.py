"""Tests for dynamic schema functionality."""

import pytest

from models import (
    ColumnType,
    ColumnDefinition,
    UserTableMeta,
    UserRow,
)
from storage import (
    SQLiteUserTableRepository,
    SQLiteUserRowRepository,
    get_knowledge_point_adapter,
    get_minimal_pairs_adapter,
    get_cloze_templates_adapter,
)
from storage.migrations import migrate_to_dynamic_schema, check_migration_status


class TestUserTableMetaValidation:
    """Tests for UserTableMeta row validation."""

    def test_validate_row_with_valid_data(self):
        """Should return True for valid row data."""
        table = UserTableMeta(
            table_id="test",
            table_name="Test Table",
            columns=[
                ColumnDefinition(name="name", type=ColumnType.TEXT),
                ColumnDefinition(name="age", type=ColumnType.INTEGER),
            ],
        )
        valid, errors = table.validate_row({"name": "Alice", "age": 30})
        assert valid is True
        assert errors == []

    def test_validate_row_missing_required_column(self):
        """Should return error for missing required column."""
        table = UserTableMeta(
            table_id="test",
            table_name="Test Table",
            columns=[
                ColumnDefinition(name="name", type=ColumnType.TEXT, required=True),
            ],
        )
        valid, errors = table.validate_row({})
        assert valid is False
        assert "Missing required column: name" in errors

    def test_validate_row_with_optional_column(self):
        """Should allow missing optional columns."""
        table = UserTableMeta(
            table_id="test",
            table_name="Test Table",
            columns=[
                ColumnDefinition(name="name", type=ColumnType.TEXT, required=True),
                ColumnDefinition(name="nickname", type=ColumnType.TEXT, required=False),
            ],
        )
        valid, errors = table.validate_row({"name": "Alice"})
        assert valid is True
        assert errors == []

    def test_validate_row_type_mismatch(self):
        """Should return error for type mismatch."""
        table = UserTableMeta(
            table_id="test",
            table_name="Test Table",
            columns=[
                ColumnDefinition(name="age", type=ColumnType.INTEGER),
            ],
        )
        valid, errors = table.validate_row({"age": "not an integer"})
        assert valid is False
        assert any("expected INTEGER" in e for e in errors)

    def test_validate_json_type(self):
        """Should validate JSON column types."""
        table = UserTableMeta(
            table_id="test",
            table_name="Test Table",
            columns=[
                ColumnDefinition(name="tags", type=ColumnType.JSON),
            ],
        )
        # Valid: list
        valid, errors = table.validate_row({"tags": ["a", "b"]})
        assert valid is True

        # Valid: dict
        valid, errors = table.validate_row({"tags": {"key": "value"}})
        assert valid is True

        # Invalid: string
        valid, errors = table.validate_row({"tags": "not json"})
        assert valid is False


class TestUserTableRepository:
    """Tests for SQLiteUserTableRepository."""

    def test_create_and_get_table(self, test_db_path):
        """Should create and retrieve table metadata."""
        repo = SQLiteUserTableRepository(test_db_path)

        table = UserTableMeta(
            table_id="vocabulary",
            table_name="Vocabulary",
            columns=[
                ColumnDefinition(name="word", type=ColumnType.TEXT),
                ColumnDefinition(name="definition", type=ColumnType.TEXT),
            ],
        )
        repo.create_table(table)

        loaded = repo.get_table("vocabulary")
        assert loaded is not None
        assert loaded.table_id == "vocabulary"
        assert loaded.table_name == "Vocabulary"
        assert len(loaded.columns) == 2

    def test_create_duplicate_table_raises_error(self, test_db_path):
        """Should raise error when creating duplicate table."""
        repo = SQLiteUserTableRepository(test_db_path)

        table = UserTableMeta(
            table_id="test",
            table_name="Test",
            columns=[ColumnDefinition(name="x", type=ColumnType.TEXT)],
        )
        repo.create_table(table)

        with pytest.raises(ValueError, match="already exists"):
            repo.create_table(table)

    def test_get_all_tables(self, test_db_path):
        """Should return all tables."""
        repo = SQLiteUserTableRepository(test_db_path)

        table1 = UserTableMeta(
            table_id="t1",
            table_name="Table 1",
            columns=[ColumnDefinition(name="x", type=ColumnType.TEXT)],
        )
        table2 = UserTableMeta(
            table_id="t2",
            table_name="Table 2",
            columns=[ColumnDefinition(name="y", type=ColumnType.INTEGER)],
        )
        repo.create_table(table1)
        repo.create_table(table2)

        tables = repo.get_all_tables()
        assert len(tables) == 2

    def test_delete_table(self, test_db_path):
        """Should delete table and its rows."""
        table_repo = SQLiteUserTableRepository(test_db_path)
        row_repo = SQLiteUserRowRepository(test_db_path)

        table = UserTableMeta(
            table_id="test",
            table_name="Test",
            columns=[ColumnDefinition(name="x", type=ColumnType.TEXT)],
        )
        table_repo.create_table(table)
        row_repo.insert_row(
            UserRow(table_id="test", row_id="r1", row_values={"x": "value"})
        )

        table_repo.delete_table("test")

        assert table_repo.get_table("test") is None
        assert row_repo.get_all_rows("test") == []


class TestUserRowRepository:
    """Tests for SQLiteUserRowRepository."""

    @pytest.fixture
    def table_with_rows(self, test_db_path):
        """Create a table for row testing."""
        table_repo = SQLiteUserTableRepository(test_db_path)
        table = UserTableMeta(
            table_id="items",
            table_name="Items",
            columns=[
                ColumnDefinition(name="name", type=ColumnType.TEXT),
                ColumnDefinition(name="count", type=ColumnType.INTEGER),
            ],
        )
        table_repo.create_table(table)
        return test_db_path

    def test_insert_and_get_row(self, table_with_rows):
        """Should insert and retrieve row."""
        repo = SQLiteUserRowRepository(table_with_rows)

        row = UserRow(
            table_id="items", row_id="item1", row_values={"name": "Widget", "count": 5}
        )
        repo.insert_row(row)

        loaded = repo.get_row("items", "item1")
        assert loaded is not None
        assert loaded.row_values["name"] == "Widget"
        assert loaded.row_values["count"] == 5

    def test_insert_row_validates_types(self, table_with_rows):
        """Should reject rows with invalid types."""
        repo = SQLiteUserRowRepository(table_with_rows)

        row = UserRow(
            table_id="items",
            row_id="item1",
            row_values={"name": "Widget", "count": "not an integer"},
        )
        with pytest.raises(ValueError, match="validation failed"):
            repo.insert_row(row)

    def test_insert_row_for_nonexistent_table(self, test_db_path):
        """Should reject rows for tables that don't exist."""
        repo = SQLiteUserRowRepository(test_db_path)

        row = UserRow(table_id="nonexistent", row_id="r1", row_values={"x": "y"})
        with pytest.raises(ValueError, match="does not exist"):
            repo.insert_row(row)

    def test_get_all_rows(self, table_with_rows):
        """Should return all rows for a table."""
        repo = SQLiteUserRowRepository(table_with_rows)

        repo.insert_row(
            UserRow(
                table_id="items",
                row_id="item1",
                row_values={"name": "A", "count": 1},
            )
        )
        repo.insert_row(
            UserRow(
                table_id="items",
                row_id="item2",
                row_values={"name": "B", "count": 2},
            )
        )

        rows = repo.get_all_rows("items")
        assert len(rows) == 2

    def test_query_rows_with_filters(self, table_with_rows):
        """Should filter rows by column values."""
        repo = SQLiteUserRowRepository(table_with_rows)

        repo.insert_row(
            UserRow(
                table_id="items",
                row_id="item1",
                row_values={"name": "Widget", "count": 5},
            )
        )
        repo.insert_row(
            UserRow(
                table_id="items",
                row_id="item2",
                row_values={"name": "Gadget", "count": 5},
            )
        )
        repo.insert_row(
            UserRow(
                table_id="items",
                row_id="item3",
                row_values={"name": "Widget", "count": 3},
            )
        )

        # Filter by name
        results = repo.query_rows("items", filters={"name": "Widget"})
        assert len(results) == 2

        # Filter by count
        results = repo.query_rows("items", filters={"count": 5})
        assert len(results) == 2

    def test_update_row(self, table_with_rows):
        """Should update existing row."""
        repo = SQLiteUserRowRepository(table_with_rows)

        row = UserRow(
            table_id="items", row_id="item1", row_values={"name": "Widget", "count": 5}
        )
        repo.insert_row(row)

        updated = UserRow(
            table_id="items",
            row_id="item1",
            row_values={"name": "Widget Pro", "count": 10},
        )
        repo.update_row(updated)

        loaded = repo.get_row("items", "item1")
        assert loaded.row_values["name"] == "Widget Pro"
        assert loaded.row_values["count"] == 10

    def test_delete_row(self, table_with_rows):
        """Should delete row."""
        repo = SQLiteUserRowRepository(table_with_rows)

        row = UserRow(
            table_id="items", row_id="item1", row_values={"name": "Widget", "count": 5}
        )
        repo.insert_row(row)

        repo.delete_row("items", "item1")
        assert repo.get_row("items", "item1") is None


class TestMigration:
    """Tests for database migration."""

    def test_migrate_knowledge_points(self, populated_test_db):
        """Should migrate knowledge_points to dynamic schema."""
        migrate_to_dynamic_schema(populated_test_db)

        table_repo = SQLiteUserTableRepository(populated_test_db)
        row_repo = SQLiteUserRowRepository(populated_test_db)

        # Check table was created
        table = table_repo.get_table("knowledge_points")
        assert table is not None
        assert table.table_name == "Knowledge Points"

        # Check rows were migrated
        rows = row_repo.get_all_rows("knowledge_points")
        assert len(rows) == 4  # 4 sample knowledge points

    def test_migrate_is_idempotent(self, populated_test_db):
        """Running migration multiple times should be safe."""
        migrate_to_dynamic_schema(populated_test_db)
        migrate_to_dynamic_schema(populated_test_db)  # Should not raise

        rows_repo = SQLiteUserRowRepository(populated_test_db)

        # Should still have correct data
        rows = rows_repo.get_all_rows("knowledge_points")
        assert len(rows) == 4

    def test_check_migration_status(self, populated_test_db):
        """Should correctly report migration status."""
        # Before migration
        status = check_migration_status(populated_test_db)
        assert status["is_migrated"] is False
        assert status["legacy_data_exists"] is True

        # After migration
        migrate_to_dynamic_schema(populated_test_db)
        status = check_migration_status(populated_test_db)
        assert status["is_migrated"] is True
        assert "knowledge_points" in status["tables_migrated"]


class TestAdaptersAfterMigration:
    """Tests for backwards compatibility adapters after migration."""

    @pytest.fixture
    def migrated_db(self, populated_test_db):
        """Create a migrated test database."""
        migrate_to_dynamic_schema(populated_test_db)
        return populated_test_db

    def test_knowledge_point_adapter_get_all(self, migrated_db):
        """Should return all knowledge points via adapter."""
        adapter = get_knowledge_point_adapter(migrated_db)
        kps = adapter.get_all()
        assert len(kps) == 4

    def test_knowledge_point_adapter_get_by_id(self, migrated_db):
        """Should return knowledge point by ID via adapter."""
        adapter = get_knowledge_point_adapter(migrated_db)
        kp = adapter.get_by_id("v001")
        assert kp is not None
        assert kp.id == "v001"
        assert kp.chinese == "我"

    def test_knowledge_point_adapter_get_by_type(self, migrated_db):
        """Should return knowledge points by type via adapter."""
        adapter = get_knowledge_point_adapter(migrated_db)
        vocab = adapter.get_by_type("vocabulary")
        grammar = adapter.get_by_type("grammar")
        assert len(vocab) == 3
        assert len(grammar) == 1

    def test_minimal_pairs_adapter(self, migrated_db):
        """Should return minimal pairs via adapter."""
        adapter = get_minimal_pairs_adapter(migrated_db)
        distractors = adapter.get_distractors("v001")
        assert distractors is not None
        assert len(distractors) == 1
        assert distractors[0]["chinese"] == "找"

    def test_cloze_templates_adapter(self, migrated_db):
        """Should return cloze templates via adapter."""
        adapter = get_cloze_templates_adapter(migrated_db)
        templates = adapter.get_all()
        assert len(templates) == 1
        assert templates[0]["target_vocab_id"] == "v001"
