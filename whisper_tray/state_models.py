"""Compatibility facade for backend-neutral state models."""

from whisper_tray.core.state.models import (
    AppState,
    AppStatePresentation,
    AppStatePublisher,
    AppStateSnapshot,
    StateListener,
)

__all__ = [
    "AppState",
    "AppStatePresentation",
    "AppStatePublisher",
    "AppStateSnapshot",
    "StateListener",
]
