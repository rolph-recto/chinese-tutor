from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.style import Style
from rich.align import Align
from rich.columns import Columns
from rich import box
from typing import Optional, List, Dict, Any, Literal

from ui.styles import (
    CHINESE_RED,
    CHINESE_GOLD,
    SUCCESS_GREEN,
    ERROR_RED,
    INFO_BLUE,
    MUTED_GRAY,
    TEXT_WHITE,
    get_retrievability_style,
    get_rating_style,
)


class ExercisePanel:
    """A styled panel for displaying exercise content."""

    def __init__(
        self,
        prompt_text: str,
        options: List[str],
        exercise_number: int = 0,
        total_exercises: int = 0,
        progress_percent: float = 0.0,
        input_mode: Literal["choice", "ordering"] = "choice",
    ):
        self.prompt_text = prompt_text
        self.options = options
        self.exercise_number = exercise_number
        self.total_exercises = total_exercises
        self.progress_percent = progress_percent
        self.input_mode = input_mode

    def render(self) -> Panel:
        content = Text()

        if self.total_exercises > 0:
            progress_bar = self._create_progress_bar()
            content.append(progress_bar, Style(color=MUTED_GRAY))
            content.append("\n")
            content.append(
                f"Exercise {self.exercise_number}/{self.total_exercises}\n",
                Style(color=MUTED_GRAY),
            )

        content.append(self.prompt_text, Style(color=CHINESE_RED, bold=True))
        content.append("\n\n")

        for i, option in enumerate(self.options):
            if self.input_mode == "ordering":
                label = str(i + 1)
            else:
                label = chr(65 + i)
            content.append(f"{label}. ", get_rating_style("hard"))
            content.append(option, Style(color=TEXT_WHITE))
            content.append("\n")

        if self.input_mode == "ordering":
            subtitle = "Enter numbers in order (e.g., 2 1 3) or 'q' to quit"
        else:
            subtitle = "Type A, B, C, or D (or 'q' to quit)"

        return Panel(
            Align.left(content),
            title="Chinese Tutor",
            subtitle=subtitle,
            border_style=CHINESE_RED,
            box=box.HEAVY,
            padding=(1, 2),
        )

    def _create_progress_bar(self) -> str:
        """Create a text-based progress bar."""
        width = 30
        filled = int(width * self.progress_percent / 100)
        remaining = width - filled
        bar = "█" * filled + "░" * remaining
        return f"[{bar}] {self.progress_percent:.0f}%"

    def __rich__(self) -> Panel:
        return self.render()


class FeedbackPanel:
    """A styled panel for displaying exercise feedback."""

    def __init__(
        self,
        is_correct: bool,
        correct_answer: str,
        user_answer: str = "",
        explanation: Optional[str] = None,
    ):
        self.is_correct = is_correct
        self.correct_answer = correct_answer
        self.user_answer = user_answer
        self.explanation = explanation

    def render(self) -> Panel:
        content = Text()

        if self.is_correct:
            content.append("✓ ", Style(color=SUCCESS_GREEN, bold=True))
            content.append("Correct!\n", Style(color=SUCCESS_GREEN, bold=True))
        else:
            content.append("✗ ", Style(color=ERROR_RED, bold=True))
            content.append("Not quite!\n", Style(color=ERROR_RED, bold=True))
            if self.user_answer:
                content.append(
                    f"You answered: {self.user_answer}\n", Style(color=MUTED_GRAY)
                )

        content.append("\n")
        content.append("Correct answer: ", Style(color=MUTED_GRAY))
        content.append(self.correct_answer, Style(color=SUCCESS_GREEN, bold=True))

        if self.explanation:
            content.append("\n\n")
            content.append("Explanation:\n", Style(color=CHINESE_GOLD, bold=True))
            content.append(self.explanation, Style(color=TEXT_WHITE))

        return Panel(
            Align.left(content),
            title="Result",
            border_style=SUCCESS_GREEN if self.is_correct else ERROR_RED,
            box=box.HEAVY,
            padding=(1, 2),
        )

    def __rich__(self) -> Panel:
        return self.render()


class RatingMenu:
    """A styled rating menu for difficulty selection."""

    RATING_OPTIONS = [
        ("1", "Again", "I forgot / got lucky", "again"),
        ("2", "Hard", "Difficult to recall", "hard"),
        ("3", "Good", "Correct with some effort", "good"),
        ("4", "Easy", "Effortless recall", "easy"),
    ]

    def __init__(self):
        self.selected_rating = None

    def render(self) -> Panel:
        content = Text()
        content.append("How easy was that?\n\n", Style(color=CHINESE_RED, bold=True))

        for key, label, description, style_key in self.RATING_OPTIONS:
            content.append(f"[{key}] ", get_rating_style(style_key))
            content.append(f"{label:<6}", get_rating_style(style_key))
            content.append(f" - {description}", Style(color=MUTED_GRAY))
            content.append("\n")

        content.append("\n")
        content.append("Rating: ", Style(color=MUTED_GRAY))

        return Panel(
            Align.left(content),
            title="Difficulty Rating",
            subtitle="Choose 1-4",
            border_style=CHINESE_GOLD,
            box=box.HEAVY,
            padding=(1, 2),
        )

    def __rich__(self) -> Panel:
        return self.render()


