"""Overlay and tray runtime setup helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from whisper_tray.adapters.tray import (
    PystrayTrayRuntime,
    QtTrayRuntime,
    TrayRuntime,
    should_use_qt_tray,
)
from whisper_tray.overlay import NullOverlayController, OverlaySettings
from whisper_tray.tray.menu import TrayMenu

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

logger = logging.getLogger(__name__)


class OverlayRuntimeCoordinator:
    """Manage overlay controller lifecycle and tray runtime selection."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def build_overlay_settings(self) -> OverlaySettings:
        """Build explicit overlay runtime settings for the current config."""
        return OverlaySettings(
            enabled=self._app.config.overlay.enabled,
            position=self._app.config.overlay.position,
            screen_target=self._app.config.overlay.screen,
        )

    def apply_overlay_settings(self, *, render_current_state: bool = True) -> bool:
        """Recreate the overlay controller for the current runtime settings."""
        self._app._overlay.close()
        runtime = self._app._tray_runtime
        if runtime is None:
            runtime = PystrayTrayRuntime()
        self._app._overlay = runtime.create_overlay_controller(
            self.build_overlay_settings()
        )

        if self._app.config.overlay.enabled and isinstance(
            self._app._overlay, NullOverlayController
        ):
            self._app.config.overlay.enabled = False
            return False

        if render_current_state and self._app.config.overlay.enabled:
            self._app._overlay.show_state(self._app._state_presentation)

        return self._app.config.overlay.enabled

    def create_tray_runtime(self) -> TrayRuntime:
        """Choose the best tray runtime for the current environment."""
        tray_backend = self._app.config.ui.tray_backend

        if tray_backend == "pystray":
            return PystrayTrayRuntime()

        if should_use_qt_tray():
            return QtTrayRuntime()

        if tray_backend == "qt":
            logger.warning(
                "TRAY_BACKEND=qt requested, but PySide6 is unavailable. "
                "Falling back to pystray."
            )
        return PystrayTrayRuntime()

    def prepare_tray_runtime(self) -> None:
        """Prepare the preferred tray runtime with a safe Qt fallback."""
        self._app._tray_runtime = self.create_tray_runtime()
        try:
            self._app._tray_runtime.prepare(self._app)
        except Exception:
            if not isinstance(self._app._tray_runtime, QtTrayRuntime):
                raise

            logger.warning(
                "Qt tray runtime failed to start. Falling back to pystray "
                "and preserving overlay settings so the legacy backend can "
                "retry overlay startup.",
                exc_info=True,
            )
            self._app._tray_runtime = PystrayTrayRuntime()
            self._app._tray_runtime.prepare(self._app)

    def setup_tray_menu(self) -> TrayMenu:
        """Build the high-level tray menu used by both runtimes."""
        return TrayMenu(
            on_toggle_auto_paste=self._app._on_toggle_auto_paste,
            on_set_language_en=self._app._on_set_language_en,
            on_set_language_ru=self._app._on_set_language_ru,
            on_set_language_auto=self._app._on_set_language_auto,
            on_toggle_overlay=self._app._on_toggle_overlay,
            on_set_overlay_position=self._app._on_set_overlay_position,
            on_set_overlay_screen=self._app._on_set_overlay_screen,
            on_set_overlay_auto_hide=self._app._on_set_overlay_auto_hide,
            on_set_overlay_density=self._app._on_set_overlay_density,
            on_exit=self._app._on_exit,
            get_auto_paste_state=lambda: self._app._clipboard.auto_paste,
            get_language_state=lambda: self._app._current_language,
            get_overlay_enabled_state=lambda: self._app.config.overlay.enabled,
            get_overlay_position_state=lambda: self._app.config.overlay.position,
            get_overlay_screen_state=lambda: self._app.config.overlay.screen,
            get_overlay_auto_hide_state=lambda: (
                self._app.config.overlay.auto_hide_seconds
            ),
            get_overlay_density_state=lambda: self._app.config.overlay.density,
        )
