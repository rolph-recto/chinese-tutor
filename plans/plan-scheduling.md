# Exercise Scheduling Implementation Plan

This plan implements the scheduling specification in `specs/scheduling-spec.md`. It refactors the existing hybrid BKT/FSRS scheduler to support dual exercise pools (Learning Mode and Retention Mode), blocked vs interleaved practice, and student-driven topic selection.

## Current State Analysis

The existing codebase has:
- **BKT implementation** (`bkt.py`): Updates p_known based on correct/incorrect responses
- **FSRS scheduler** (`fsrs_scheduler.py`): Handles long-term retention scheduling
- **Main scheduler** (`scheduler.py`): Hybrid scoring that transitions items from BKT to FSRS at p_known >= 0.8
- **Models** (`models.py`): KnowledgePoint, StudentMastery, SchedulingMode enum

### Gap Analysis

| Spec Requirement | Current Implementation | Action Needed |
|-----------------|------------------------|---------------|
| Two exercise pools (Learning/Retention) | Single unified pool with mode per-KP | Add pool abstraction, session composition |
| Mastery threshold 0.95 for transition | Threshold is 0.80 | Update threshold constant |
| Permanent transition to Retention | Already permanent | No change needed |
| Blocked Practice (single cluster) | Not implemented | Add tag-based cluster filtering, blocked mode |
| Interleaved Practice (all Learning KPs) | Partially exists (current default) | Formalize as explicit mode |
| Topic Selection Menu | Not implemented | Add menu generation using tags, prerequisite filtering |
| Session composition ratio | Not implemented | Add configurable ratio |
| Multi-skill exercise handling | Not implemented | Add multi-KP update logic |
| FSRS Retrievability ranking | Partially exists | Formalize retrievability-based selection |

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `models.py` | **Modify** | Replace `hsk_level` with `tags`, add PracticeMode enum, SessionState |
| `scheduler.py` | **Modify** | Implement dual pools, blocked/interleaved modes |
| `menu.py` | **Create** | Topic Selection Menu generation and filtering |
| `main.py` | **Modify** | Add menu interaction flow |
| `data/vocabulary.json` | **Modify** | Replace `hsk_level` with `tags` list |
| `data/grammar.json` | **Modify** | Replace `hsk_level` with `tags` list |
| `tests/test_menu.py` | **Create** | Test menu generation logic |
| `tests/test_scheduler.py` | **Modify** | Add tests for new scheduling modes |

## Implementation Steps

### Step 1: Update Data Models (`models.py`)

**Replace `hsk_level` with `tags`:**

The existing `hsk_level: int` field is too narrow. Replace it with a flexible `tags` field that can hold multiple labels including HSK level, cluster membership, and any future categorizations.

```python
class KnowledgePoint(BaseModel):
    id: str
    type: KnowledgePointType
    chinese: str
    pinyin: str
    english: str
    tags: list[str] = Field(default_factory=list)  # e.g., ["hsk1", "pronouns", "basic-verbs"]
    prerequisites: list[str] = Field(default_factory=list)
```

**Tag naming conventions:**
- HSK levels: `hsk1`, `hsk2`, ..., `hsk6`
- Clusters: `cluster:pronouns`, `cluster:basic-verbs`, `cluster:sentence-patterns`, etc.
- Other categories as needed: `grammar`, `vocabulary`, `tones`, etc.

**Add new enums and session state:**

```python
class PracticeMode(str, Enum):
    """Current practice mode within Learning Mode."""
    BLOCKED = "blocked"      # Focused on single cluster
    INTERLEAVED = "interleaved"  # All Learning Mode skills

class SessionState(BaseModel):
    """Tracks the current session's scheduling state."""
    practice_mode: PracticeMode = PracticeMode.INTERLEAVED
    active_cluster_tag: str | None = None  # e.g., "cluster:pronouns" during blocked practice
    learning_retention_ratio: float = 0.7  # 70% learning, 30% retention
    exercises_since_menu: int = 0
```

