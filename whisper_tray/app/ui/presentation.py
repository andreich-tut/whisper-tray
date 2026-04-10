"""State presentation and snapshot publishing helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from whisper_tray.state import (
    AppState,
    AppStatePresenter,
    AppStateSnapshot,
    format_hotkey,
)

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp


class PresentationCoordinator:
    """Build and publish app-state snapshots and drive the state presenter."""

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
