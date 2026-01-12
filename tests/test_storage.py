"""Tests for the storage layer repository implementations."""

from datetime import datetime, timedelta


from models import (
    KnowledgePoint,
    KnowledgePointType,
    StudentState,
    StudentMastery,
    FSRSState,
)
from storage import (
    SQLiteKnowledgePointRepository,
    SQLiteStudentStateRepository,
    SQLiteMinimalPairsRepository,
    SQLiteClozeTemplatesRepository,
    get_connection,
)


class TestKnowledgePointRepository:
    """Tests for SQLiteKnowledgePointRepository."""

    def test_get_all_returns_empty_for_empty_db(self, test_db_path):
        """Should return empty list when database has no knowledge points."""
        repo = SQLiteKnowledgePointRepository(test_db_path)
        result = repo.get_all()
        assert result == []

    def test_get_all_returns_all_knowledge_points(self, populated_test_db):
        """Should return all knowledge points from database."""
        repo = SQLiteKnowledgePointRepository(populated_test_db)
        result = repo.get_all()
        assert len(result) == 4  # 4 sample knowledge points
        assert all(isinstance(kp, KnowledgePoint) for kp in result)

    def test_get_by_id_returns_matching_kp(self, populated_test_db):
        """Should return knowledge point matching the given ID."""
        repo = SQLiteKnowledgePointRepository(populated_test_db)
        result = repo.get_by_id("v001")
        assert result is not None
        assert result.id == "v001"
        assert result.chinese == "我"
        assert result.type == KnowledgePointType.VOCABULARY

    def test_get_by_id_returns_none_for_unknown_id(self, populated_test_db):
        """Should return None when ID doesn't exist."""
        repo = SQLiteKnowledgePointRepository(populated_test_db)
        result = repo.get_by_id("nonexistent")
        assert result is None

    def test_get_by_type_returns_matching_kps(self, populated_test_db):
        """Should return knowledge points of the specified type."""
        repo = SQLiteKnowledgePointRepository(populated_test_db)
        vocab_kps = repo.get_by_type("vocabulary")
        grammar_kps = repo.get_by_type("grammar")

        assert len(vocab_kps) == 3  # v001, v002, v005
        assert len(grammar_kps) == 1  # g001
        assert all(kp.type == KnowledgePointType.VOCABULARY for kp in vocab_kps)
        assert all(kp.type == KnowledgePointType.GRAMMAR for kp in grammar_kps)

    def test_tags_deserialized_correctly(self, populated_test_db):
        """Should deserialize tags JSON array correctly."""
        repo = SQLiteKnowledgePointRepository(populated_test_db)
        result = repo.get_by_id("v001")
        assert isinstance(result.tags, list)
        assert "hsk1" in result.tags