**Update `StudentMastery`:**
```python
class StudentMastery(BaseModel):
    # ... existing fields ...

    # Pool assignment (derived from p_known threshold)
    @property
    def is_mastered(self) -> bool:
        """Returns True if skill has reached mastery threshold (0.95)."""
        return self.p_known >= 0.95
```

**Update constants:**
```python
MASTERY_THRESHOLD = 0.95  # Changed from 0.80
```

### Step 1b: Update Data Files

**`data/vocabulary.json`** - Replace `hsk_level` with `tags`:

```json
{
  "id": "v001",
  "type": "vocabulary",
  "chinese": "我",
  "pinyin": "wǒ",
  "english": "I, me",
  "tags": ["hsk1", "cluster:pronouns"],
  "prerequisites": []
}
```

**`data/grammar.json`** - Same change:

```json
{
  "id": "g001",
  "type": "grammar",
  "chinese": "Subject + 是 + Noun",
  "pinyin": "shì",
  "english": "Subject is Noun (identity/definition)",
  "tags": ["hsk1", "cluster:sentence-patterns"],
  "prerequisites": ["v005"]
}
```

**Example cluster tags:**
- `cluster:pronouns` - 我, 你, 他, 她
- `cluster:basic-verbs` - 是, 吃, 喝
- `cluster:sentence-patterns` - SVO with 是, negation with 不
- `cluster:question-words` - 吗, 什么, 谁

### Step 2: Create Topic Selection Menu (`menu.py`)

The menu discovers clusters dynamically from tags rather than requiring a separate cluster definition file.

```python
CLUSTER_TAG_PREFIX = "cluster:"

class TopicSelectionMenu:
    """Generates and manages the topic selection menu based on tags."""

    def __init__(
        self,
        knowledge_points: list[KnowledgePoint],
        student_state: StudentState
    ):
        self.knowledge_points = {kp.id: kp for kp in knowledge_points}
        self.student_state = student_state

    def get_all_cluster_tags(self) -> list[str]:
        """Extract all unique cluster tags from knowledge points."""
        cluster_tags = set()
        for kp in self.knowledge_points.values():
            for tag in kp.tags:
                if tag.startswith(CLUSTER_TAG_PREFIX):
                    cluster_tags.add(tag)
        return sorted(cluster_tags)

    def get_kps_for_cluster(self, cluster_tag: str) -> list[KnowledgePoint]:
        """Get all knowledge points with a given cluster tag."""
        return [
            kp for kp in self.knowledge_points.values()
            if cluster_tag in kp.tags
        ]

    def get_eligible_clusters(self) -> list[str]:
        """
        Returns cluster tags eligible for selection.

        A cluster is eligible if:
        1. At least one skill has p_known < 0.95 (unmastered)
        2. All prerequisite skills for KPs in the cluster are mastered
        """
        eligible = []
        for cluster_tag in self.get_all_cluster_tags():
            if self._has_unmastered_skills(cluster_tag) and \
               self._prerequisites_mastered(cluster_tag):
                eligible.append(cluster_tag)
        return eligible

    def _has_unmastered_skills(self, cluster_tag: str) -> bool:
        """Check if cluster has at least one skill with p_known < 0.95."""
        for kp in self.get_kps_for_cluster(cluster_tag):
            mastery = self.student_state.get_mastery(kp.id)
            if mastery.p_known < MASTERY_THRESHOLD:
                return True
        return False

    def _prerequisites_mastered(self, cluster_tag: str) -> bool:
        """Check if all prerequisite KPs for this cluster's skills are mastered."""
        for kp in self.get_kps_for_cluster(cluster_tag):
            for prereq_id in kp.prerequisites:
                prereq_mastery = self.student_state.get_mastery(prereq_id)
                if prereq_mastery.p_known < MASTERY_THRESHOLD:
                    return False
        return True

    def _cluster_fully_mastered(self, cluster_tag: str) -> bool:
        """Check if all skills in cluster have p_known >= 0.95."""
        for kp in self.get_kps_for_cluster(cluster_tag):
            mastery = self.student_state.get_mastery(kp.id)
            if mastery.p_known < MASTERY_THRESHOLD:
                return False
        return True

    def get_cluster_display_name(self, cluster_tag: str) -> str:
        """Convert cluster tag to display name (e.g., 'cluster:pronouns' -> 'Pronouns')."""
        name = cluster_tag.removeprefix(CLUSTER_TAG_PREFIX)
        return name.replace("-", " ").title()

    def display_menu(self) -> None:
        """Print the topic selection menu to stdout."""
        eligible = self.get_eligible_clusters()

        print("\n" + "=" * 60)
        print("TOPIC SELECTION MENU")
        print("=" * 60)

        if not eligible:
            print("No new topics available. Continue with retention practice.")
            return

        for i, cluster_tag in enumerate(eligible, 1):
            name = self.get_cluster_display_name(cluster_tag)
            progress = self._get_cluster_progress(cluster_tag)
            kp_count = len(self.get_kps_for_cluster(cluster_tag))
            print(f"\n{i}. {name}")
            print(f"   {kp_count} skills, {progress:.0%} mastered")

        print("\n" + "-" * 60)

    def _get_cluster_progress(self, cluster_tag: str) -> float:
        """Calculate percentage of skills mastered in cluster."""
        kps = self.get_kps_for_cluster(cluster_tag)
        if not kps:
            return 0.0
        mastered = sum(
            1 for kp in kps
            if self.student_state.get_mastery(kp.id).p_known >= MASTERY_THRESHOLD
        )
        return mastered / len(kps)
```

