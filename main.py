import json
import random
from pathlib import Path

from models import KnowledgePoint, SchedulingMode, StudentState
from bkt import update_mastery
from scheduler import select_next_knowledge_point, update_practice_stats
from exercises import segmented_translation, minimal_pair

DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = Path(__file__).parent / "student_state.json"


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


def main():
    print("=" * 40)
    print("       Chinese Tutor (HSK1)")
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

    while True:
        # Select next knowledge point to test
        target_kp = select_next_knowledge_point(student_state, knowledge_points)

        # Randomly select exercise type
        exercise_type = random.choice(["segmented_translation", "minimal_pair"])

        # Generate exercise based on type
        if exercise_type == "minimal_pair":
            exercise = minimal_pair.generate_exercise(knowledge_points, target_kp)
            # Fall back to segmented translation if no minimal pairs available
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
            mastery = student_state.get_mastery(kp_id)
            old_p = mastery.p_known
            new_p = update_mastery(mastery, is_correct)
            update_practice_stats(mastery, is_correct)

            # Display mode-specific information
            mode = mastery.scheduling_mode.value.upper()
            if mastery.scheduling_mode == SchedulingMode.FSRS and mastery.fsrs_state:
                due_str = (
                    mastery.fsrs_state.due.strftime("%Y-%m-%d %H:%M")
                    if mastery.fsrs_state.due
                    else "N/A"
                )
                print(
                    f"  {kp.chinese} ({kp.english}): [{mode}] "
                    f"retrievability={new_p*100:.0f}%, due={due_str}"
                )
            else:
                print(
                    f"  {kp.chinese} ({kp.english}): [{mode}] "
                    f"{old_p*100:.0f}% → {new_p*100:.0f}%"
                )

        # Update last KP type for interleaving
        if target_kp:
            student_state.last_kp_type = target_kp.type

        # Save state after each exercise
        save_student_state(student_state)

        print()
        continue_input = input("Continue? (y/n): ").strip().lower()
        if continue_input != "y":
            print("\nGoodbye! Your progress has been saved.")
            break

        print()


if __name__ == "__main__":
    main()
