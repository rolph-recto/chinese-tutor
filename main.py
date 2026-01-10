import argparse
import json
import random
from pathlib import Path

from models import KnowledgePoint, SessionState, StudentState
from scheduler import ExerciseScheduler, update_practice_stats
from fsrs_scheduler import initialize_fsrs_for_mastery, process_fsrs_review, get_fsrs_retrievability
from exercises import segmented_translation, minimal_pair, chinese_to_english, english_to_chinese

DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = Path(__file__).parent / "student_state.json"


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Chinese Tutor - HSK1 Learning System"
    )
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

    while True:
        # Select next knowledge point to test
        target_kp = scheduler.select_next_knowledge_point()

        if target_kp is None:
            print("No exercises available.")
            break

        # Randomly select exercise type
        exercise_type = random.choice([
            "segmented_translation",
            "minimal_pair",
            "chinese_to_english",
            "english_to_chinese",
        ])

        # Generate exercise based on type
        if exercise_type == "minimal_pair":
            exercise = minimal_pair.generate_exercise(knowledge_points, target_kp)
            # Fall back to segmented translation if no minimal pairs available
            if exercise is None:
                exercise_type = "segmented_translation"
                exercise = segmented_translation.generate_exercise(knowledge_points, target_kp)
        elif exercise_type == "chinese_to_english":
            exercise = chinese_to_english.generate_exercise(knowledge_points, target_kp)
            if exercise is None:
                exercise_type = "segmented_translation"
                exercise = segmented_translation.generate_exercise(knowledge_points, target_kp)
        elif exercise_type == "english_to_chinese":
            exercise = english_to_chinese.generate_exercise(knowledge_points, target_kp)
            if exercise is None:
                exercise_type = "segmented_translation"
                exercise = segmented_translation.generate_exercise(knowledge_points, target_kp)
        else:
            exercise = segmented_translation.generate_exercise(knowledge_points, target_kp)

        # Handle exercise based on type
        if exercise_type == "minimal_pair":
            # Present minimal pair exercise
            options = minimal_pair.present_exercise(exercise)

            # Get user input
            user_input = input("Enter your choice (A/B/C or 1/2/3): ").strip()

            if user_input.lower() == "q":
                print("\nGoodbye! Your progress has been saved.")
                save_student_state(student_state)
                break

            # Check answer
            is_correct, correct_answer = minimal_pair.check_answer(exercise, user_input, options)

            if is_correct:
                print(f"\nCorrect! {correct_answer}")
            else:
                print(f"\nIncorrect. The correct answer is: {correct_answer}")

        elif exercise_type == "chinese_to_english":
            # Present Chinese to English exercise
            chinese_to_english.present_exercise(exercise)

            # Get user input
            user_input = input("Enter your choice (A/B/C/D or 1/2/3/4): ").strip()

            if user_input.lower() == "q":
                print("\nGoodbye! Your progress has been saved.")
                save_student_state(student_state)
                break

            # Check answer
            is_correct, correct_answer = chinese_to_english.check_answer(exercise, user_input)

            if is_correct:
                print(f"\nCorrect! {correct_answer}")
            else:
                print(f"\nIncorrect. The correct answer is: {correct_answer}")

        elif exercise_type == "english_to_chinese":
            # Present English to Chinese exercise
            english_to_chinese.present_exercise(exercise)

            # Get user input
            user_input = input("Enter your choice (A/B/C/D or 1/2/3/4): ").strip()

            if user_input.lower() == "q":
                print("\nGoodbye! Your progress has been saved.")
                save_student_state(student_state)
                break

            # Check answer
            is_correct, correct_answer = english_to_chinese.check_answer(exercise, user_input)

            if is_correct:
                print(f"\nCorrect! {correct_answer}")
            else:
                print(f"\nIncorrect. The correct answer is: {correct_answer}")

        else:
            # Present segmented translation exercise
            shuffled_chunks = segmented_translation.present_exercise(exercise)

            # Get user input
            user_input = input(
                "Enter the numbers in correct order (e.g., 2 1 3): "
            ).strip()

            if user_input.lower() == "q":
                print("\nGoodbye! Your progress has been saved.")
                save_student_state(student_state)
                break

            # Parse user input
            try:
                user_order = [int(x) for x in user_input.split()]
            except ValueError:
                print("Invalid input. Please enter numbers separated by spaces.\n")
                continue

            # Check answer
            is_correct, correct_sentence = segmented_translation.check_answer(
                exercise, user_order, shuffled_chunks
            )

            # Get pinyin for the sentence
            pinyin_parts = []
            for chunk in [exercise.chinese_chunks[i] for i in exercise.correct_order]:
                for kp in knowledge_points:
                    if kp.chinese == chunk:
                        pinyin_parts.append(kp.pinyin)
                        break
                else:
                    pinyin_parts.append("")

            if is_correct:
                print(f"\nCorrect! {correct_sentence} ({' '.join(pinyin_parts)})")
            else:
                print(f"\nIncorrect. The correct answer is: {correct_sentence}")
                print(f"Pinyin: {' '.join(pinyin_parts)}")

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

        print()


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
