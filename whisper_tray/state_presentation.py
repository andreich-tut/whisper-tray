"""Compatibility facade for state presentation helpers."""

from whisper_tray.core.presentation import (
    AppStatePresenter,
    ErrorPresentation,
    describe_error,
    format_hotkey,
)

__all__ = [
    "AppStatePresenter",
    "ErrorPresentation",
    "describe_error",
    "format_hotkey",
]
