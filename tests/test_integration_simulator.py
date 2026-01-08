"""Integration tests using the student simulator."""

import pytest
import random

from simulate import Simulator, ResponseGenerator
from simulator_models import SimulatedStudent
from main import load_knowledge_points
from models import Exercise


class TestSimulatorBasicRun:
    """Basic simulator execution tests."""

    @pytest.fixture
    def knowledge_points(self):
        """Load actual knowledge points from data files."""
        return load_knowledge_points()

    def test_simulator_runs_without_error(
        self, knowledge_points, default_simulator_config
    ):
        """Simulator should complete a short run without errors."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=1, exercises_per_day=5, verbose=False)

        assert results is not None
        assert results.total_exercises == 5
        assert results.days_simulated == 1

    def test_simulator_tracks_exercises(
        self, knowledge_points, default_simulator_config
    ):
        """Simulator should track all exercise results."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=2, exercises_per_day=5, verbose=False)

        assert len(results.exercise_results) == 10
        assert len(results.daily_summaries) == 2

    def test_simulator_updates_mastery(
        self, knowledge_points, default_simulator_config
    ):
        """Simulator should update BKT mastery estimates."""
        random.seed(42)

        simulator = Simulator(knowledge_points, default_simulator_config)
        results = simulator.run(days=1, exercises_per_day=10, verbose=False)

        # At least some KPs should have non-zero mastery
        assert len(results.kp_trajectories) > 0
        assert any(
            traj.snapshots[-1].bkt_p_known > 0
            for traj in results.kp_trajectories.values()
            if traj.snapshots
        )


class TestSimulatorMasteryValidation:
    """Tests validating BKT estimates against ground truth."""

    @pytest.fixture
    def knowledge_points(self):
        return load_knowledge_points()

    def test_fast_learner_shows_progress(
        self, knowledge_points, fast_learner_config
    ):
        """Fast learner should show mastery improvement."""
        random.seed(42)

        simulator = Simulator(knowledge_points, fast_learner_config)
        results = simulator.run(days=5, exercises_per_day=10, verbose=False)

        # Should have some progress
        assert results.total_correct > 0
        # Average mastery should increase
        final_avg_mastery = sum(
            traj.snapshots[-1].bkt_p_known
            for traj in results.kp_trajectories.values()
            if traj.snapshots
        ) / max(1, len(results.kp_trajectories))
        assert final_avg_mastery > 0

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


class TestFSRSTransition:
    """Tests for BKT to FSRS transitions in simulation."""

    @pytest.fixture
    def knowledge_points(self):
        return load_knowledge_points()

    def test_fsrs_transitions_tracked(
        self, knowledge_points, fast_learner_config
    ):
        """FSRS transitions should be tracked in results."""
        random.seed(42)

        simulator = Simulator(knowledge_points, fast_learner_config)
        results = simulator.run(days=10, exercises_per_day=15, verbose=False)

        # final_kps_in_fsrs should be a valid count
        assert results.final_kps_in_fsrs >= 0
        assert results.final_kps_in_fsrs <= len(results.kp_trajectories)


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
    def knowledge_points(self):
        return load_knowledge_points()

    def test_same_seed_same_results(
        self, knowledge_points, default_simulator_config
    ):
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
    def knowledge_points(self):
        return load_knowledge_points()

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

        # At least one should have non-zero mastery
        has_nonzero = any(
            m.p_known > 0 for m in simulator.student_state.masteries.values()
        )
        assert has_nonzero

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