class TestStudentStateRepository:
    """Tests for SQLiteStudentStateRepository."""

    def test_load_returns_empty_state_for_empty_db(self, test_db_path):
        """Should return empty StudentState when no masteries exist."""
        repo = SQLiteStudentStateRepository(test_db_path)
        result = repo.load()
        assert isinstance(result, StudentState)
        assert len(result.masteries) == 0

    def test_save_and_load_roundtrip(self, test_db_path):
        """Should correctly save and reload student state."""
        # Insert a knowledge point to satisfy foreign key
        conn = get_connection(test_db_path)
        conn.execute(
            """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("v001", "vocabulary", "我", "wǒ", "I, me", "[]"),
        )
        conn.commit()
        conn.close()

        repo = SQLiteStudentStateRepository(test_db_path)

        # Create a state with mastery records
        state = StudentState()
        state.masteries["v001"] = StudentMastery(
            knowledge_point_id="v001",
            fsrs_state=FSRSState(
                stability=5.0,
                difficulty=4.5,
                due=datetime(2024, 1, 15, 12, 0, 0),
                last_review=datetime(2024, 1, 10, 12, 0, 0),
                state=2,
                step=None,
            ),
        )

        repo.save(state)
        loaded = repo.load()

        assert len(loaded.masteries) == 1
        assert "v001" in loaded.masteries
        mastery = loaded.masteries["v001"]
        assert mastery.fsrs_state.stability == 5.0
        assert mastery.fsrs_state.difficulty == 4.5
        assert mastery.fsrs_state.state == 2

    def test_get_mastery_returns_matching_record(self, test_db_path):
        """Should return mastery for given knowledge point ID."""
        # Insert a knowledge point to satisfy foreign key
        conn = get_connection(test_db_path)
        conn.execute(
            """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("v001", "vocabulary", "我", "wǒ", "I, me", "[]"),
        )
        conn.commit()
        conn.close()

        repo = SQLiteStudentStateRepository(test_db_path)

        # Save a mastery record
        state = StudentState()
        state.masteries["v001"] = StudentMastery(
            knowledge_point_id="v001",
            fsrs_state=FSRSState(
                stability=3.0,
                difficulty=5.0,
                due=datetime.now(),
                last_review=datetime.now(),
                state=2,
                step=None,
            ),
        )
        repo.save(state)

        # Retrieve single mastery
        mastery = repo.get_mastery("v001")
        assert mastery is not None
        assert mastery.knowledge_point_id == "v001"

    def test_get_mastery_returns_none_for_unknown_id(self, test_db_path):
        """Should return None when mastery doesn't exist."""
        repo = SQLiteStudentStateRepository(test_db_path)
        result = repo.get_mastery("nonexistent")
        assert result is None

    def test_save_mastery_updates_existing(self, test_db_path):
        """Should update existing mastery when saving."""
        # Insert a knowledge point to satisfy foreign key
        conn = get_connection(test_db_path)
        conn.execute(
            """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("v001", "vocabulary", "我", "wǒ", "I, me", "[]"),
        )
        conn.commit()
        conn.close()

        repo = SQLiteStudentStateRepository(test_db_path)

        # Save initial mastery
        initial_mastery = StudentMastery(
            knowledge_point_id="v001",
            fsrs_state=FSRSState(
                stability=1.0,
                difficulty=5.0,
                due=datetime.now(),
                last_review=datetime.now(),
                state=1,
                step=0,
            ),
        )
        repo.save_mastery(initial_mastery)

        # Update with new values
        updated_mastery = StudentMastery(
            knowledge_point_id="v001",
            fsrs_state=FSRSState(
                stability=10.0,
                difficulty=4.0,
                due=datetime.now() + timedelta(days=5),
                last_review=datetime.now(),
                state=2,
                step=None,
            ),
        )
        repo.save_mastery(updated_mastery)

        # Verify update
        loaded = repo.get_mastery("v001")
        assert loaded.fsrs_state.stability == 10.0
        assert loaded.fsrs_state.difficulty == 4.0


class TestMinimalPairsRepository:
    """Tests for SQLiteMinimalPairsRepository."""

    def test_get_distractors_returns_matching_pairs(self, populated_test_db):
        """Should return distractors for target knowledge point."""
        repo = SQLiteMinimalPairsRepository(populated_test_db)
        result = repo.get_distractors("v001")

        assert result is not None
        assert len(result) == 1
        assert result[0]["chinese"] == "找"
        assert result[0]["pinyin"] == "zhǎo"

    def test_get_distractors_returns_none_for_unknown_target(self, populated_test_db):
        """Should return None when target has no distractors."""
        repo = SQLiteMinimalPairsRepository(populated_test_db)
        result = repo.get_distractors("nonexistent")
        assert result is None

    def test_get_all_target_ids(self, populated_test_db):
        """Should return set of all target IDs."""
        repo = SQLiteMinimalPairsRepository(populated_test_db)
        result = repo.get_all_target_ids()

        assert isinstance(result, set)
        assert "v001" in result

    def test_get_all_as_dict(self, populated_test_db):
        """Should return dict mapping target_id to distractors."""
        repo = SQLiteMinimalPairsRepository(populated_test_db)
        result = repo.get_all_as_dict()

        assert isinstance(result, dict)
        assert "v001" in result
        assert len(result["v001"]) == 1


class TestClozeTemplatesRepository:
    """Tests for SQLiteClozeTemplatesRepository."""

    def test_get_all_returns_all_templates(self, populated_test_db):
        """Should return all cloze templates."""
        repo = SQLiteClozeTemplatesRepository(populated_test_db)
        result = repo.get_all()

        assert len(result) == 1
        assert result[0]["id"] == "cloze001"
        assert result[0]["target_vocab_id"] == "v001"

    def test_get_by_vocab_id_returns_matching_templates(self, populated_test_db):
        """Should return templates for specified vocabulary."""
        repo = SQLiteClozeTemplatesRepository(populated_test_db)
        result = repo.get_by_vocab_id("v001")

        assert len(result) == 1
        assert result[0]["chinese"] == "_____ 是学生。"

    def test_get_by_vocab_id_returns_empty_for_unknown(self, populated_test_db):
        """Should return empty list when vocab has no templates."""
        repo = SQLiteClozeTemplatesRepository(populated_test_db)
        result = repo.get_by_vocab_id("nonexistent")
        assert result == []

    def test_tags_deserialized_correctly(self, populated_test_db):
        """Should deserialize tags JSON array correctly."""
        repo = SQLiteClozeTemplatesRepository(populated_test_db)
        result = repo.get_all()

        assert isinstance(result[0]["tags"], list)
        assert "hsk1" in result[0]["tags"]
