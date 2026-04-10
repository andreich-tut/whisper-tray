"""Session, language, and overlay action handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from whisper_tray.app.actions.language import LanguageActions
from whisper_tray.app.actions.overlay import OverlayActions
from whisper_tray.app.actions.session import SessionActions

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

__all__ = ["AppSessionActions"]


class AppSessionActions:
    """Coordinate tray menu actions across language, overlay, and session concerns."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app
        self._language = LanguageActions(app)
        self._overlay = OverlayActions(app)
        self._session = SessionActions(app)

    # --- format helpers (delegated to overlay actions) ---

    @staticmethod
    def format_overlay_position(position: str) -> str:
        """Convert an overlay corner into a readable tray label."""
        return OverlayActions.format_overlay_position(position)

    @staticmethod
    def format_overlay_auto_hide(seconds: float) -> str:
        """Convert a ready-state timeout into a readable tray label."""
        return OverlayActions.format_overlay_auto_hide(seconds)

    @staticmethod
    def format_overlay_density(density: str) -> str:
        """Convert an overlay density into a readable tray label."""
        return OverlayActions.format_overlay_density(density)

    @staticmethod
    def format_overlay_screen(screen: str) -> str:
        """Convert an overlay screen target into a readable tray label."""
        return OverlayActions.format_overlay_screen(screen)

    # --- session ---

    def setup_hotkey_listener(self) -> None:
        """Set up the global hotkey listener."""
        self._session.setup_hotkey_listener()

    def on_toggle_auto_paste(self, icon: object, item: object | None) -> None:
        """Handle toggle auto-paste menu actions."""
        self._session.on_toggle_auto_paste(icon, item)

    @staticmethod
    def on_exit(icon: object, item: object | None) -> None:
        """Handle exit menu actions."""
        SessionActions.on_exit(icon, item)

    # --- language ---

    def on_set_language_en(self, icon: object, item: object | None) -> None:
        """Handle selecting English transcription."""
        self._language.on_set_language_en(icon, item)

    def on_set_language_ru(self, icon: object, item: object | None) -> None:
        """Handle selecting Russian transcription."""
        self._language.on_set_language_ru(icon, item)

    def on_set_language_auto(self, icon: object, item: object | None) -> None:
        """Handle selecting automatic language detection."""
        self._language.on_set_language_auto(icon, item)

    # --- overlay ---

    def on_toggle_overlay(self, icon: object, item: object | None) -> None:
        """Handle toggling the optional on-screen overlay."""
        self._overlay.on_toggle_overlay(icon, item)

    def on_set_overlay_position(
        self,
        position: str,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting a tray-managed overlay corner."""
        self._overlay.on_set_overlay_position(position, icon, item)

    def on_set_overlay_auto_hide(
        self,
        seconds: float,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting the ready-state overlay timeout."""
        self._overlay.on_set_overlay_auto_hide(seconds, icon, item)

    def on_set_overlay_screen(
        self,
        screen: str,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting the overlay display target."""
        self._overlay.on_set_overlay_screen(screen, icon, item)

    def on_set_overlay_density(
        self,
        density: str,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting the overlay presentation density."""
        self._overlay.on_set_overlay_density(density, icon, item)