class MasteryTable:
    """A styled table showing knowledge point mastery updates."""

    def __init__(self, mastery_data: List[Dict[str, Any]]):
        self.mastery_data = mastery_data

    def render(self) -> Panel:
        table = Table(
            show_header=True,
            header_style=Style(color=CHINESE_RED, bold=True),
            border_style=MUTED_GRAY,
            row_styles=[Style(), Style(dim=True)],
            box=box.HEAVY,
        )

        table.add_column("Chinese", style=Style(color=CHINESE_RED, bold=True))
        table.add_column("English", style=Style(color=TEXT_WHITE))
        table.add_column("Retrievability", justify="center")
        table.add_column("Next Due", style=Style(color=MUTED_GRAY))

        for item in self.mastery_data:
            retrievability = item.get("retrievability", 0)
            retrievability_str = f"{retrievability * 100:.0f}%"
            retrievability_style = get_retrievability_style(retrievability)

            due_date = item.get("due", "N/A")
            if due_date == "N/A":
                due_style = Style(color=MUTED_GRAY)
            else:
                due_style = Style(color=INFO_BLUE)

            table.add_row(
                item.get("chinese", ""),
                item.get("english", ""),
                Text(retrievability_str, style=retrievability_style),
                Text(due_date, style=due_style),
            )

        return Panel(
            Align.center(table),
            title="Mastery Updates",
            border_style=CHINESE_GOLD,
            box=box.HEAVY,
            padding=(1, 1),
        )

    def __rich__(self) -> Panel:
        return self.render()


class WelcomeScreen:
    """Welcome screen with banner and session info."""

    def __init__(
        self,
        knowledge_point_count: int,
        due_count: int
    ):
        self.knowledge_point_count = knowledge_point_count
        self.due_count = due_count

    def render(self) -> Panel:
        banner = Text()
        banner.append(
            "╔═══════════════════════════════════════════╗\n", Style(color=CHINESE_RED)
        )
        banner.append("║             ", Style(color=CHINESE_RED))
        banner.append(
            "中 国 语 言 学 习",
            Style(color=CHINESE_GOLD, bold=True),
        )
        banner.append("             ║\n", Style(color=CHINESE_RED))
        banner.append(
            "║              Chinese Tutor                ║\n", Style(color=CHINESE_RED)
        )
        banner.append(
            "╚═══════════════════════════════════════════╝\n", Style(color=CHINESE_RED)
        )
        banner.append("\n")
        banner.append(
            "Welcome back to your Chinese learning journey!\n\n",
            Style(color=TEXT_WHITE),
        )
        banner.append(
            "Type 'q' at any time to save and quit.\n", Style(color=MUTED_GRAY)
        )

        stats = Table(
            show_header=False,
            border_style=MUTED_GRAY,
            box=box.ROUNDED,
        )
        stats.add_column("Label", justify="center")
        stats.add_column("Value", justify="center")

        stats.add_row(
            Text("Total Items", style=Style(color=MUTED_GRAY)),
            Text(
                str(self.knowledge_point_count),
                style=Style(color=CHINESE_GOLD, bold=True),
            ),
        )
        stats.add_row(
            Text("Due Today", style=Style(color=MUTED_GRAY)),
            Text(str(self.due_count), style=Style(color=CHINESE_GOLD, bold=True)),
        )

        # content = Text()
        # content.append(banner)

        return Panel(
            Columns(
                [Align.center(banner), Align.center(stats)],
                align="center",
                padding=(3, 3),
            ),
            border_style=CHINESE_RED,
            box=box.HEAVY,
            padding=(2, 3),
        )

    def __rich__(self) -> Panel:
        return self.render()


class ProgressTracker:
    """Track and display session progress."""

    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.correct_count = 0
        self.incorrect_count = 0

    def update(self, is_correct: bool):
        self.current += 1
        if is_correct:
            self.correct_count += 1
        else:
            self.incorrect_count += 1

    @property
    def progress_percent(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100

    def render_session_summary(self) -> Panel:
        progress_bar = self._create_progress_bar()

        accuracy = (self.correct_count / self.current * 100) if self.current > 0 else 0

        stats = Table(
            show_header=False,
            border_style=MUTED_GRAY,
            box=box.SIMPLE,
        )
        stats.add_column("Label", style=Style(color=MUTED_GRAY))
        stats.add_column("Value", justify="right")

        stats.add_row("Completed", f"{self.current}/{self.total}")
        stats.add_row(
            "Correct",
            Text(f"{self.correct_count}", style=Style(color=SUCCESS_GREEN)),
        )
        stats.add_row(
            "Incorrect",
            Text(f"{self.incorrect_count}", style=Style(color=ERROR_RED)),
        )
        stats.add_row(
            "Accuracy",
            Text(f"{accuracy:.0f}%", style=Style(color=CHINESE_GOLD, bold=True)),
        )

        content = Text()
        content.append("Session Complete!\n\n", Style(color=CHINESE_RED, bold=True))
        content.append(f"Progress: {progress_bar}\n", Style(color=MUTED_GRAY))
        content.append("\n\n")
        content.append("See you next time! 👋\n", Style(color=MUTED_GRAY))

        return Panel(
            Columns(
                [Align.center(content), Align.center(stats)],
                align="center",
                padding=(0, 1),
            ),
            title="Session Summary",
            border_style=CHINESE_GOLD,
            box=box.HEAVY,
            padding=(2, 3),
        )

    def _create_progress_bar(self) -> str:
        width = 30
        filled = int(width * self.progress_percent / 100)
        remaining = width - filled
        bar = "█" * filled + "░" * remaining
        return f"[{bar}] {self.progress_percent:.0f}%"

    def __rich__(self) -> Panel:
        return self.render_session_summary()


class LoadingIndicator:
    """Animated loading indicator."""

    def __init__(self, message: str = "Loading..."):
        self.message = message
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0

    def render(self) -> Text:
        frame = self.frames[self.current_frame]
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        return Text(
            f"{frame} {self.message}",
            Style(color=CHINESE_GOLD),
        )

    def __rich__(self) -> Text:
        return self.render()
