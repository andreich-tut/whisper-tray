"""Overlay configuration actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from whisper_tray.app_constants import OVERLAY_INSTALL_MESSAGE

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp


class OverlayActions:
    """Handle overlay enable/disable and setting change actions."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    @staticmethod
    def format_overlay_position(position: str) -> str:
        """Convert an overlay corner into a readable tray label."""
        return position.replace("-", " ").title()

    @staticmethod
    def format_overlay_auto_hide(seconds: float) -> str:
        """Convert a ready-state timeout into a readable tray label."""
        if seconds <= 0:
            return "Stay Visible"
        if seconds.is_integer():
            unit = "Second" if seconds == 1 else "Seconds"
            return f"{int(seconds)} {unit}"
        return f"{seconds:g} Seconds"

    @staticmethod
    def format_overlay_density(density: str) -> str:
        """Convert an overlay density into a readable tray label."""
        return density.title()

    @staticmethod
    def format_overlay_screen(screen: str) -> str:
        """Convert an overlay screen target into a readable tray label."""
        labels = {
            "primary": "Primary Display",
            "cursor": "Cursor Display",
        }
        return labels.get(screen, screen.replace("-", " ").title())

    def on_toggle_overlay(self, icon: object, item: object | None) -> None:
        """Handle toggling the optional on-screen overlay."""
        del item
        requested_state = not self._app.config.overlay.enabled
        self._app.config.overlay.enabled = requested_state
        overlay_active = self._app._apply_overlay_settings()
        self._app._refresh_tray_menu(icon)

        if requested_state and overlay_active:
            self._app._notify_user(
                "Overlay enabled "
                f"({self.format_overlay_position(self._app.config.overlay.position)})"
            )
            return

        if requested_state:
            self._app._notify_user(OVERLAY_INSTALL_MESSAGE)
            return

        self._app._notify_user("Overlay disabled")

    def on_set_overlay_position(
        self,
        position: str,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting a tray-managed overlay corner."""
        del item
        if position == self._app.config.overlay.position:
            return

        self._app.config.overlay.position = position
        overlay_was_enabled = self._app.config.overlay.enabled
        overlay_active = (
            self._app._apply_overlay_settings() if overlay_was_enabled else False
        )
        self._app._refresh_tray_menu(icon)

        if overlay_was_enabled and not overlay_active:
            self._app._notify_user(OVERLAY_INSTALL_MESSAGE)
            return

        self._app._notify_user(
            f"Overlay position: {self.format_overlay_position(position)}"
        )

    def on_set_overlay_auto_hide(
        self,
        seconds: float,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting the ready-state overlay timeout."""
        del item
        if abs(seconds - self._app.config.overlay.auto_hide_seconds) < 1e-9:
            return

        self._app.config.overlay.auto_hide_seconds = seconds
        self._app._refresh_presentation_model()
        self._app._refresh_tray_menu(icon)
        self._app._notify_user(
            f"Overlay ready auto-hide: {self.format_overlay_auto_hide(seconds)}"
        )

    def on_set_overlay_screen(
        self,
        screen: str,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting the overlay display target."""
        del item
        if screen == self._app.config.overlay.screen:
            return

        self._app.config.overlay.screen = screen
        overlay_was_enabled = self._app.config.overlay.enabled
        overlay_active = (
            self._app._apply_overlay_settings() if overlay_was_enabled else False
        )
        self._app._refresh_tray_menu(icon)

        if overlay_was_enabled and not overlay_active:
            self._app._notify_user(OVERLAY_INSTALL_MESSAGE)
            return

        self._app._notify_user(f"Overlay display: {self.format_overlay_screen(screen)}")

    def on_set_overlay_density(
        self,
        density: str,
        icon: object,
        item: object | None,
    ) -> None:
        """Handle selecting the overlay presentation density."""
        del item
        if density == self._app.config.overlay.density:
            return

        self._app.config.overlay.density = density
        self._app._refresh_presentation_model()
        self._app._refresh_tray_menu(icon)
        self._app._notify_user(f"Overlay view: {self.format_overlay_density(density)}")
