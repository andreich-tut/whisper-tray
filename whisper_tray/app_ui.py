"""UI/runtime helpers for tray and overlay coordination."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from whisper_tray.overlay import NullOverlayController, OverlaySettings
from whisper_tray.state import (
    AppState,
    AppStatePresenter,
    AppStateSnapshot,
    format_hotkey,
)
from whisper_tray.tray.menu import TrayMenu
from whisper_tray.tray.runtime import (
    PystrayTrayRuntime,
    QtTrayRuntime,
    TrayRuntime,
    should_use_qt_tray,
)

if TYPE_CHECKING:
    from whisper_tray.app import WhisperTrayApp

logger = logging.getLogger(__name__)


class AppUiCoordinator:
    """Coordinate shared tray, overlay, and presentation updates."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def on_state_changed(self, snapshot: AppStateSnapshot) -> None:
        """Cache and fan out the latest app state to UI components."""
        self._app._state_snapshot = snapshot
        self._app._state_presentation = self._app._state_presenter.present(snapshot)
        self._app._overlay.show_state(self._app._state_presentation)
        self._app._update_tray_icon()

    def build_state_presenter(self) -> AppStatePresenter:
        """Create the shared presenter from the current runtime settings."""
        return AppStatePresenter(
            hotkey_label=format_hotkey(self._app.config.hotkey.hotkey),
            ready_auto_hide_seconds=self._app.config.overlay.auto_hide_seconds,
            overlay_density=self._app.config.overlay.density,
        )

    def refresh_presentation_model(self) -> None:
        """Rebuild the presenter and rerender the current UI state."""
        self._app._state_presenter = self.build_state_presenter()
        self.on_state_changed(self._app._state_snapshot)

    def build_overlay_settings(self) -> OverlaySettings:
        """Build explicit overlay runtime settings for the current config."""
        return OverlaySettings(
            enabled=self._app.config.overlay.enabled,
            position=self._app.config.overlay.position,
            screen_target=self._app.config.overlay.screen,
        )

    def build_snapshot(
        self,
        state: AppState,
        *,
        message: str | None = None,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> AppStateSnapshot:
        """Create a typed app-state snapshot for the current runtime."""
        return AppStateSnapshot(
            state=state,
            device=self._app._transcriber.device,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )

    def publish_snapshot(self, snapshot: AppStateSnapshot) -> None:
        """Publish a pre-built shared app state snapshot."""
        self._app._state_publisher.publish_snapshot(snapshot)

    def publish_state(
        self,
        state: AppState,
        message: str | None = None,
        *,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> None:
        """Publish a new shared app state."""
        self.publish_snapshot(
            self.build_snapshot(
                state,
                message=message,
                transcript=transcript,
                auto_pasted=auto_pasted,
            )
        )

    def get_tray_title(self) -> str:
        """Return the current tray hover text for the active app state."""
        return self._app._state_presentation.tray_title

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
                self._app._tray_icon_ref.title = self.get_tray_title()
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