### Step 3: Refactor Scheduler (`scheduler.py`)

Replace current monolithic scheduler with dual-pool architecture:

```python
class ExerciseScheduler:
    """
    Main scheduler implementing dual-pool (Learning/Retention) architecture.
    """

    def __init__(
        self,
        knowledge_points: list[KnowledgePoint],
        student_state: StudentState,
        session_state: SessionState
    ):
        self.knowledge_points = {kp.id: kp for kp in knowledge_points}
        self.student_state = student_state
        self.session_state = session_state
        self.menu = TopicSelectionMenu(knowledge_points, student_state)

    # =========================================================================
    # Pool Management (Spec Section 1)
    # =========================================================================

    def get_learning_pool(self) -> list[str]:
        """Get KP IDs in Learning Mode (p_known < 0.95)."""
        return [
            kp_id for kp_id, mastery in self.student_state.masteries.items()
            if mastery.p_known < MASTERY_THRESHOLD
        ]

    def get_retention_pool(self) -> list[str]:
        """Get KP IDs in Retention Mode (p_known >= 0.95)."""
        return [
            kp_id for kp_id, mastery in self.student_state.masteries.items()
            if mastery.p_known >= MASTERY_THRESHOLD
        ]

    def check_mastery_transition(self, kp_id: str) -> bool:
        """
        Check if a skill should transition to Retention Mode.
        Returns True if transition occurred.
        """
        mastery = self.student_state.get_mastery(kp_id)
        if mastery and mastery.p_known >= MASTERY_THRESHOLD:
            if mastery.scheduling_mode != SchedulingMode.FSRS:
                # Initialize FSRS state for newly mastered skill
                mastery.scheduling_mode = SchedulingMode.FSRS
                mastery.fsrs_state = initialize_fsrs_state()
                mastery.transitioned_to_fsrs_at = datetime.now()
                return True
        return False

    # =========================================================================
    # Session Composition (Spec Section 1)
    # =========================================================================

    def compose_session_queue(self, session_size: int = 10) -> list[str]:
        """
        Compose exercise queue based on learning/retention ratio.
        """
        learning_pool = self.get_learning_pool()
        retention_pool = self.get_retention_pool()

        # If no learning items, use retention only
        if not learning_pool:
            return self._select_from_retention(session_size)

        # Calculate split based on ratio
        learning_count = int(session_size * self.session_state.learning_retention_ratio)
        retention_count = session_size - learning_count

        queue = []
        queue.extend(self._select_from_learning(learning_count))
        queue.extend(self._select_from_retention(retention_count))

        # Shuffle to interleave learning and retention
        random.shuffle(queue)
        return queue

    # =========================================================================
    # Learning Mode Selection (Spec Section 2)
    # =========================================================================

    def _select_from_learning(self, count: int) -> list[str]:
        """Select KPs from Learning Mode based on current practice mode."""
        if self.session_state.practice_mode == PracticeMode.BLOCKED:
            return self._select_blocked(count)
        else:
            return self._select_interleaved(count)

    def _select_blocked(self, count: int) -> list[str]:
        """
        Blocked Practice: Only select from active cluster tag.
        """
        if not self.session_state.active_cluster_tag:
            return []

        # Get unmastered KPs with the active cluster tag
        eligible = [
            kp_id for kp_id, kp in self.knowledge_points.items()
            if self.session_state.active_cluster_tag in kp.tags
            and self._is_in_learning_mode(kp_id)
        ]

        # Score and select top candidates using BKT-based scoring
        scored = [(kp_id, self._calculate_learning_score(kp_id)) for kp_id in eligible]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [kp_id for kp_id, _ in scored[:count]]

    def _select_interleaved(self, count: int) -> list[str]:
        """
        Interleaved Practice: Select from all Learning Mode skills.
        """
        learning_pool = self.get_learning_pool()

        # Filter to KPs with met prerequisites
        eligible = [
            kp_id for kp_id in learning_pool
            if self._prerequisites_met(kp_id)
        ]

        # Score and select
        scored = [(kp_id, self._calculate_learning_score(kp_id)) for kp_id in eligible]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [kp_id for kp_id, _ in scored[:count]]

    def _calculate_learning_score(self, kp_id: str) -> float:
        """
        Calculate priority score for a Learning Mode KP.
        Combines review urgency, frontier expansion, and interleaving.
        """
        mastery = self.student_state.get_mastery(kp_id)
        kp = self.knowledge_points.get(kp_id)

        if not mastery or not kp:
            return 0.0

        score = 0.0

        # Review urgency (70% weight): prioritize items needing review
        if mastery.p_known > 0 and mastery.p_known < MASTERY_THRESHOLD:
            # Higher score for items that need more practice
            review_urgency = 1.0 - mastery.p_known
            score += 0.7 * review_urgency

        # Frontier expansion (30% weight): introduce new items
        if mastery.practice_count == 0:
            score += 0.3

        # Time decay bonus: prioritize items not practiced recently
        if mastery.last_practiced:
            days_since = (datetime.now() - mastery.last_practiced).days
            score += min(0.1 * days_since, 0.2)

        return score

    def check_blocked_practice_complete(self) -> bool:
        """
        Check if all skills in current blocked cluster have reached threshold.
        If so, transition to interleaved mode and show menu.
        """
        if self.session_state.practice_mode != PracticeMode.BLOCKED:
            return False

        if not self.session_state.active_cluster_tag:
            return False

        # Get all KPs with the active cluster tag
        cluster_kp_ids = [
            kp_id for kp_id, kp in self.knowledge_points.items()
            if self.session_state.active_cluster_tag in kp.tags
        ]

        # Check if all KPs in cluster are mastered
        all_mastered = all(
            self.student_state.get_mastery(kp_id).p_known >= MASTERY_THRESHOLD
            for kp_id in cluster_kp_ids
        )

        if all_mastered:
            self.session_state.practice_mode = PracticeMode.INTERLEAVED
            self.session_state.active_cluster_tag = None
            return True

        return False

    def activate_blocked_practice(self, cluster_tag: str) -> None:
        """Activate blocked practice for a specific cluster tag."""
        self.session_state.practice_mode = PracticeMode.BLOCKED
        self.session_state.active_cluster_tag = cluster_tag

    # =========================================================================
    # Retention Mode Selection (Spec Section 3)
    # =========================================================================

    def _select_from_retention(self, count: int) -> list[str]:
        """
        Select KPs from Retention Mode using FSRS retrievability ranking.
        Prioritizes skills with lowest retrievability (most overdue).
        """
        retention_pool = self.get_retention_pool()

        if not retention_pool:
            return []

        # Calculate retrievability for each item
        scored = []
        for kp_id in retention_pool:
            mastery = self.student_state.get_mastery(kp_id)
            if mastery and mastery.fsrs_state:
                retrievability = calculate_retrievability(mastery.fsrs_state)
                # Lower retrievability = higher priority
                scored.append((kp_id, 1.0 - retrievability))
            else:
                # No FSRS state yet, give medium priority
                scored.append((kp_id, 0.5))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [kp_id for kp_id, _ in scored[:count]]

    # =========================================================================
    # Multi-Skill Exercise Handling (Spec Section 4)
    # =========================================================================

    def update_multi_skill_exercise(
        self,
        kp_ids: list[str],
        is_correct: bool
    ) -> None:
        """
        Update all skills associated with a multi-skill exercise.
        Applies uniform BKT update to all associated skills.
        """
        for kp_id in kp_ids:
            mastery = self.student_state.get_mastery(kp_id)
            if not mastery:
                continue

            if mastery.scheduling_mode == SchedulingMode.BKT:
                # Apply BKT update
                mastery.p_known = update_bkt(mastery, is_correct)
            else:
                # Apply FSRS update (doesn't move back to Learning)
                update_fsrs_review(mastery.fsrs_state, is_correct)

            # Check for mastery transition
            self.check_mastery_transition(kp_id)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _is_in_learning_mode(self, kp_id: str) -> bool:
        """Check if KP is in Learning Mode."""
        mastery = self.student_state.get_mastery(kp_id)
        return mastery is None or mastery.p_known < MASTERY_THRESHOLD

    def _prerequisites_met(self, kp_id: str) -> bool:
        """Check if all prerequisites for a KP are mastered."""
        kp = self.knowledge_points.get(kp_id)
        if not kp:
            return False

        for prereq_id in kp.prerequisites:
            prereq_mastery = self.student_state.get_mastery(prereq_id)
            if not prereq_mastery or prereq_mastery.p_known < MASTERY_THRESHOLD:
                return False

        return True
```

