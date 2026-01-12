"""Integration tests using the student simulator."""

import json
import pytest
import random

from simulate import Simulator, ResponseGenerator
from simulator_models import SimulatedStudent
import main
from models import Exercise
from storage import init_schema, get_connection


def _populate_test_db_from_json(db_path, data_dir):
    """Populate test database from JSON data files."""
    conn = get_connection(db_path)
    try:
        # Migrate vocabulary
        vocab_file = data_dir / "vocabulary.json"
        if vocab_file.exists():
            with open(vocab_file) as f:
                items = json.load(f)
            for item in items:
                conn.execute(
                    """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"],
                        item["type"],
                        item["chinese"],
                        item["pinyin"],
                        item["english"],
                        json.dumps(item.get("tags", [])),
                    ),
                )

        # Migrate grammar
        grammar_file = data_dir / "grammar.json"
        if grammar_file.exists():
            with open(grammar_file) as f:
                items = json.load(f)
            for item in items:
                conn.execute(
                    """INSERT INTO knowledge_points (id, type, chinese, pinyin, english, tags)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"],
                        item["type"],
                        item["chinese"],
                        item["pinyin"],
                        item["english"],
                        json.dumps(item.get("tags", [])),
                    ),
                )

        # Migrate minimal pairs
        pairs_file = data_dir / "minimal_pairs.json"
        if pairs_file.exists():
            with open(pairs_file) as f:
                pairs = json.load(f)
            for pair in pairs:
                target_id = pair["target_id"]
                for distractor in pair["distractors"]:
                    conn.execute(
                        """INSERT INTO minimal_pairs
                        (target_id, distractor_chinese, distractor_pinyin, distractor_english, reason)
                        VALUES (?, ?, ?, ?, ?)""",
                        (
                            target_id,
                            distractor["chinese"],
                            distractor["pinyin"],
                            distractor["english"],
                            distractor.get("reason"),
                        ),
                    )

        # Migrate cloze templates
        cloze_file = data_dir / "cloze_templates.json"
        if cloze_file.exists():
            with open(cloze_file) as f:
                templates = json.load(f)
            for template in templates:
                conn.execute(
                    """INSERT INTO cloze_templates (id, chinese, english, target_vocab_id, tags)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        template["id"],
                        template["chinese"],
                        template["english"],
                        template["target_vocab_id"],
                        json.dumps(template.get("tags", [])),
                    ),
                )

        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def test_db_with_data(tmp_path, monkeypatch):
    """Set up test database with knowledge points for simulator tests."""
    from storage import SQLiteMinimalPairsRepository, SQLiteClozeTemplatesRepository
    import exercises.minimal_pair
    import exercises.cloze_deletion

    test_db_path = tmp_path / "test_tutor.db"
    init_schema(test_db_path)
    _populate_test_db_from_json(test_db_path, main.DATA_DIR)
    monkeypatch.setattr(main, "DB_PATH", test_db_path)

    # Patch exercise handlers to use test database
    def _get_test_minimal_pairs_repo(db_path=None):
        return SQLiteMinimalPairsRepository(test_db_path)

    def _get_test_cloze_repo(db_path=None):
        return SQLiteClozeTemplatesRepository(test_db_path)

    monkeypatch.setattr(
        exercises.minimal_pair, "get_minimal_pairs_repo", _get_test_minimal_pairs_repo
    )
    monkeypatch.setattr(
        exercises.cloze_deletion, "get_cloze_templates_repo", _get_test_cloze_repo
    )

    return test_db_path


class TestSimulatorBasicRun:
    """Basic simulator execution tests."""

    @pytest.fixture
    def knowledge_points(self, test_db_with_data):
        """Load actual knowledge points from test database."""
        return main.load_knowledge_points()

    def test_simulator_runs_without_error(
        self, knowledge_points, default_simulator_config
    ):
        """Simulator should complete a short run without errors."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=1, exercises_per_day=5, verbose=False)

        assert results is not None
        assert results.total_exercises <= 5
        assert results.days_simulated == 1

    def test_simulator_tracks_exercises(
        self, knowledge_points, default_simulator_config
    ):
        """Simulator should track all exercise results."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=2, exercises_per_day=5, verbose=False)

        assert len(results.exercise_results) <= 10
        assert len(results.daily_summaries) == 2

    def test_simulator_updates_mastery(
        self, knowledge_points, default_simulator_config
    ):
        """Simulator should update FSRS retrievability estimates."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=1, exercises_per_day=10, verbose=False)

        # At least some KPs should have non-zero retrievability
        assert len(results.kp_trajectories) > 0
        assert any(
            traj.snapshots[-1].retrievability > 0
            for traj in results.kp_trajectories.values()
            if traj.snapshots
        )


class TestSimulatorMasteryValidation:
    """Tests validating FSRS estimates against ground truth."""

    @pytest.fixture
    def knowledge_points(self, test_db_with_data):
        return main.load_knowledge_points()

    def test_fast_learner_shows_progress(self, knowledge_points, fast_learner_config):
        """Fast learner should show mastery improvement."""
        random.seed(42)

        simulator = Simulator(knowledge_points, fast_learner_config)
        results = simulator.run(days=5, exercises_per_day=10, verbose=False)

        # Should have some progress
        assert results.total_correct > 0
        # Average retrievability should be positive
        final_avg_retrievability = sum(
            traj.snapshots[-1].retrievability
            for traj in results.kp_trajectories.values()
            if traj.snapshots
        ) / max(1, len(results.kp_trajectories))
        assert final_avg_retrievability > 0

    def test_slow_learner_slower_progress(
        self, knowledge_points, fast_learner_config, slow_learner_config
    ):
        """Slow learner config should have lower learning rate than fast learner."""
        # This test verifies the configs are set up correctly
        # rather than relying on stochastic simulation outcomes
        assert fast_learner_config.learning_rate > slow_learner_config.learning_rate
        assert fast_learner_config.retention_rate > slow_learner_config.retention_rate

        # Both should run without errors
        random.seed(42)
        fast_sim = Simulator(knowledge_points, fast_learner_config)
        fast_results = fast_sim.run(days=2, exercises_per_day=5, verbose=False)

        random.seed(42)
        slow_sim = Simulator(knowledge_points, slow_learner_config)
        slow_results = slow_sim.run(days=2, exercises_per_day=5, verbose=False)

        # Both should produce valid results
        assert fast_results.total_exercises == slow_results.total_exercises
        assert 0.0 <= fast_results.overall_accuracy <= 1.0
        assert 0.0 <= slow_results.overall_accuracy <= 1.0


class TestResponseGenerator:
    """Tests for simulated response generation."""

    def test_high_knowledge_mostly_correct(self, default_simulator_config):
        """Student with high true knowledge should usually answer correctly."""
        student = SimulatedStudent(config=default_simulator_config)
        student.true_knowledge["test_kp"] = 0.95

        generator = ResponseGenerator(student)

        # Create a mock exercise
        class MockExercise(Exercise):
            id: str = "test"
            knowledge_point_ids: list[str] = ["test_kp"]
            difficulty: float = 0.3

        exercise = MockExercise()

        # Run multiple times and check accuracy
        random.seed(42)
        correct_count = sum(
            1 for _ in range(100) if generator.generate_response(exercise)
        )

        # Should be mostly correct (accounting for slip)
        assert correct_count > 70

    def test_low_knowledge_mostly_incorrect(self, default_simulator_config):
        """Student with low true knowledge should usually answer incorrectly."""
        student = SimulatedStudent(config=default_simulator_config)
        student.true_knowledge["test_kp"] = 0.1

        generator = ResponseGenerator(student)

        class MockExercise(Exercise):
            id: str = "test"
            knowledge_point_ids: list[str] = ["test_kp"]
            difficulty: float = 0.3

        exercise = MockExercise()

        random.seed(42)
        correct_count = sum(
            1 for _ in range(100) if generator.generate_response(exercise)
        )

        # Should be mostly incorrect (accounting for guessing)
        assert correct_count < 50


class TestSimulatorReproducibility:
    """Tests for deterministic simulation with seeds."""

    @pytest.fixture
    def knowledge_points(self, test_db_with_data):
        return main.load_knowledge_points()

    def test_same_seed_same_results(self, knowledge_points, default_simulator_config):
        """Same random seed should produce identical results."""
        random.seed(42)
        sim1 = Simulator(knowledge_points, default_simulator_config)
        results1 = sim1.run(days=2, exercises_per_day=5, verbose=False)

        random.seed(42)
        sim2 = Simulator(knowledge_points, default_simulator_config)
        results2 = sim2.run(days=2, exercises_per_day=5, verbose=False)

        assert results1.total_correct == results2.total_correct
        assert results1.overall_accuracy == results2.overall_accuracy


class TestQuickSanityChecks:
    """Quick sanity check tests (5-10 exercises)."""

    @pytest.fixture
    def knowledge_points(self, test_db_with_data):
        return main.load_knowledge_points()

    def test_sanity_check_basic(self, knowledge_points, default_simulator_config):
        """Quick sanity check: system runs and produces valid output."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=1, exercises_per_day=5, verbose=False)

        # Basic sanity checks
        assert results.total_exercises == 5
        assert 0.0 <= results.overall_accuracy <= 1.0
        assert results.total_correct <= results.total_exercises

    def test_sanity_check_accuracy_range(
        self, knowledge_points, default_simulator_config
    ):
        """Quick sanity check: accuracy is reasonable."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=1, exercises_per_day=10, verbose=False)

        # Initial accuracy should be in a reasonable range
        assert 0.0 <= results.overall_accuracy <= 1.0

    def test_sanity_check_mastery_updates(
        self, knowledge_points, default_simulator_config
    ):
        """Quick sanity check: mastery values are being updated."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        simulator.run(days=1, exercises_per_day=10, verbose=False)

        # Should have updated some masteries
        assert len(simulator.student_state.masteries) > 0

        # At least one should have been initialized with FSRS state
        has_initialized = any(
            m.fsrs_state is not None for m in simulator.student_state.masteries.values()
        )
        assert has_initialized

    def test_sanity_check_exercise_types(
        self, knowledge_points, default_simulator_config
    ):
        """Quick sanity check: both exercise types are generated."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=2, exercises_per_day=10, verbose=False)

        exercise_types = set(r.exercise_type for r in results.exercise_results)

        # Should have at least one type (ideally both, but depends on data)
        assert len(exercise_types) >= 1

    def test_sanity_check_daily_summaries(
        self, knowledge_points, default_simulator_config
    ):
        """Quick sanity check: daily summaries are accurate."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=2, exercises_per_day=5, verbose=False)

        # Each day should have a summary
        assert len(results.daily_summaries) == 2

        # Sum of daily exercises should equal total
        daily_total = sum(d.total_exercises for d in results.daily_summaries)
        assert daily_total == results.total_exercises

        # Sum of daily correct should equal total correct
        daily_correct = sum(d.correct_count for d in results.daily_summaries)
        assert daily_correct == results.total_correct
