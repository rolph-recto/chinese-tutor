"""Unit tests for cloze deletion exercise."""

import pytest

from models import KnowledgePoint, KnowledgePointType
from exercises.cloze_deletion import ClozeDeletionHandler


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


class TestGenerateExercise:
    """Tests for exercise generation."""

    def test_generate_exercise_returns_exercise(self, vocab_knowledge_points):
        """Should generate a valid exercise."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)

        assert exercise is not None
        assert exercise.chinese_sentence != ""
        assert exercise.english_translation != ""
        assert exercise.target_word != ""
        assert len(exercise.knowledge_point_ids) == 1

    def test_generate_exercise_has_4_options(self, vocab_knowledge_points):
        """Should generate exactly 4 options."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)

        assert exercise is not None
        assert len(exercise.options) == 4

    def test_generate_exercise_no_duplicate_options(self, vocab_knowledge_points):
        """All options should be distinct."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)

        assert exercise is not None
        assert len(set(exercise.options)) == 4

    def test_generate_exercise_correct_index_valid(self, vocab_knowledge_points):
        """Correct index should be within bounds."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)

        assert exercise is not None
        assert 0 <= exercise.correct_index < 4

    def test_generate_exercise_correct_option_in_options(self, vocab_knowledge_points):
        """Correct word should be present in options."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)

        assert exercise is not None
        correct_option = f"{exercise.target_word} ({exercise.target_pinyin})"
        assert correct_option in exercise.options

    def test_generate_exercise_uses_correct_target(self, vocab_knowledge_points):
        """Target word from template should be the correct answer."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)

        assert exercise is not None
        correct_option = exercise.options[exercise.correct_index]
        assert exercise.target_word in correct_option

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
        exercise = ClozeDeletionHandler.generate(small_vocab)

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
        exercise = ClozeDeletionHandler.generate(kps_with_grammar)

        assert exercise is not None
        assert all(kp_id.startswith("v") for kp_id in exercise.knowledge_point_ids)


class TestCheckAnswer:
    """Tests for answer checking."""

    def test_check_answer_correct_letter(self, vocab_knowledge_points):
        """Correct letter answer should return True."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = handler.check_answer(correct_letter)

        assert is_correct is True

    def test_check_answer_correct_number(self, vocab_knowledge_points):
        """Correct number answer should return True."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        correct_number = str(exercise.correct_index + 1)
        is_correct, _ = handler.check_answer(correct_number)

        assert is_correct is True

    def test_check_answer_incorrect(self, vocab_knowledge_points):
        """Incorrect answer should return False."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        wrong_index = (exercise.correct_index + 1) % 4
        wrong_letter = ["A", "B", "C", "D"][wrong_index]
        is_correct, _ = handler.check_answer(wrong_letter)

        assert is_correct is False

    def test_check_answer_returns_correct_answer(self, vocab_knowledge_points):
        """Should return the correct answer in the result."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        _, correct_answer = handler.check_answer("X")

        assert correct_answer == exercise.options[exercise.correct_index]

    def test_check_answer_invalid_input(self, vocab_knowledge_points):
        """Invalid input should return False."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        is_correct, _ = handler.check_answer("invalid")

        assert is_correct is False

    def test_check_answer_out_of_bounds(self, vocab_knowledge_points):
        """Out of bounds number should return False."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        is_correct, _ = handler.check_answer("5")

        assert is_correct is False

    def test_check_answer_lowercase_letter(self, vocab_knowledge_points):
        """Lowercase letters should be accepted."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        correct_letter = ["a", "b", "c", "d"][exercise.correct_index]
        is_correct, _ = handler.check_answer(correct_letter)

        assert is_correct is True

    def test_check_answer_with_whitespace(self, vocab_knowledge_points):
        """Input with whitespace should be handled."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = handler.check_answer(f"  {correct_letter}  ")

        assert is_correct is True


class TestInputPrompt:
    """Tests for input prompt."""

    def test_get_input_prompt(self, vocab_knowledge_points):
        """Should return valid input prompt."""
        exercise = ClozeDeletionHandler.generate(vocab_knowledge_points)
        assert exercise is not None

        handler = ClozeDeletionHandler(exercise)
        prompt = handler.get_input_prompt()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert "choice" in prompt.lower()
