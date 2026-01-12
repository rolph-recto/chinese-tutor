"""Shared utilities for exercise handling."""

import random

from models import KnowledgePoint


def parse_letter_input(user_input: str, max_options: int = 4) -> int | None:
    """Parse letter (A-F) or number (1-6) input to 0-based index.

    Args:
        user_input: Raw user input string.
        max_options: Maximum number of valid options.

    Returns:
        0-based index or None if input is invalid or out of bounds.
    """
    user_input = user_input.strip().upper()
    letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    if user_input in letter_map:
        index = letter_map[user_input]
    elif user_input.isdigit():
        index = int(user_input) - 1
    else:
        return None

    if index < 0 or index >= max_options:
        return None

    return index


def select_distractors(
    target_kp: KnowledgePoint,
    all_vocab: list[KnowledgePoint],
    count: int = 3,
) -> list[KnowledgePoint]:
    """Select distractor vocabulary items using mixed approach.

    Prefers items from the same cluster as the target, falls back to random.

    Args:
        target_kp: The target knowledge point to find distractors for.
        all_vocab: All available vocabulary knowledge points.
        count: Number of distractors to select.

    Returns:
        List of distractor knowledge points.
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