### Step 4: Update Main Interactive Loop (`main.py`)

Add menu interaction and mode management:

```python
def run_interactive():
    # ... existing setup ...

    scheduler = ExerciseScheduler(
        knowledge_points=knowledge_points,
        student_state=student_state,
        session_state=SessionState()
    )

    # Initial menu if starting fresh
    if scheduler.session_state.practice_mode == PracticeMode.INTERLEAVED:
        show_topic_menu_and_select(scheduler)

    while True:
        # Check if blocked practice is complete
        if scheduler.check_blocked_practice_complete():
            print("\nCluster complete! Select your next topic.")
            show_topic_menu_and_select(scheduler)

        # Select next KP
        next_kp_id = scheduler.select_next_knowledge_point()

        if not next_kp_id:
            print("No exercises available.")
            break

        # Generate and present exercise
        exercise = generate_exercise(next_kp_id, knowledge_points)
        is_correct = present_exercise(exercise)

        # Update mastery (handles multi-skill)
        scheduler.update_multi_skill_exercise(
            exercise.knowledge_point_ids,
            is_correct
        )

        # Save state
        save_student_state(student_state)


def show_topic_menu_and_select(scheduler: ExerciseScheduler) -> None:
    """Display menu and handle cluster selection."""
    menu = scheduler.menu
    eligible = menu.get_eligible_clusters()

    if not eligible:
        print("No topics available. Continuing with retention practice.")
        return

    menu.display_menu()

    while True:
        try:
            choice = int(input("\nSelect a topic (number): "))
            if 1 <= choice <= len(eligible):
                selected_tag = eligible[choice - 1]
                scheduler.activate_blocked_practice(selected_tag)
                print(f"\nStarting blocked practice: {menu.get_cluster_display_name(selected_tag)}")
                return
        except ValueError:
            pass
        print("Invalid selection. Please enter a number.")
```

