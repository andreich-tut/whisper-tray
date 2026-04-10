"""Tray runtime protocol and backend selection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from whisper_tray.overlay import OverlayController
from whisper_tray.overlay.controller import OverlaySettings, _pyside6_is_available

if TYPE_CHECKING:
    from whisper_tray.app import WhisperTrayApp


class TrayRuntime(Protocol):
    """Backend interface for tray event-loop implementations."""

    def prepare(self, app: "WhisperTrayApp") -> None:
        """Create tray resources before the app starts background work."""

    def run(self) -> None:
        """Enter the backend event loop and block until exit."""

    def create_overlay_controller(
        self,
        settings: OverlaySettings,
    ) -> OverlayController:
        """Create an overlay controller compatible with this tray runtime."""


def should_use_qt_tray() -> bool:
    """Return whether the optional Qt tray runtime is available."""
    return _pyside6_is_available()
