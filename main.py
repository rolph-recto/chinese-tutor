import argparse
import json
import random
from pathlib import Path

from models import KnowledgePoint, SessionState, StudentState
from scheduler import ExerciseScheduler, update_practice_stats
from fsrs_scheduler import (
    initialize_fsrs_for_mastery,
    process_fsrs_review,
    get_fsrs_retrievability,
)
from exercises import (
    segmented_translation,
    minimal_pair,
    chinese_to_english,
    english_to_chinese,
)

EXERCISE_MODULES = {
    "segmented_translation": segmented_translation,
    "minimal_pair": minimal_pair,
    "chinese_to_english": chinese_to_english,
    "english_to_chinese": english_to_chinese,
}


def get_exercise_module(exercise_type: str):
    """Get the exercise module for the given type."""
    return EXERCISE_MODULES[exercise_type]


def generate_exercise_with_fallback(
    exercise_type: str,
    knowledge_points: list[KnowledgePoint],
    target_kp: KnowledgePoint | None = None,
):
    """Generate an exercise of the given type, falling back to segmented_translation if needed."""
    module = get_exercise_module(exercise_type)
    exercise = module.generate_exercise(knowledge_points, target_kp)
    if exercise is not None:
        return exercise_type, exercise
    return "segmented_translation", segmented_translation.generate_exercise(
        knowledge_points, target_kp
    )


DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = Path(__file__).parent / "student_state.json"


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(description="Chinese Tutor - HSK1 Learning System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Simulate subcommand
    sim_parser = subparsers.add_parser("simulate", help="Run student simulation")
    sim_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days to simulate (default: 30)",
    )
    sim_parser.add_argument(
        "--exercises-per-day",
        "-e",
        type=int,
        default=10,
        help="Exercises per day (default: 10)",
    )
    sim_parser.add_argument(
        "--learning-rate",
        "-l",
        type=float,
        default=0.3,
        help="Student learning rate 0.0-1.0 (default: 0.3)",
    )
    sim_parser.add_argument(
        "--retention-rate",
        "-r",
        type=float,
        default=0.85,
        help="Student retention rate 0.0-1.0 (default: 0.85)",
    )
    sim_parser.add_argument(
        "--slip-rate",
        "-s",
        type=float,
        default=0.1,
        help="Error/slip rate 0.0-0.5 (default: 0.1)",
    )
    sim_parser.add_argument(
        "--guess-rate",
        "-g",
        type=float,
        default=0.25,
        help="Guess rate 0.0-0.5 (default: 0.25)",
    )
    sim_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="simulation_results.json",
        help="Output JSON file path (default: simulation_results.json)",
    )
    sim_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed exercise-by-exercise output",
    )
    sim_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    return parser


def load_knowledge_points() -> list[KnowledgePoint]:
    """Load all knowledge points from JSON files."""
    knowledge_points = []

    vocab_file = DATA_DIR / "vocabulary.json"
    if vocab_file.exists():
        with open(vocab_file) as f:
            for item in json.load(f):
                knowledge_points.append(KnowledgePoint(**item))

    grammar_file = DATA_DIR / "grammar.json"
    if grammar_file.exists():
        with open(grammar_file) as f:
            for item in json.load(f):
                knowledge_points.append(KnowledgePoint(**item))

    return knowledge_points


def load_student_state() -> StudentState:
    """Load student state from file, or create new if doesn't exist."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return StudentState.model_validate_json(f.read())
    return StudentState()


def save_student_state(state: StudentState) -> None:
    """Save student state to file."""
    with open(STATE_FILE, "w") as f:
        f.write(state.model_dump_json(indent=2))


def run_simulation(args) -> None:
    """Run the simulation subcommand."""
    from simulate import run_simulation_and_report
    from simulator_models import SimulatedStudentConfig

    config = SimulatedStudentConfig(
        learning_rate=args.learning_rate,
        retention_rate=args.retention_rate,
        slip_rate=args.slip_rate,
        guess_rate=args.guess_rate,
    )

    knowledge_points = load_knowledge_points()

    if not knowledge_points:
        print("Error: No knowledge points found. Check data/ directory.")
        return

    print("=" * 40)
    print("    Student Simulator")
    print("=" * 40)
    print()
    print(f"Simulating {args.days} days with {args.exercises_per_day} exercises/day...")
    if args.seed is not None:
        print(f"Random seed: {args.seed}")
    print()

    run_simulation_and_report(
        knowledge_points=knowledge_points,
        config=config,
        days=args.days,
        exercises_per_day=args.exercises_per_day,
        output_path=Path(args.output),
        verbose=args.verbose,
        seed=args.seed,
    )


def run_interactive() -> None:
    """Run the interactive tutoring session."""
    print("=" * 40)
    print("       Chinese Tutor")
    print("=" * 40)
    print()

    knowledge_points = load_knowledge_points()
    student_state = load_student_state()

    if not knowledge_points:
        print("Error: No knowledge points found. Check data/ directory.")
        return

    print(f"Loaded {len(knowledge_points)} knowledge points.")
    print("Type 'q' to quit at any time.\n")

    kp_dict = {kp.id: kp for kp in knowledge_points}

    # Initialize session state and scheduler
    session_state = SessionState()
    scheduler = ExerciseScheduler(
        knowledge_points=knowledge_points,
        student_state=student_state,
        session_state=session_state,
    )

    kp_queue = scheduler.compose_session_queue()

    if len(kp_queue) > 0:
        print(f"{len(kp_queue)} knowledge points due.")

    else:
        print("No knowledge points due.")

    for target_kp_id in kp_queue:
        target_kp = scheduler.knowledge_points.get(target_kp_id)

        exercise_type = random.choice(
            [
                "segmented_translation",
                "minimal_pair",
                "chinese_to_english",
                "english_to_chinese",
            ]
        )

        exercise_type, exercise = generate_exercise_with_fallback(
            exercise_type, knowledge_points, target_kp
        )

        module = get_exercise_module(exercise_type)
        should_retry, is_correct, correct_answer = module.process_user_input(exercise)

        if is_correct is None:
            print("\nGoodbye! Your progress has been saved.")
            save_student_state(student_state)
            break

        if not should_retry:
            feedback = module.format_feedback(is_correct, correct_answer)
            print(feedback)

        # Update mastery and practice stats for each knowledge point in the exercise
        print("\nMastery updates:")
        for kp_id in exercise.knowledge_point_ids:
            if kp_id not in kp_dict:
                continue
            kp = kp_dict[kp_id]
            mastery = student_state.get_mastery(kp_id, kp.type)

            # Initialize FSRS if needed
            if mastery.fsrs_state is None:
                initialize_fsrs_for_mastery(mastery)

            # Process FSRS review
            process_fsrs_review(mastery, is_correct)
            update_practice_stats(mastery, is_correct)

            # Display FSRS information
            retrievability = get_fsrs_retrievability(mastery)
            due_str = (
                mastery.fsrs_state.due.strftime("%Y-%m-%d %H:%M")
                if mastery.fsrs_state and mastery.fsrs_state.due
                else "N/A"
            )
            ret_pct = retrievability * 100 if retrievability else 0
            print(
                f"  {kp.chinese} ({kp.english}): "
                f"retrievability={ret_pct:.0f}%, due={due_str}"
            )

        # Update last KP type for interleaving
        if target_kp:
            student_state.last_kp_type = target_kp.type

        # Save state after each exercise
        save_student_state(student_state)


def main():
    """Main entry point with CLI routing."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "simulate":
        run_simulation(args)
    else:
        # Default to interactive mode
        run_interactive()


if __name__ == "__main__":
    main()
