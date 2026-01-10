"""English to Chinese multiple choice exercise.

Shows an English word and asks the student to select the correct Chinese translation
from 4 choices (with pinyin shown).
"""

import random
import uuid
from typing import Any

from models import KnowledgePoint, MultipleChoiceVocabExercise


def _select_distractors(
    target_kp: KnowledgePoint,
    all_vocab: list[KnowledgePoint],
    count: int = 3,
) -> list[KnowledgePoint]:
    """
    Select distractor vocabulary items using mixed approach.

    Prefers items from the same cluster as the target, falls back to random.
    """
    distractors = []
    used_ids = {target_kp.id}

    # Get target's cluster tags
    cluster_tags = [t for t in target_kp.tags if t.startswith("cluster:")]

    # First pass: same cluster
    if cluster_tags:
        same_cluster = [
            kp
            for kp in all_vocab
            if kp.id not in used_ids and any(t in kp.tags for t in cluster_tags)
        ]
        random.shuffle(same_cluster)
        for kp in same_cluster[:count]:
            distractors.append(kp)
            used_ids.add(kp.id)

    # Second pass: fill with random
    remaining = count - len(distractors)
    if remaining > 0:
        other_vocab = [kp for kp in all_vocab if kp.id not in used_ids]
        random.shuffle(other_vocab)
        distractors.extend(other_vocab[:remaining])

    return distractors


def generate_exercise(
    knowledge_points: list[KnowledgePoint],
    target_kp: KnowledgePoint | None = None,
) -> MultipleChoiceVocabExercise | None:
    """
    Generate an English to Chinese multiple choice exercise.

    If target_kp is provided, uses that knowledge point as the target.
    Returns None if there aren't enough vocabulary items (need at least 4).
    """
    # Filter to vocabulary knowledge points only
    vocab_kps = [kp for kp in knowledge_points if kp.type.value == "vocabulary"]

    if len(vocab_kps) < 4:
        return None

    # Select target (use provided or random)
    if target_kp and target_kp.type.value == "vocabulary":
        selected_kp = target_kp
    else:
        selected_kp = random.choice(vocab_kps)

    # Get distractors
    distractors = _select_distractors(selected_kp, vocab_kps, count=3)

    if len(distractors) < 3:
        return None

    # Build options: Chinese with pinyin for each option
    # Format: "中文 (pīnyīn)"
    correct_option = f"{selected_kp.chinese} ({selected_kp.pinyin})"
    distractor_options = [f"{d.chinese} ({d.pinyin})" for d in distractors]

    all_options = [correct_option] + distractor_options
    random.shuffle(all_options)

    # Find correct index after shuffling
    correct_index = all_options.index(correct_option)

    # Use first English translation if multiple provided
    prompt_english = selected_kp.english.split(",")[0].strip()

    return MultipleChoiceVocabExercise(
        id=str(uuid.uuid4()),
        knowledge_point_ids=[selected_kp.id],
        difficulty=0.4,
        direction="english_to_chinese",
        prompt=prompt_english,
        prompt_pinyin="",  # Not shown for English prompts
        options=all_options,
        correct_index=correct_index,
    )


def present_exercise(exercise: MultipleChoiceVocabExercise) -> list[str]:
    """
    Present the exercise to the user.

    Returns the options list for answer checking.
    """
    print(f'\nWhat is the Chinese for "{exercise.prompt}"?')
    print()

    labels = ["A", "B", "C", "D"]
    for i, option in enumerate(exercise.options):
        label = labels[i] if i < len(labels) else str(i + 1)
        print(f"  {label}. {option}")
    print()

    return exercise.options


def check_answer(
    exercise: MultipleChoiceVocabExercise,
    user_input: str,
    options: Any = None,
) -> tuple[bool, str]:
    """
    Check if the user's answer is correct.

    user_input: letter (A/B/C/D) or number (1/2/3/4)
    options: unused, kept for interface consistency

    Returns (is_correct, correct_answer_display)
    """
    user_input = user_input.strip().upper()

    # Map letters to indices
    letter_map = {"A": 0, "B": 1, "C": 2, "D": 3}

    if user_input in letter_map:
        user_index = letter_map[user_input]
    elif user_input.isdigit():
        user_index = int(user_input) - 1
    else:
        # Invalid input
        correct_answer = exercise.options[exercise.correct_index]
        return False, correct_answer

    # Check bounds
    if user_index < 0 or user_index >= len(exercise.options):
        correct_answer = exercise.options[exercise.correct_index]
        return False, correct_answer

    is_correct = user_index == exercise.correct_index
    correct_answer = exercise.options[exercise.correct_index]

    return is_correct, correct_answer


def process_user_input(
    exercise: MultipleChoiceVocabExercise,
) -> tuple[bool, bool | None, str]:
    """
    Process user input for an English to Chinese exercise.

    Returns (should_retry, is_correct_or_None, correct_answer_display):
    - should_retry: True if invalid input, user should retry same exercise
    - is_correct_or_None: True if correct, False if incorrect, None if quit
    - correct_answer_display: String to show the correct answer
    """
    present_exercise(exercise)

    user_input = input("Enter your choice (A/B/C/D or 1/2/3/4): ").strip()

    if user_input.lower() == "q":
        return False, None, ""

    is_correct, correct_answer_display = check_answer(exercise, user_input)

    return False, is_correct, correct_answer_display


def format_feedback(is_correct: bool, correct_answer: str) -> str:
    """Return formatted feedback string for an English to Chinese exercise."""
    if is_correct:
        return f"\nCorrect! {correct_answer}"
    else:
        return f"\nIncorrect. The correct answer is: {correct_answer}"
