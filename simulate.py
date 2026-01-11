"""Core simulation logic for the student simulator."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from models import (
    Exercise,
    KnowledgePoint,
    SessionState,
    StudentState,
)
from scheduler import ExerciseScheduler, update_practice_stats
from exercises import segmented_translation, minimal_pair
from simulator_models import (
    SimulatedStudentConfig,
    SimulatedStudent,
    ExerciseResult,
    DailySummary,
    KnowledgePointSnapshot,
    KnowledgePointTrajectory,
    SimulationResults,
)


class ResponseGenerator:
    """Generates simulated student responses based on true knowledge."""

    def __init__(self, student: SimulatedStudent):
        self.student = student

    def generate_response(self, exercise: Exercise) -> bool:
        """
        Generate a response (correct/incorrect) based on:
        1. True knowledge of involved KPs
        2. Exercise difficulty
        3. Slip and guess rates
        """
        kp_ids = exercise.knowledge_point_ids
        if not kp_ids:
            return random.random() < 0.5

        # Average true knowledge across all KPs in exercise
        avg_knowledge = sum(
            self.student.get_true_knowledge(kp_id) for kp_id in kp_ids
        ) / len(kp_ids)

        # Factor in exercise difficulty (higher difficulty = harder)
        # difficulty is 0.0-1.0, where 1.0 is hardest
        difficulty_factor = 1.0 - (exercise.difficulty * 0.3)  # Max 30% reduction

        effective_knowledge = avg_knowledge * difficulty_factor

        # Apply slip/guess model
        # P(correct) = P(knows) * (1 - P(slip)) + P(not knows) * P(guess)
        p_correct = (
            effective_knowledge * (1 - self.student.config.slip_rate)
            + (1 - effective_knowledge) * self.student.config.guess_rate
        )

        return random.random() < p_correct


class Simulator:
    """Runs the student simulation."""

    def __init__(
        self,
        knowledge_points: list[KnowledgePoint],
        config: SimulatedStudentConfig,
    ):
        self.knowledge_points = knowledge_points
        self.kp_dict = {kp.id: kp for kp in knowledge_points}
        self.config = config

        # Initialize fresh state
        self.student = SimulatedStudent(config=config)
        self.student_state = StudentState()
        self.response_generator = ResponseGenerator(self.student)

        # Results tracking
        self.exercise_results: list[ExerciseResult] = []
        self.daily_summaries: list[DailySummary] = []
        self.kp_trajectories: dict[str, KnowledgePointTrajectory] = {}

    def _get_mastery_for_kp(self, kp_id: str):
        """
        Get mastery for a KP, initializing FSRS state if needed.
        """
        kp = self.kp_dict.get(kp_id)
        kp_type = kp.type if kp else None
        return self.student_state.get_mastery(kp_id, kp_type)

    def run(
        self,
        days: int,
        exercises_per_day: int,
        verbose: bool = False,
    ) -> SimulationResults:
        """Run the full simulation."""
        start_time = datetime.now()
        current_time = start_time

        for day in range(1, days + 1):
            self._simulate_day(
                day=day,
                exercises_per_day=exercises_per_day,
                current_time=current_time,
                verbose=verbose,
            )

            # Advance time to next day
            current_time += timedelta(days=1)

            # Apply forgetting to all known KPs
            self._apply_daily_forgetting()

        end_time = datetime.now()

        return self._compile_results(
            start_time=start_time,
            end_time=end_time,
            days=days,
            exercises_per_day=exercises_per_day,
        )

    def _simulate_day(
        self,
        day: int,
        exercises_per_day: int,
        current_time: datetime,
        verbose: bool,
    ) -> DailySummary:
        """Simulate a single day of practice."""
        day_correct = 0
        day_exercises = 0
        seg_trans_count = 0
        seg_trans_correct = 0
        mp_count = 0
        mp_correct = 0
        kps_practiced: set[str] = set()

        session = SessionState(exercises_completed=0)
        scheduler = ExerciseScheduler(
            self.knowledge_points, self.student_state, session
        )
        kp_queue = scheduler.compose_session_queue(exercises_per_day)

        print(f"day {day}, {len(kp_queue)} knowledge points due")

        for ex_num, target_kp_id in enumerate(kp_queue):
            target_kp: KnowledgePoint | None = scheduler.knowledge_points.get(
                target_kp_id
            )
            assert target_kp is not None

            # Generate exercise
            exercise, exercise_type = self._generate_exercise(target_kp)

            if exercise is None:
                continue

            # Record pre-exercise state
            pre_state = self._capture_kp_states(exercise.knowledge_point_ids)

            # Generate simulated response
            is_correct = self.response_generator.generate_response(exercise)

            # Update systems
            post_state = self._process_exercise_result(
                exercise=exercise,
                is_correct=is_correct,
                current_time=current_time,
            )

            # Track results
            kps_practiced.update(exercise.knowledge_point_ids)
            day_exercises += 1

            if is_correct:
                day_correct += 1

            if exercise_type == "segmented_translation":
                seg_trans_count += 1
                if is_correct:
                    seg_trans_correct += 1
            else:
                mp_count += 1
                if is_correct:
                    mp_correct += 1

            # Record exercise result
            self.exercise_results.append(
                ExerciseResult(
                    timestamp=current_time,
                    day=day,
                    exercise_number=ex_num + 1,
                    exercise_type=exercise_type,
                    knowledge_point_ids=exercise.knowledge_point_ids,
                    is_correct=is_correct,
                    true_knowledge_before=pre_state["true"],
                    retrievability_before=pre_state["retrievability"],
                    retrievability_after=post_state["retrievability"],
                )
            )

            # Update KP trajectories
            self._record_kp_snapshots(
                kp_ids=exercise.knowledge_point_ids,
                day=day,
                exercise_number=ex_num,
                current_time=current_time,
            )

            # Update last KP type for interleaving
            self.student_state.last_kp_type = target_kp.type

            if verbose:
                self._print_exercise_result(day, ex_num, target_kp, is_correct)

        # Create daily summary
        summary = DailySummary(
            day=day,
            date=current_time,
            total_exercises=day_exercises,
            correct_count=day_correct,
            accuracy=day_correct / day_exercises if day_exercises > 0 else 0.0,
            segmented_translation_count=seg_trans_count,
            segmented_translation_correct=seg_trans_correct,
            minimal_pair_count=mp_count,
            minimal_pair_correct=mp_correct,
            kps_practiced=list(kps_practiced),
            avg_true_knowledge=self._calc_avg_true_knowledge(),
            avg_retrievability=self._calc_avg_retrievability(),
        )

        self.daily_summaries.append(summary)
        return summary

    def _generate_exercise(
        self, target_kp: KnowledgePoint
    ) -> tuple[Exercise | None, str]:
        """Generate an exercise for the target KP."""
        exercise_type = random.choice(["segmented_translation", "minimal_pair"])

        if exercise_type == "minimal_pair":
            exercise = minimal_pair.generate_exercise(self.knowledge_points, target_kp)
            if exercise is None:
                exercise_type = "segmented_translation"
                exercise = segmented_translation.generate_exercise(
                    self.knowledge_points, target_kp
                )
        else:
            exercise = segmented_translation.generate_exercise(
                self.knowledge_points, target_kp
            )

        return exercise, exercise_type

    def _capture_kp_states(self, kp_ids: list[str]) -> dict:
        """Capture current state of knowledge points."""
        retrievability_states = {}
        for kp_id in kp_ids:
            mastery = self._get_mastery_for_kp(kp_id)
            ret = mastery.retrievability
            retrievability_states[kp_id] = ret if ret is not None else 1.0

        return {
            "true": {kp_id: self.student.get_true_knowledge(kp_id) for kp_id in kp_ids},
            "retrievability": retrievability_states,
        }

    def _process_exercise_result(
        self,
        exercise: Exercise,
        is_correct: bool,
        current_time: datetime,
    ) -> dict:
        """Process exercise result through FSRS and update true knowledge."""
        post_state = {"retrievability": {}, "true": {}}

        for kp_id in exercise.knowledge_point_ids:
            if kp_id not in self.kp_dict:
                continue

            # Update true knowledge (simulated student's internal state)
            self.student.update_true_knowledge(kp_id, is_correct, current_time)

            # Update FSRS (the system's estimate)
            mastery = self._get_mastery_for_kp(kp_id)
            mastery.process_review(is_correct)
            update_practice_stats(mastery, is_correct)

            ret = mastery.retrievability
            post_state["retrievability"][kp_id] = ret if ret is not None else 1.0
            post_state["true"][kp_id] = self.student.get_true_knowledge(kp_id)

        return post_state

    def _apply_daily_forgetting(self) -> None:
        """Apply forgetting curve to all practiced KPs."""
        for kp_id in self.student.true_knowledge:
            self.student.apply_forgetting(kp_id, days_elapsed=1.0)

    def _record_kp_snapshots(
        self,
        kp_ids: list[str],
        day: int,
        exercise_number: int,
        current_time: datetime,
    ) -> None:
        """Record snapshots for knowledge points."""
        for kp_id in kp_ids:
            if kp_id not in self.kp_dict:
                continue

            # Initialize trajectory if needed
            if kp_id not in self.kp_trajectories:
                kp = self.kp_dict[kp_id]
                self.kp_trajectories[kp_id] = KnowledgePointTrajectory(
                    kp_id=kp_id,
                    kp_chinese=kp.chinese,
                    kp_english=kp.english,
                    first_practiced=current_time,
                )

            mastery = self._get_mastery_for_kp(kp_id)

            # Get FSRS state
            fsrs_stability = None
            fsrs_difficulty = None
            if mastery.fsrs_state:
                fsrs_stability = mastery.fsrs_state.stability
                fsrs_difficulty = mastery.fsrs_state.difficulty

            ret = mastery.retrievability
            retrievability = ret if ret is not None else 1.0

            snapshot = KnowledgePointSnapshot(
                timestamp=current_time,
                day=day,
                exercise_number=exercise_number,
                true_knowledge=self.student.get_true_knowledge(kp_id),
                retrievability=retrievability,
                practice_count=mastery.practice_count,
                correct_count=mastery.correct_count,
                fsrs_stability=fsrs_stability,
                fsrs_difficulty=fsrs_difficulty,
            )

            self.kp_trajectories[kp_id].snapshots.append(snapshot)

    def _calc_avg_true_knowledge(self) -> float:
        """Calculate average true knowledge across all practiced KPs."""
        if not self.student.true_knowledge:
            return 0.0
        return sum(self.student.true_knowledge.values()) / len(
            self.student.true_knowledge
        )

    def _calc_avg_retrievability(self) -> float:
        """Calculate average FSRS retrievability across all masteries."""
        if not self.student_state.masteries:
            return 0.0
        total = 0.0
        count = 0
        for m in self.student_state.masteries.values():
            ret = m.retrievability
            if ret is not None:
                total += ret
                count += 1
        return total / count if count > 0 else 0.0

    def _print_exercise_result(
        self,
        day: int,
        ex_num: int,
        target_kp: KnowledgePoint,
        is_correct: bool,
    ) -> None:
        """Print verbose exercise result."""
        status = "correct" if is_correct else "incorrect"
        mastery = self._get_mastery_for_kp(target_kp.id)
        true_k = self.student.get_true_knowledge(target_kp.id)
        ret = mastery.retrievability
        ret_val = ret if ret is not None else 1.0
        print(
            f"  Day {day}, Ex {ex_num}: {target_kp.chinese} ({target_kp.english}) "
            f"- {status} | true={true_k:.2f}, ret={ret_val:.2f}"
        )

    def _compile_results(
        self,
        start_time: datetime,
        end_time: datetime,
        days: int,
        exercises_per_day: int,
    ) -> SimulationResults:
        """Compile all results into final output."""
        total_correct = sum(1 for r in self.exercise_results if r.is_correct)
        total_exercises = len(self.exercise_results)

        # Count practiced KPs
        final_practiced = len(self.kp_trajectories)

        return SimulationResults(
            config=self.config,
            days_simulated=days,
            exercises_per_day=exercises_per_day,
            random_seed=None,  # Will be set by caller if applicable
            start_time=start_time,
            end_time=end_time,
            total_exercises=total_exercises,
            total_correct=total_correct,
            overall_accuracy=total_correct / total_exercises
            if total_exercises > 0
            else 0.0,
            daily_summaries=self.daily_summaries,
            exercise_results=self.exercise_results,
            kp_trajectories=self.kp_trajectories,
            final_kps_practiced=final_practiced,
        )


def print_console_summary(
    results: SimulationResults, kp_dict: dict[str, KnowledgePoint]
) -> None:
    """Print formatted console summary of simulation results."""
    print()
    print("=" * 80)
    print("                        SIMULATION COMPLETE")
    print("=" * 80)
    print()
    print("Configuration:")
    print(f"  Days simulated:     {results.days_simulated}")
    print(f"  Exercises per day:  {results.exercises_per_day}")
    print(f"  Total exercises:    {results.total_exercises}")
    print()
    print("Student Parameters:")
    print(f"  Learning rate:      {results.config.learning_rate:.2f}")
    print(f"  Retention rate:     {results.config.retention_rate:.2f}")
    print(f"  Slip rate:          {results.config.slip_rate:.2f}")
    print(f"  Guess rate:         {results.config.guess_rate:.2f}")
    print()
    print("=" * 80)
    print("                        OVERALL RESULTS")
    print("=" * 80)
    print()
    print(
        f"Total correct:        {results.total_correct} / {results.total_exercises} "
        f"({results.overall_accuracy * 100:.1f}%)"
    )
    print()

    # Exercise type breakdown
    seg_total = sum(d.segmented_translation_count for d in results.daily_summaries)
    seg_correct = sum(d.segmented_translation_correct for d in results.daily_summaries)
    mp_total = sum(d.minimal_pair_count for d in results.daily_summaries)
    mp_correct = sum(d.minimal_pair_correct for d in results.daily_summaries)

    print("By exercise type:")
    if seg_total > 0:
        print(
            f"  Segmented Translation:  {seg_correct} / {seg_total} "
            f"({seg_correct / seg_total * 100:.1f}%)"
        )
    if mp_total > 0:
        print(
            f"  Minimal Pairs:          {mp_correct} / {mp_total} "
            f"({mp_correct / mp_total * 100:.1f}%)"
        )
    print()
    print("Knowledge Points:")
    print(f"  Total KPs practiced:   {results.final_kps_practiced}")
    print()
    print("=" * 80)
    print("                        DAILY BREAKDOWN")
    print("=" * 80)
    print()
    print("Day   Exercises  Correct  Accuracy")
    print("----  ---------  -------  --------")

    for summary in results.daily_summaries:
        print(
            f"{summary.day:4d}  {summary.total_exercises:9d}  "
            f"{summary.correct_count:7d}  {summary.accuracy * 100:7.1f}%"
        )

    print()
    print("=" * 80)
    print("                        RETRIEVABILITY vs TRUE KNOWLEDGE")
    print("=" * 80)
    print()
    print("KP ID   Chinese   True Knowledge   Retrievability   Practices")
    print("------  -------   --------------   --------------   ---------")

    # Sort by practice count descending
    sorted_trajectories = sorted(
        results.kp_trajectories.values(),
        key=lambda t: t.snapshots[-1].practice_count if t.snapshots else 0,
        reverse=True,
    )

    for traj in sorted_trajectories:
        if not traj.snapshots:
            continue
        final = traj.snapshots[-1]
        print(
            f"{traj.kp_id:6s}  {traj.kp_chinese:8s}  {final.true_knowledge:14.2f}   "
            f"{final.retrievability:14.2f}   "
            f"{final.practice_count:9d}"
        )

    print()


def save_json_results(results: SimulationResults, output_path: Path) -> None:
    """Save simulation results to JSON file."""
    # Convert to dict with serializable datetimes
    data = json.loads(results.model_dump_json())

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def run_simulation_and_report(
    knowledge_points: list[KnowledgePoint],
    config: SimulatedStudentConfig,
    days: int,
    exercises_per_day: int,
    output_path: Path,
    verbose: bool = False,
    seed: int | None = None,
) -> SimulationResults:
    """Run simulation and generate all outputs."""
    # Set random seed if provided
    if seed is not None:
        random.seed(seed)

    kp_dict = {kp.id: kp for kp in knowledge_points}

    # Run simulation
    simulator = Simulator(knowledge_points, config)
    results = simulator.run(days, exercises_per_day, verbose)

    # Update seed in results
    results.random_seed = seed

    # Print console summary
    print_console_summary(results, kp_dict)

    # Save JSON results
    save_json_results(results, output_path)
    print(f"Results saved to: {output_path}")

    return results
