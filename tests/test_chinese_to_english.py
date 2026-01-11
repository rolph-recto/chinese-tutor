"""Unit tests for Chinese to English multiple choice exercise."""

import pytest

from models import KnowledgePoint, KnowledgePointType
from exercises import chinese_to_english


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
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)

        assert exercise is not None
        assert exercise.direction == "chinese_to_english"
        assert exercise.prompt != ""
        assert exercise.prompt_pinyin != ""
        assert len(exercise.knowledge_point_ids) == 1

    def test_generate_exercise_has_4_options(self, vocab_knowledge_points):
        """Should generate exactly 4 options."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)

        assert exercise is not None
        assert len(exercise.options) == 4

    def test_generate_exercise_no_duplicate_options(self, vocab_knowledge_points):
        """All options should be distinct."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)

        assert exercise is not None
        assert len(set(exercise.options)) == 4

    def test_generate_exercise_correct_index_valid(self, vocab_knowledge_points):
        """Correct index should be within bounds."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)

        assert exercise is not None
        assert 0 <= exercise.correct_index < 4

    def test_generate_exercise_with_target_kp(self, vocab_knowledge_points):
        """Should use target knowledge point when provided."""
        target = vocab_knowledge_points[0]  # "我"
        exercise = chinese_to_english.generate_exercise(
            vocab_knowledge_points, target_kp=target
        )

        assert exercise is not None
        assert exercise.prompt == "我"
        assert exercise.prompt_pinyin == "wǒ"
        assert exercise.knowledge_point_ids == ["v001"]

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
        exercise = chinese_to_english.generate_exercise(small_vocab)

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
        exercise = chinese_to_english.generate_exercise(kps_with_grammar)

        assert exercise is not None
        # Should not include grammar in knowledge_point_ids
        assert all(kp_id.startswith("v") for kp_id in exercise.knowledge_point_ids)

    def test_generate_exercise_prefers_same_cluster(self, vocab_knowledge_points):
        """Distractors should prefer items from the same cluster."""
        # Target a pronoun
        target = vocab_knowledge_points[0]  # "我" in cluster:pronouns

        # Run multiple times to verify tendency
        same_cluster_count = 0
        trials = 20

        for _ in range(trials):
            exercise = chinese_to_english.generate_exercise(
                vocab_knowledge_points, target_kp=target
            )
            assert exercise is not None

            # Get English translations for pronouns
            pronoun_english = {"I", "you", "he", "she"}
            options_from_pronouns = sum(
                1 for opt in exercise.options if any(p in opt for p in pronoun_english)
            )
            if options_from_pronouns >= 3:  # At least 3 from same cluster
                same_cluster_count += 1

        # Should often get same-cluster distractors
        assert same_cluster_count >= trials // 2


class TestCheckAnswer:
    """Tests for answer checking."""

    def test_check_answer_correct_letter(self, vocab_knowledge_points):
        """Correct letter answer should return True."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = chinese_to_english.check_answer(exercise, correct_letter)

        assert is_correct is True

    def test_check_answer_correct_number(self, vocab_knowledge_points):
        """Correct number answer should return True."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        correct_number = str(exercise.correct_index + 1)
        is_correct, _ = chinese_to_english.check_answer(exercise, correct_number)

        assert is_correct is True

    def test_check_answer_incorrect(self, vocab_knowledge_points):
        """Incorrect answer should return False."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        # Pick a wrong index
        wrong_index = (exercise.correct_index + 1) % 4
        wrong_letter = ["A", "B", "C", "D"][wrong_index]
        is_correct, _ = chinese_to_english.check_answer(exercise, wrong_letter)

        assert is_correct is False

    def test_check_answer_returns_correct_answer(self, vocab_knowledge_points):
        """Should return the correct answer in the result."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        _, correct_answer = chinese_to_english.check_answer(exercise, "X")

        assert correct_answer == exercise.options[exercise.correct_index]

    def test_check_answer_invalid_input(self, vocab_knowledge_points):
        """Invalid input should return False."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        is_correct, _ = chinese_to_english.check_answer(exercise, "invalid")

        assert is_correct is False

    def test_check_answer_out_of_bounds(self, vocab_knowledge_points):
        """Out of bounds number should return False."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        is_correct, _ = chinese_to_english.check_answer(exercise, "5")

        assert is_correct is False

    def test_check_answer_lowercase_letter(self, vocab_knowledge_points):
        """Lowercase letters should be accepted."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        correct_letter = ["a", "b", "c", "d"][exercise.correct_index]
        is_correct, _ = chinese_to_english.check_answer(exercise, correct_letter)

        assert is_correct is True

    def test_check_answer_with_whitespace(self, vocab_knowledge_points):
        """Input with whitespace should be handled."""
        exercise = chinese_to_english.generate_exercise(vocab_knowledge_points)
        assert exercise is not None

        correct_letter = ["A", "B", "C", "D"][exercise.correct_index]
        is_correct, _ = chinese_to_english.check_answer(
            exercise, f"  {correct_letter}  "
        )

        assert is_correct is True
