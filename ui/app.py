from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from ui.components import (
    ExercisePanel,
    FeedbackPanel,
    RatingMenu,
    MasteryTable,
    WelcomeScreen,
    ProgressTracker,
)
from ui.styles import (
    SUCCESS_GREEN,
    ERROR_RED,
    INFO_BLUE,
    MUTED_GRAY,
)
from typing import Optional, List, Dict, Any, Literal
from fsrs import Rating


class TutorUI:
    """Main UI orchestrator for the Chinese Tutor application."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._progress_tracker: Optional[ProgressTracker] = None

    def show_welcome(
        self,
        knowledge_point_count: int,
        due_count: int,
        streak: int = 0,
    ) -> None:
        """Display the welcome screen and wait for user to press Enter."""
        welcome = WelcomeScreen(
            knowledge_point_count=knowledge_point_count,
            due_count=due_count,
            streak=streak,
        )
        self.console.print(welcome)
        self.console.print()
        self.console.input(Text("Press Enter to start...", style=f"bold {MUTED_GRAY}"))

    def show_session_complete(self, tracker: ProgressTracker) -> None:
        """Display session completion summary."""
        self.console.print(tracker.render_session_summary())

    def show_exercise(
        self,
        prompt_text: str,
        options: List[str],
        exercise_number: int,
        total_exercises: int,
        input_mode: Literal["choice", "ordering"] = "choice",
    ) -> str:
        """Display an exercise and get user input.

        Args:
            prompt_text: The exercise prompt to display.
            options: List of options to display.
            exercise_number: Current exercise number (1-indexed).
            total_exercises: Total number of exercises in session.
            input_mode: "choice" for A/B/C/D selection, "ordering" for number sequence.

        Returns:
            "quit" if user quits, otherwise the user's answer.
        """
        progress_percent = (
            (exercise_number / total_exercises * 100) if total_exercises > 0 else 0
        )

        panel = ExercisePanel(
            prompt_text=prompt_text,
            options=options,
            exercise_number=exercise_number,
            total_exercises=total_exercises,
            progress_percent=progress_percent,
            input_mode=input_mode,
        )

        self.console.print(panel)
        self.console.print()

        if input_mode == "ordering":
            return self._get_ordering_input(len(options))
        else:
            return self._get_choice_input()

    def _get_choice_input(self) -> str:
        """Get A/B/C/D choice input from user."""
        while True:
            user_input = self.console.input(
                Text("Your answer: ", style=f"bold {MUTED_GRAY}")
            ).strip()

            if user_input.lower() == "q":
                return "quit"

            if user_input.upper() in ["A", "B", "C", "D"]:
                return user_input.upper()

            self.console.print(
                Text("Please enter A, B, C, or D (or 'q' to quit)\n", style=ERROR_RED)
            )

    def _get_ordering_input(self, num_options: int) -> str:
        """Get number sequence input from user for ordering exercises."""
        while True:
            user_input = self.console.input(
                Text("Your answer: ", style=f"bold {MUTED_GRAY}")
            ).strip()

            if user_input.lower() == "q":
                return "quit"

            # Validate number sequence
            try:
                numbers = [int(x) for x in user_input.split()]
                if all(1 <= n <= num_options for n in numbers):
                    return user_input
            except ValueError:
                pass

            self.console.print(
                Text(
                    f"Please enter numbers 1-{num_options} separated by spaces (or 'q' to quit)\n",
                    style=ERROR_RED,
                )
            )

    def show_feedback(
        self,
        is_correct: bool,
        correct_answer: str,
        user_answer: str = "",
        explanation: Optional[str] = None,
    ) -> None:
        """Display feedback for the user's answer."""
        feedback = FeedbackPanel(
            is_correct=is_correct,
            correct_answer=correct_answer,
            user_answer=user_answer,
            explanation=explanation,
        )
        self.console.print(feedback)
        self.console.print()

    def show_rating_prompt(self) -> Rating:
        """Display the rating menu and get user selection."""
        rating_menu = RatingMenu()
        self.console.print(rating_menu)
        self.console.print()

        rating_map = {
            "1": Rating.Again,
            "2": Rating.Hard,
            "3": Rating.Good,
            "4": Rating.Easy,
        }

        while True:
            user_input = self.console.input(
                Text("Rating: ", style=f"bold {MUTED_GRAY}")
            ).strip()

            if user_input in rating_map:
                return rating_map[user_input]

            self.console.print(Text("Please enter 1, 2, 3, or 4\n", style=ERROR_RED))

    def show_mastery_updates(self, mastery_data: List[Dict[str, Any]]) -> None:
        """Display mastery update information."""
        if not mastery_data:
            return

        table = MasteryTable(mastery_data)
        self.console.print(table)
        self.console.print()

    def show_progress(self, current: int, total: int) -> None:
        """Show current progress (lightweight inline display)."""
        progress_percent = (current / total * 100) if total > 0 else 0
        bar_width = 20
        filled = int(bar_width * progress_percent / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        self.console.print(
            f"\rProgress: [{bar}] {progress_percent:.0f}% ({current}/{total})",
            end="",
            highlight=False,
        )

    def clear_progress_line(self) -> None:
        """Clear the progress line from the terminal."""
        self.console.print("\r" + " " * 50, end="")

    def show_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(
            Panel(
                Text(f"Error: {message}", style=ERROR_RED),
                title="Error",
                border_style=ERROR_RED,
            )
        )

    def show_info(self, message: str) -> None:
        """Display an informational message."""
        self.console.print(Text(message, style=INFO_BLUE))

    def show_success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(Text(message, style=SUCCESS_GREEN))

    def show_quit_message(self) -> None:
        """Display the quit message."""
        self.console.print()
        self.console.print(
            Text("👋 Goodbye! Your progress has been saved.", style=MUTED_GRAY)
        )

    def show_no_items_due(self) -> None:
        """Display message when no items are due."""
        self.console.print(
            Panel(
                Text(
                    "🎉 You're all caught up!\n\nNo knowledge points are due for review right now. "
                    "Great job keeping up with your studies!",
                    style=SUCCESS_GREEN,
                ),
                title="All Done",
                border_style=SUCCESS_GREEN,
            )
        )

    def create_progress_tracker(self, total: int) -> ProgressTracker:
        """Create a new progress tracker for a session."""
        self._progress_tracker = ProgressTracker(total)
        return self._progress_tracker

    def update_progress(self, is_correct: bool) -> None:
        """Update the progress tracker with a new result."""
        if self._progress_tracker:
            self._progress_tracker.update(is_correct)

    def get_progress_tracker(self) -> Optional[ProgressTracker]:
        """Get the current progress tracker."""
        return self._progress_tracker

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        self.console.clear()

    def wait_for_continue(self) -> None:
        """Wait for user to press Enter to continue."""
        self.console.input(
            Text("Press Enter to continue...", style=f"bold {MUTED_GRAY}")
        )
