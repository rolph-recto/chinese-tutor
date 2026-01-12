import argparse
import random
import signal
import sys
from pathlib import Path

import fsrs
from rich.console import Console

from models import KnowledgePoint, SessionState, StudentState
from storage import get_knowledge_point_repo, get_student_state_repo, DEFAULT_DB_PATH
from scheduler import ExerciseScheduler
from exercises import (
    ExerciseHandler,
    ChineseToEnglishHandler,
    ClozeDeletionHandler,
    EnglishToChineseHandler,
    MinimalPairHandler,
    SegmentedTranslationHandler,
)
from ui import TutorUI

# Registry of exercise handler classes
EXERCISE_HANDLERS: dict[str, type[ExerciseHandler]] = {
    "segmented_translation": SegmentedTranslationHandler,
    "minimal_pair": MinimalPairHandler,
    "chinese_to_english": ChineseToEnglishHandler,
    "english_to_chinese": EnglishToChineseHandler,
    "cloze_deletion": ClozeDeletionHandler,
}


def get_exercise_handler(exercise_type: str) -> type[ExerciseHandler]:
    """Get the exercise handler class for the given type."""
    return EXERCISE_HANDLERS[exercise_type]


def prompt_for_rating(ui: TutorUI) -> fsrs.Rating:
    """Prompt the user to rate the difficulty of recall."""
    return ui.show_rating_prompt()


def generate_exercise_with_fallback(
    exercise_type: str,
    knowledge_points: list[KnowledgePoint],
    target_kp: KnowledgePoint | None = None,
):
    """Generate an exercise of the given type, falling back to segmented_translation if needed.

    Returns a tuple of (exercise_type, handler) where handler is an initialized
    ExerciseHandler instance.
    """
    handler_class = get_exercise_handler(exercise_type)
    exercise = handler_class.generate(knowledge_points, target_kp)

    if exercise is not None:
        # Special handling for SegmentedTranslationHandler which needs knowledge_points
        if exercise_type == "segmented_translation":
            handler = SegmentedTranslationHandler(exercise, knowledge_points)
        else:
            handler = handler_class(exercise)
        return exercise_type, handler

    # Fall back to segmented translation
    exercise = SegmentedTranslationHandler.generate(knowledge_points, target_kp)
    handler = SegmentedTranslationHandler(exercise, knowledge_points)
    return "segmented_translation", handler


DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DEFAULT_DB_PATH


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(description="Chinese Tutor")
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
    """Load all knowledge points from the database."""
    repo = get_knowledge_point_repo(DB_PATH)
    return repo.get_all()


def load_student_state() -> StudentState:
    """Load student state from the database, or create new if empty."""
    repo = get_student_state_repo(DB_PATH)
    return repo.load()


def save_student_state(state: StudentState) -> None:
    """Save student state to the database."""
    repo = get_student_state_repo(DB_PATH)
    repo.save(state)


def handle_quit(ui: TutorUI, student_state: StudentState) -> None:
    """Print quit message, save state, and exit."""
    ui.show_quit_message()
    save_student_state(student_state)
    sys.exit(0)


def create_sigint_handler(ui: TutorUI, student_state: StudentState):
    """Create a SIGINT handler that saves state before exiting."""

    def sigint_handler(signum, frame):
        handle_quit(ui, student_state)

    return sigint_handler


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

    from rich.console import Console

    console = Console()

    console.print("=" * 40, style="bold blue")
    console.print("    Student Simulator", style="bold blue")
    console.print("=" * 40, style="bold blue")
    console.print()

    console.print(
        f"Simulating {args.days} days with {args.exercises_per_day} exercises/day..."
    )
    if args.seed is not None:
        console.print(f"Random seed: {args.seed}")
    console.print()

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
    console = Console()
    ui = TutorUI(console)

    ui.clear_screen()

    knowledge_points = load_knowledge_points()
    student_state = load_student_state()

    if not knowledge_points:
        ui.show_error("No knowledge points found. Check data/ directory.")
        return

    signal.signal(signal.SIGINT, create_sigint_handler(ui, student_state))

    kp_dict = {kp.id: kp for kp in knowledge_points}

    session_state = SessionState()
    scheduler = ExerciseScheduler(
        knowledge_points=knowledge_points,
        student_state=student_state,
        session_state=session_state,
    )

    kp_queue = scheduler.compose_session_queue()

    ui.show_welcome(
        knowledge_point_count=len(knowledge_points),
        due_count=len(kp_queue),
    )

    if len(kp_queue) > 0:
        ui.show_info(f"{len(kp_queue)} knowledge points due.")
    else:
        ui.show_no_items_due()
        return

    ui.create_progress_tracker(len(kp_queue))

    for exercise_index, target_kp_id in enumerate(kp_queue):
        ui.clear_screen()
        target_kp = scheduler.knowledge_points.get(target_kp_id)

        exercise_type = random.choice(
            [
                "segmented_translation",
                "cloze_deletion",
                "minimal_pair",
                "chinese_to_english",
                "english_to_chinese",
            ]
        )

        exercise_type, handler = generate_exercise_with_fallback(
            exercise_type, knowledge_points, target_kp
        )

        options = handler.get_options() if hasattr(handler, "get_options") else []

        # Use ordering mode for segmented translation, choice mode for others
        input_mode = (
            "ordering" if exercise_type == "segmented_translation" else "choice"
        )

        user_input = ui.show_exercise(
            prompt_text=handler.get_prompt_text(),
            options=options,
            exercise_number=exercise_index + 1,
            total_exercises=len(kp_queue),
            input_mode=input_mode,
        )

        if user_input == "quit":
            ui.show_quit_message()
            save_student_state(student_state)
            break

        should_retry, is_correct, correct_answer = (
            handler.process_user_input_with_input(user_input)
        )

        if is_correct is None:
            ui.show_quit_message()
            save_student_state(student_state)
            break

        ui.show_feedback(is_correct, correct_answer, user_input)

        if is_correct:
            rating = prompt_for_rating(ui)
        else:
            rating = fsrs.Rating.Again
            ui.wait_for_continue()

        ui.update_progress(is_correct)

        mastery_updates = []
        for kp_id in handler.exercise.knowledge_point_ids:
            if kp_id not in kp_dict:
                continue
            kp = kp_dict[kp_id]
            mastery = student_state.get_mastery(kp_id, kp.type)

            mastery.process_review(rating)

            retrievability = mastery.retrievability
            due_str = (
                mastery.fsrs_state.due.strftime("%Y-%m-%d %H:%M")
                if mastery.fsrs_state and mastery.fsrs_state.due
                else "N/A"
            )
            ret_pct = retrievability * 100 if retrievability else 0

            mastery_updates.append(
                {
                    "chinese": kp.chinese,
                    "english": kp.english,
                    "retrievability": ret_pct / 100,
                    "due": due_str,
                }
            )

        if mastery_updates:
            ui.show_mastery_updates(mastery_updates)

        save_student_state(student_state)

    tracker = ui.get_progress_tracker()
    if tracker:
        ui.show_session_complete(tracker)


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
