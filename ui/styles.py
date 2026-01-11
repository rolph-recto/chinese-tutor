from rich.theme import Theme
from rich.console import Console
from rich.style import Style
from rich.text import Text

CHINESE_RED = "#E74C3C"
CHINESE_GOLD = "#F1C40F"
SUCCESS_GREEN = "#27AE60"
ERROR_RED = "#C0392B"
INFO_BLUE = "#3498DB"
MUTED_GRAY = "#7F8C8D"
TEXT_WHITE = "#FFFFFF"

DEFAULT_THEME = Theme(
    {
        "primary": Style(color=CHINESE_RED, bold=True),
        "secondary": Style(color=CHINESE_GOLD, bold=True),
        "success": Style(color=SUCCESS_GREEN),
        "error": Style(color=ERROR_RED, bold=True),
        "info": Style(color=INFO_BLUE),
        "muted": Style(color=MUTED_GRAY),
        "chinese": Style(color=CHINESE_RED, bold=True),
        "option_label": Style(color=CHINESE_GOLD, bold=True),
        "option_text": Style(color=TEXT_WHITE),
        "progress_bar": Style(color=SUCCESS_GREEN),
        "progress_complete": Style(color=SUCCESS_GREEN, bold=True),
        "progress_remaining": Style(color=MUTED_GRAY),
        "retrievability_high": Style(color=SUCCESS_GREEN, bold=True),
        "retrievability_medium": Style(color=CHINESE_GOLD),
        "retrievability_low": Style(color=ERROR_RED),
        "title": Style(color=CHINESE_RED, bold=True),
        "subtitle": Style(color=MUTED_GRAY),
        "rating_again": Style(color=ERROR_RED, bold=True),
        "rating_hard": Style(color=CHINESE_GOLD, bold=True),
        "rating_good": Style(color=SUCCESS_GREEN, bold=True),
        "rating_easy": Style(color=INFO_BLUE, bold=True),
    }
)

CONSOLE = Console(theme=DEFAULT_THEME)


def get_retrievability_style(retrievability: float) -> Style:
    """Get color style based on retrievability percentage."""
    if retrievability >= 0.8:
        return Style(color=SUCCESS_GREEN, bold=True)
    elif retrievability >= 0.5:
        return Style(color=CHINESE_GOLD)
    else:
        return Style(color=ERROR_RED)


def get_rating_style(rating: str) -> Style:
    """Get style for rating option."""
    styles = {
        "again": Style(color=ERROR_RED, bold=True),
        "hard": Style(color=CHINESE_GOLD, bold=True),
        "good": Style(color=SUCCESS_GREEN, bold=True),
        "easy": Style(color=INFO_BLUE, bold=True),
    }
    return styles.get(rating.lower(), Style())


def create_welcome_banner() -> Text:
    """Create the welcome banner text."""
    banner = Text()
    banner.append(
        "╔══════════════════════════════════════╗\n", Style(color=CHINESE_RED)
    )
    banner.append(
        "║       中 国 语 言 学 习         ║\n", Style(color=CHINESE_GOLD, bold=True)
    )
    banner.append("║       Chinese Tutor               ║\n", Style(color=CHINESE_RED))
    banner.append("╚══════════════════════════════════════╝", Style(color=CHINESE_RED))
    return banner


def create_success_header() -> Text:
    """Create a success/correct answer header."""
    header = Text()
    header.append("✓ ", Style(color=SUCCESS_GREEN, bold=True))
    header.append("Correct!", Style(color=SUCCESS_GREEN, bold=True))
    return header


def create_error_header() -> Text:
    """Create an error/incorrect answer header."""
    header = Text()
    header.append("✗ ", Style(color=ERROR_RED, bold=True))
    header.append("Not quite!", Style(color=ERROR_RED, bold=True))
    return header


def create_session_complete_header() -> Text:
    """Create session complete header."""
    header = Text()
    header.append("🎉 ", Style(color=CHINESE_GOLD))
    header.append("Session Complete!", Style(color=CHINESE_RED, bold=True))
    return header
