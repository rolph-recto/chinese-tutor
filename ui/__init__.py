"""Chinese Tutor UI Module - Fancy terminal interface for Chinese learning."""

from ui.app import TutorUI
from ui.components import (
    ExercisePanel,
    FeedbackPanel,
    RatingMenu,
    MasteryTable,
    WelcomeScreen,
    ProgressTracker,
)
from ui.styles import (
    CHINESE_RED,
    CHINESE_GOLD,
    SUCCESS_GREEN,
    ERROR_RED,
    INFO_BLUE,
    MUTED_GRAY,
)

__all__ = [
    "TutorUI",
    "ExercisePanel",
    "FeedbackPanel",
    "RatingMenu",
    "MasteryTable",
    "WelcomeScreen",
    "ProgressTracker",
    "CHINESE_RED",
    "CHINESE_GOLD",
    "SUCCESS_GREEN",
    "ERROR_RED",
    "INFO_BLUE",
    "MUTED_GRAY",
]
