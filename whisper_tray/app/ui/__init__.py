"""UI coordination package for tray, overlay, and presentation updates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from whisper_tray.adapters.tray.menu import TrayMenu
from whisper_tray.app.ui.overlay_runtime import OverlayRuntimeCoordinator
from whisper_tray.app.ui.presentation import PresentationCoordinator
from whisper_tray.app.ui.tray_updates import TrayUpdatesCoordinator
from whisper_tray.core.overlay import OverlaySettings
from whisper_tray.state import AppState, AppStatePresenter, AppStateSnapshot

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

__all__ = ["AppUiCoordinator"]


class AppUiCoordinator:
    """Coordinate shared tray, overlay, and presentation updates."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app
        self._presentation = PresentationCoordinator(app)
        self._tray = TrayUpdatesCoordinator(app)
        self._overlay_runtime = OverlayRuntimeCoordinator(app)

    # --- presentation ---

    def on_state_changed(self, snapshot: AppStateSnapshot) -> None:
        """Cache and fan out the latest app state to UI components."""
        self._presentation.on_state_changed(snapshot)

    def build_state_presenter(self) -> AppStatePresenter:
        """Create the shared presenter from the current runtime settings."""
        return self._presentation.build_state_presenter()

    def refresh_presentation_model(self) -> None:
        """Rebuild the presenter and rerender the current UI state."""
        self._presentation.refresh_presentation_model()

    def build_snapshot(
        self,
        state: AppState,
        *,
        message: str | None = None,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> AppStateSnapshot:
        """Create a typed app-state snapshot for the current runtime."""
        return self._presentation.build_snapshot(
            state,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )

    def publish_snapshot(self, snapshot: AppStateSnapshot) -> None:
        """Publish a pre-built shared app state snapshot."""
        self._presentation.publish_snapshot(snapshot)

    def publish_state(
        self,
        state: AppState,
        message: str | None = None,
        *,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> None:
        """Publish a new shared app state."""
        self._presentation.publish_state(
            state,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )

    def get_tray_title(self) -> str:
        """Return the current tray hover text for the active app state."""
        return self._presentation.get_tray_title()

    # --- tray updates ---

    def update_tray_icon(self) -> None:
        """Update the tray icon image and hover text for the current state."""
        self._tray.update_tray_icon()

    def refresh_tray_menu(self, icon: object) -> None:
        """Refresh dynamic tray menu checkmarks when the backend supports it."""
        self._tray.refresh_tray_menu(icon)

    def notify_user(self, message: str) -> None:
        """Show a best-effort tray notification without breaking app flow."""
        self._tray.notify_user(message)

    # --- overlay runtime ---

    def build_overlay_settings(self) -> OverlaySettings:
        """Build explicit overlay runtime settings for the current config."""
        return self._overlay_runtime.build_overlay_settings()

    def apply_overlay_settings(self, *, render_current_state: bool = True) -> bool:
        """Recreate the overlay controller for the current runtime settings."""
        return self._overlay_runtime.apply_overlay_settings(
            render_current_state=render_current_state
        )

    def create_tray_runtime(self) -> object:
        """Choose the best tray runtime for the current environment."""
        return self._overlay_runtime.create_tray_runtime()

    def prepare_tray_runtime(self) -> None:
        """Prepare the preferred tray runtime with a safe Qt fallback."""
        self._overlay_runtime.prepare_tray_runtime()

    def setup_tray_menu(self) -> TrayMenu:
        """Build the high-level tray menu used by both runtimes."""
        return self._overlay_runtime.setup_tray_menu()
