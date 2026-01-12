"""Unit tests for cloze deletion exercise generation and handling."""

import json
import pytest

from models import KnowledgePoint, KnowledgePointType
from exercises.chinese_adapter import ChineseExerciseAdapter
from exercises.generic_handlers import FillBlankHandler
from storage import get_connection, init_schema, SQLiteClozeTemplatesRepository
import exercises.chinese_adapter


@pytest.fixture
def vocab_knowledge_points() -> list[KnowledgePoint]:
    """Create vocabulary knowledge points for testing (need at least 4)."""
    return [
        KnowledgePoint(
            id="v001",
            type=KnowledgePointType.VOCABULARY,
            chinese="我",
            pinyin="wǒ",
            english="I, me",
            tags=["hsk1", "cluster:pronouns"],
        ),
        KnowledgePoint(
            id="v002",
            type=KnowledgePointType.VOCABULARY,
            chinese="你",
            pinyin="nǐ",
            english="you",
            tags=["hsk1", "cluster:pronouns"],
        ),
        KnowledgePoint(
            id="v003",
            type=KnowledgePointType.VOCABULARY,
            chinese="他",
            pinyin="tā",
            english="he, him",
            tags=["hsk1", "cluster:pronouns"],
        ),
        KnowledgePoint(
            id="v004",
            type=KnowledgePointType.VOCABULARY,
            chinese="她",
            pinyin="tā",
            english="she, her",
            tags=["hsk1", "cluster:pronouns"],
        ),
        KnowledgePoint(
            id="v014",
            type=KnowledgePointType.VOCABULARY,
            chinese="水",
            pinyin="shuǐ",
            english="water",
            tags=["hsk1", "cluster:food-drink"],
        ),
        KnowledgePoint(
            id="v015",
            type=KnowledgePointType.VOCABULARY,
            chinese="茶",
            pinyin="chá",
            english="tea",
            tags=["hsk1", "cluster:food-drink"],
        ),
    ]


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch, vocab_knowledge_points):
    """Set up test database with cloze templates for each test."""
    test_db_path = tmp_path / "test_tutor.db"
    init_schema(test_db_path)

    conn = get_connection(test_db_path)
    try:
        # Insert vocabulary knowledge points
        for kp in vocab_knowledge_points:
            conn.execute(
                """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    kp.id,
                    kp.type.value,
                    kp.chinese,
                    kp.pinyin,
                    kp.english,
                    json.dumps(kp.tags),
                ),
            )

        # Insert cloze templates
        templates = [
            (
                "cloze001",
                "_____ 是学生。",
                "_____ am a student.",
                "v001",
                json.dumps(["hsk1"]),
            ),
            (
                "cloze002",
                "_____ 喝茶。",
                "_____ drink tea.",
                "v002",
                json.dumps(["hsk1"]),
            ),
        ]
        for template in templates:
            conn.execute(
                """INSERT INTO cloze_templates (id, chinese, english, target_vocab_id, tags)
                VALUES (?, ?, ?, ?, ?)""",
                template,
            )

        conn.commit()
    finally:
        conn.close()

    # Patch get_cloze_templates_repo to return a repository using the test database
    def _get_test_cloze_repo(db_path=None):
        return SQLiteClozeTemplatesRepository(test_db_path)

    monkeypatch.setattr(
        exercises.chinese_adapter, "get_cloze_templates_repo", _get_test_cloze_repo
    )

    return test_db_path


class TestGenerateExercise:
    """Tests for exercise generation via adapter."""

    def test_generate_exercise_returns_exercise(self, vocab_knowledge_points):
        """Should generate a valid exercise."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        assert exercise.sentence != ""
        assert exercise.context != ""
        assert exercise.metadata.get("target_word") != ""
        assert len(exercise.source_ids) == 1

    def test_generate_exercise_has_4_options(self, vocab_knowledge_points):
        """Should generate exactly 4 options."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        assert len(exercise.options) == 4

    def test_generate_exercise_no_duplicate_options(self, vocab_knowledge_points):
        """All options should be distinct."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        assert len(set(exercise.options)) == 4

    def test_generate_exercise_correct_index_valid(self, vocab_knowledge_points):
        """Correct index should be within bounds."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        assert 0 <= exercise.correct_index < 4

    def test_generate_exercise_correct_option_in_options(self, vocab_knowledge_points):
        """Correct word should be present in options."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        target_word = exercise.metadata.get("target_word")
        target_pinyin = exercise.metadata.get("target_pinyin")
        correct_option = f"{target_word} ({target_pinyin})"
        assert correct_option in exercise.options

    def test_generate_exercise_uses_correct_target(self, vocab_knowledge_points):
        """Target word from template should be the correct answer."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        correct_option = exercise.options[exercise.correct_index]
        target_word = exercise.metadata.get("target_word")
        assert target_word in correct_option

    def test_generate_exercise_insufficient_vocab(self):
        """Should return None if fewer than 4 vocabulary items."""
        small_vocab = [
            KnowledgePoint(
                id="v001",
                type=KnowledgePointType.VOCABULARY,
                chinese="我",
                pinyin="wǒ",
                english="I",
                tags=[],
            ),
            KnowledgePoint(
                id="v002",
                type=KnowledgePointType.VOCABULARY,
                chinese="你",
                pinyin="nǐ",
                english="you",
                tags=[],
            ),
        ]
        adapter = ChineseExerciseAdapter(small_vocab)
        exercise = adapter.create_cloze_deletion()

        assert exercise is None

    def test_generate_exercise_ignores_grammar_kps(self, vocab_knowledge_points):
        """Should only use vocabulary knowledge points."""
        kps_with_grammar = vocab_knowledge_points + [
            KnowledgePoint(
                id="g001",
                type=KnowledgePointType.GRAMMAR,
                chinese="Subject + 是 + Noun",
                pinyin="Subject + shì + Noun",
                english="Subject is Noun",
                tags=["hsk1"],
            )
        ]
        adapter = ChineseExerciseAdapter(kps_with_grammar)
        exercise = adapter.create_cloze_deletion()

        assert exercise is not None
        assert all(kp_id.startswith("v") for kp_id in exercise.source_ids)


class TestCheckAnswer:
    """Tests for answer checking via generic handler."""

    def test_check_answer_correct_letter(self, vocab_knowledge_points):
        """Correct letter answer should return True."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = handler.check_answer(correct_letter)

        assert is_correct is True

    def test_check_answer_correct_number(self, vocab_knowledge_points):
        """Correct number answer should return True."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        correct_number = str(exercise.correct_index + 1)
        is_correct, _ = handler.check_answer(correct_number)

        assert is_correct is True

    def test_check_answer_incorrect(self, vocab_knowledge_points):
        """Incorrect answer should return False."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        wrong_index = (exercise.correct_index + 1) % 4
        wrong_letter = ["A", "B", "C", "D"][wrong_index]
        is_correct, _ = handler.check_answer(wrong_letter)

        assert is_correct is False

    def test_check_answer_returns_correct_answer(self, vocab_knowledge_points):
        """Should return the correct answer in the result."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        _, correct_answer = handler.check_answer("X")

        assert correct_answer == exercise.options[exercise.correct_index]

    def test_check_answer_invalid_input(self, vocab_knowledge_points):
        """Invalid input should return False."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        is_correct, _ = handler.check_answer("invalid")

        assert is_correct is False

    def test_check_answer_out_of_bounds(self, vocab_knowledge_points):
        """Out of bounds number should return False."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        is_correct, _ = handler.check_answer("5")

        assert is_correct is False

    def test_check_answer_lowercase_letter(self, vocab_knowledge_points):
        """Lowercase letters should be accepted."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        correct_letter = ["a", "b", "c", "d"][exercise.correct_index]
        is_correct, _ = handler.check_answer(correct_letter)

        assert is_correct is True

    def test_check_answer_with_whitespace(self, vocab_knowledge_points):
        """Input with whitespace should be handled."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = handler.check_answer(f"  {correct_letter}  ")

        assert is_correct is True


class TestInputPrompt:
    """Tests for input prompt."""

    def test_get_input_prompt(self, vocab_knowledge_points):
        """Should return valid input prompt."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_cloze_deletion()
        assert exercise is not None

        handler = FillBlankHandler(exercise)
        prompt = handler.get_input_prompt()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert "choice" in prompt.lower()