### Step 5: Add Tests

#### `tests/test_menu.py`

```python
def test_get_all_cluster_tags():
    """Should extract unique cluster tags from KP tags."""

def test_get_kps_for_cluster():
    """Should return all KPs with a given cluster tag."""

def test_eligible_clusters_excludes_fully_mastered():
    """Clusters with all skills mastered should not appear."""

def test_eligible_clusters_requires_prerequisites():
    """Clusters with unmet prerequisites should not appear."""

def test_eligible_clusters_includes_partial_progress():
    """Clusters with some mastered skills should appear."""

def test_cluster_display_name():
    """Should convert 'cluster:basic-verbs' to 'Basic Verbs'."""

def test_menu_display_shows_progress():
    """Menu should show mastery progress for each cluster."""
```

#### `tests/test_scheduler.py` (additions)

```python
def test_learning_pool_below_threshold():
    """KPs with p_known < 0.95 should be in learning pool."""

def test_retention_pool_above_threshold():
    """KPs with p_known >= 0.95 should be in retention pool."""

def test_mastery_transition_at_threshold():
    """KPs reaching 0.95 should transition to FSRS."""

def test_blocked_practice_filters_by_tag():
    """Blocked mode should only select KPs with active cluster tag."""

def test_interleaved_selects_all_learning():
    """Interleaved mode should select from all learning KPs."""

def test_blocked_complete_triggers_menu():
    """Completing blocked cluster should trigger menu."""

def test_retention_prioritizes_low_retrievability():
    """Retention selection should prioritize lowest retrievability."""

def test_multi_skill_updates_all_kps():
    """Multi-skill exercise should update all associated KPs."""

def test_session_composition_ratio():
    """Session queue should respect learning/retention ratio."""

def test_empty_learning_uses_retention_only():
    """Empty learning pool should use 100% retention."""
```

