"""Tray icon updates, menu refresh, and user notifications."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

logger = logging.getLogger(__name__)


class TrayUpdatesCoordinator:
    """Update the tray icon, refresh the menu, and send notifications."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def update_tray_icon(self) -> None:
        """Update the tray icon image and hover text for the current state."""
        if not self._app._tray_icon_ref:
            return

        with self._app._tray_update_lock:
            try:
                self._app._tray_icon.update_icon_for_presentation(
                    self._app._tray_icon_ref,
                    self._app._state_presentation,
                    flash_on=self._app._processing_flash_on,
                )
                self._app._tray_icon_ref.title = self._app._get_tray_title()
            except Exception:
                logger.warning("Failed to update tray icon state", exc_info=True)

    def refresh_tray_menu(self, icon: object) -> None:
        """Refresh dynamic tray menu checkmarks when the backend supports it."""
        update_menu = getattr(icon, "update_menu", None)
        if not callable(update_menu):
            return

        try:
            update_menu()
        except Exception:
            logger.debug("Failed to refresh tray menu", exc_info=True)

    def notify_user(self, message: str) -> None:
        """Show a best-effort tray notification without breaking app flow."""
        if not self._app._tray_icon_ref:
            return

        try:
            self._app._tray_icon_ref.notify(message)
        except Exception:
            logger.debug("Failed to send tray notification", exc_info=True)
