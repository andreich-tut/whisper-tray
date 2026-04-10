"""Public facade for application state and presentation models."""

from whisper_tray.state_models import (
    AppState,
    AppStatePresentation,
    AppStatePublisher,
    AppStateSnapshot,
    StateListener,
)
from whisper_tray.state_presentation import (
    AppStatePresenter,
    ErrorPresentation,
    describe_error,
    format_hotkey,
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
