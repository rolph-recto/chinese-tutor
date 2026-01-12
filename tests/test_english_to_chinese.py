"""Unit tests for English to Chinese multiple choice exercise generation and handling."""

import pytest

from models import KnowledgePoint, KnowledgePointType
from exercises.chinese_adapter import ChineseExerciseAdapter
from exercises.generic_handlers import MultipleChoiceHandler


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
    """Tests for exercise generation via adapter."""

    def test_generate_exercise_returns_exercise(self, vocab_knowledge_points):
        """Should generate a valid exercise."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()

        assert exercise is not None
        assert exercise.metadata.get("direction") == "english_to_chinese"
        assert exercise.prompt != ""
        assert exercise.prompt_secondary == ""  # Not shown for English prompts
        assert len(exercise.source_ids) == 1

    def test_generate_exercise_has_4_options(self, vocab_knowledge_points):
        """Should generate exactly 4 options."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()

        assert exercise is not None
        assert len(exercise.options) == 4

    def test_generate_exercise_no_duplicate_options(self, vocab_knowledge_points):
        """All options should be distinct."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()

        assert exercise is not None
        assert len(set(exercise.options)) == 4

    def test_generate_exercise_options_include_pinyin(self, vocab_knowledge_points):
        """Options should include Chinese with pinyin."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()

        assert exercise is not None
        # Each option should have format "中文 (pīnyīn)"
        for option in exercise.options:
            assert "(" in option and ")" in option

    def test_generate_exercise_correct_index_valid(self, vocab_knowledge_points):
        """Correct index should be within bounds."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()

        assert exercise is not None
        assert 0 <= exercise.correct_index < 4

    def test_generate_exercise_with_target_kp(self, vocab_knowledge_points):
        """Should use target knowledge point when provided."""
        target = vocab_knowledge_points[0]  # "我"
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese(target_kp=target)

        assert exercise is not None
        assert '"I"' in exercise.prompt  # First English translation in prompt
        assert exercise.source_ids == ["v001"]
        # Correct answer should contain 我
        correct_option = exercise.options[exercise.correct_index]
        assert "我" in correct_option

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
        exercise = adapter.create_english_to_chinese()

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
        exercise = adapter.create_english_to_chinese()

        assert exercise is not None
        # Should not include grammar in source_ids
        assert all(kp_id.startswith("v") for kp_id in exercise.source_ids)

    def test_generate_exercise_prefers_same_cluster(self, vocab_knowledge_points):
        """Distractors should prefer items from the same cluster."""
        # Target a pronoun
        target = vocab_knowledge_points[0]  # "我" in cluster:pronouns
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)

        # Run multiple times to verify tendency
        same_cluster_count = 0
        trials = 20

        for _ in range(trials):
            exercise = adapter.create_english_to_chinese(target_kp=target)
            assert exercise is not None

            # Check if options contain pronoun characters
            pronoun_chars = {"我", "你", "他", "她"}
            options_from_pronouns = sum(
                1 for opt in exercise.options if any(c in opt for c in pronoun_chars)
            )
            if options_from_pronouns >= 3:  # At least 3 from same cluster
                same_cluster_count += 1

        # Should often get same-cluster distractors
        assert same_cluster_count >= trials // 2


class TestCheckAnswer:
    """Tests for answer checking via generic handler."""

    def test_check_answer_correct_letter(self, vocab_knowledge_points):
        """Correct letter answer should return True."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = handler.check_answer(correct_letter)

        assert is_correct is True

    def test_check_answer_correct_number(self, vocab_knowledge_points):
        """Correct number answer should return True."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        correct_number = str(exercise.correct_index + 1)
        is_correct, _ = handler.check_answer(correct_number)

        assert is_correct is True

    def test_check_answer_incorrect(self, vocab_knowledge_points):
        """Incorrect answer should return False."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        # Pick a wrong index
        wrong_index = (exercise.correct_index + 1) % 4
        wrong_letter = ["A", "B", "C", "D"][wrong_index]
        is_correct, _ = handler.check_answer(wrong_letter)

        assert is_correct is False

    def test_check_answer_returns_correct_answer(self, vocab_knowledge_points):
        """Should return the correct answer in the result."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        _, correct_answer = handler.check_answer("X")

        assert correct_answer == exercise.options[exercise.correct_index]

    def test_check_answer_invalid_input(self, vocab_knowledge_points):
        """Invalid input should return False."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        is_correct, _ = handler.check_answer("invalid")

        assert is_correct is False

    def test_check_answer_out_of_bounds(self, vocab_knowledge_points):
        """Out of bounds number should return False."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        is_correct, _ = handler.check_answer("5")

        assert is_correct is False

    def test_check_answer_lowercase_letter(self, vocab_knowledge_points):
        """Lowercase letters should be accepted."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        correct_letter = ["a", "b", "c", "d"][exercise.correct_index]
        is_correct, _ = handler.check_answer(correct_letter)

        assert is_correct is True

    def test_check_answer_with_whitespace(self, vocab_knowledge_points):
        """Input with whitespace should be handled."""
        adapter = ChineseExerciseAdapter(vocab_knowledge_points)
        exercise = adapter.create_english_to_chinese()
        assert exercise is not None

        handler = MultipleChoiceHandler(exercise)
        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = handler.check_answer(f"  {correct_letter}  ")

        assert is_correct is True
