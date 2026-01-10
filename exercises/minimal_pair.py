import json
import random
import uuid
from pathlib import Path

from models import KnowledgePoint, MinimalPairExercise, MinimalPairOption

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_minimal_pairs() -> dict[str, list[dict]]:
    """Load minimal pairs data and return a dict mapping target_id to distractors."""
    pairs_file = DATA_DIR / "minimal_pairs.json"
    if not pairs_file.exists():
        return {}

    with open(pairs_file) as f:
        pairs_list = json.load(f)

    return {item["target_id"]: item["distractors"] for item in pairs_list}


def generate_exercise(
    knowledge_points: list[KnowledgePoint], target_kp: KnowledgePoint | None = None
) -> MinimalPairExercise | None:
    """
    Generate a minimal pair exercise.

    If target_kp is provided, tries to generate an exercise for that knowledge point.
    Returns None if no minimal pairs are available for the selected vocabulary.
    """
    minimal_pairs = _load_minimal_pairs()

    if not minimal_pairs:
        return None

    # Get vocabulary knowledge points that have minimal pairs defined
    vocab_kps = [
        kp
        for kp in knowledge_points
        if kp.type.value == "vocabulary" and kp.id in minimal_pairs
    ]

    if not vocab_kps:
        return None

    # Select target (prefer target_kp if it has minimal pairs)
    if target_kp and target_kp.id in minimal_pairs:
        selected_kp = target_kp
    else:
        selected_kp = random.choice(vocab_kps)

    distractors = minimal_pairs[selected_kp.id]

    # Build options: correct answer + distractors
    correct_option = MinimalPairOption(
        chinese=selected_kp.chinese,
        pinyin=selected_kp.pinyin,
        english=selected_kp.english.split(",")[0].strip(),
    )

    distractor_options = [
        MinimalPairOption(
            chinese=d["chinese"], pinyin=d["pinyin"], english=d["english"]
        )
        for d in distractors
    ]

    # Combine and shuffle options
    all_options = [correct_option] + distractor_options
    random.shuffle(all_options)

    # Find the correct index after shuffling
    correct_index = next(
        i for i, opt in enumerate(all_options) if opt.chinese == selected_kp.chinese
    )

    return MinimalPairExercise(
        id=str(uuid.uuid4()),
        knowledge_point_ids=[selected_kp.id],
        difficulty=0.4,
        target_chinese=selected_kp.chinese,
        target_pinyin=selected_kp.pinyin,
        target_english=selected_kp.english.split(",")[0].strip(),
        options=all_options,
        correct_index=correct_index,
    )


def present_exercise(exercise: MinimalPairExercise) -> list[MinimalPairOption]:
    """
    Present the exercise to the user.

    Returns the options list for answer checking.
    """
    print(
        f'\nSelect the character for "{exercise.target_english}" ({exercise.target_pinyin})'
    )
    print()

    labels = ["A", "B", "C", "D", "E", "F"]
    for i, option in enumerate(exercise.options):
        label = labels[i] if i < len(labels) else str(i + 1)
        print(f"  {label}. {option.chinese}")
    print()

    return exercise.options


def check_answer(
    exercise: MinimalPairExercise,
    user_input: str,
    options: list[MinimalPairOption],
) -> tuple[bool, str]:
    """
    Check if the user's answer is correct.

    user_input: letter (A/B/C/D) or number (1/2/3/4)
    options: the options as presented to the user

    Returns (is_correct, correct_answer_display)
    """
    # Parse user input
    user_input = user_input.strip().upper()

    # Map letters to indices
    letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    if user_input in letter_map:
        user_index = letter_map[user_input]
    elif user_input.isdigit():
        user_index = int(user_input) - 1
    else:
        # Invalid input
        correct_opt = options[exercise.correct_index]
        return False, f"{correct_opt.chinese} ({correct_opt.pinyin})"

    # Check bounds
    if user_index < 0 or user_index >= len(options):
        correct_opt = options[exercise.correct_index]
        return False, f"{correct_opt.chinese} ({correct_opt.pinyin})"

    is_correct = user_index == exercise.correct_index
    correct_opt = options[exercise.correct_index]
    correct_display = f"{correct_opt.chinese} ({correct_opt.pinyin})"

    return is_correct, correct_display


def process_user_input(exercise: MinimalPairExercise) -> tuple[bool, bool | None, str]:
    """
    Process user input for a minimal pair exercise.

    Returns (should_retry, is_correct_or_None, correct_answer_display):
    - should_retry: True if invalid input, user should retry same exercise
    - is_correct_or_None: True if correct, False if incorrect, None if quit
    - correct_answer_display: String to show the correct answer
    """
    present_exercise(exercise)

    user_input = input("Enter your choice (A/B/C or 1/2/3): ").strip()

    if user_input.lower() == "q":
        return False, None, ""

    is_correct, correct_answer_display = check_answer(
        exercise, user_input, exercise.options
    )

    return False, is_correct, correct_answer_display


def format_feedback(is_correct: bool, correct_answer: str) -> str:
    """Return formatted feedback string for a minimal pair exercise."""
    if is_correct:
        return f"\nCorrect! {correct_answer}"
    else:
        return f"\nIncorrect. The correct answer is: {correct_answer}"
