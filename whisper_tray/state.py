"""Public facade for application state and presentation models."""

from whisper_tray.core.presentation import (
    AppStatePresenter,
    ErrorPresentation,
    describe_error,
    format_hotkey,
)
from whisper_tray.core.state import (
    AppState,
    AppStatePresentation,
    AppStatePublisher,
    AppStateSnapshot,
    StateListener,
)

__all__ = [
    "AppState",
    "AppStatePresentation",
    "AppStatePresenter",
    "AppStatePublisher",
    "AppStateSnapshot",
    "ErrorPresentation",
    "StateListener",
    "describe_error",
    "format_hotkey",
]