#### `tests/test_models.py` (additions)

```python
def test_knowledge_point_tags():
    """KnowledgePoint should accept list of tags."""

def test_knowledge_point_hsk_tag():
    """Should be able to filter KPs by hsk level tag."""
```

## Key Design Decisions

1. **Tags instead of separate cluster model** - Clusters are defined via `cluster:*` tags on KnowledgePoints, avoiding a separate data structure. This is more flexible and allows KPs to belong to multiple clusters.

2. **Dynamic cluster discovery** - The menu discovers available clusters by scanning KP tags at runtime, so adding a new cluster only requires tagging KPs appropriately.

3. **Mastery threshold 0.95** - Per spec, skills transition to Retention Mode at p_known >= 0.95 (higher than current 0.80)

4. **Permanent transition** - Once in Retention Mode, skills never return to Learning Mode, even on incorrect answers (per spec section 3)

5. **Session composition** - Configurable ratio (default 70/30) allows flexibility; falls back to 100% retention when learning pool is empty

6. **Tag-based blocking** - Blocked practice filters by `cluster:*` tag rather than cluster ID, enabling simple KP-to-cluster assignment

7. **FSRS retrievability ranking** - Retention Mode uses FSRS retrievability to prioritize most overdue reviews

8. **Multi-skill uniform update** - All skills in a multi-skill exercise receive the same update direction (spec section 4)

9. **Menu only in Learning Mode** - Topic Selection Menu is restricted to Learning Mode exercises (spec section 5)

## Migration Notes

- Existing data files need `hsk_level` field replaced with `tags` list
- Add `hsk1` (or appropriate level) tag to preserve HSK level information
- Add `cluster:*` tags to define cluster membership
- Existing student state files will need the new `SessionState` fields
- Current mastery threshold (0.80) items between 0.80-0.95 will remain in Learning Mode until they reach 0.95
- No data migration needed for FSRS state - it's already compatible

## Dependencies

No new dependencies required. Uses existing:
- pydantic for models
- fsrs (py-fsrs) for retention scheduling
