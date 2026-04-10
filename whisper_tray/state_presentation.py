"""Compatibility facade for state presentation helpers."""

from whisper_tray.state_errors import ErrorPresentation, describe_error
from whisper_tray.state_formatting import format_hotkey
from whisper_tray.state_presenter import AppStatePresenter

__all__ = [
    "AppStatePresenter",
    "ErrorPresentation",
    "describe_error",
    "format_hotkey",
]
