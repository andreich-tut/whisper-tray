"""Presentation helpers for shared app state."""

from whisper_tray.core.presentation.errors import ErrorPresentation, describe_error
from whisper_tray.core.presentation.formatting import format_hotkey
from whisper_tray.core.presentation.presenter import AppStatePresenter

__all__ = [
    "AppStatePresenter",
    "ErrorPresentation",
    "describe_error",
    "format_hotkey",
]
