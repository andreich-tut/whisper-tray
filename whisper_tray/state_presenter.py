"""State-to-presentation mapping for tray and overlay UI."""

from __future__ import annotations

from whisper_tray.state_errors import describe_error
from whisper_tray.state_formatting import format_transcript
from whisper_tray.state_models import AppState, AppStatePresentation, AppStateSnapshot


class AppStatePresenter:
    """Maps internal app state to tray and overlay presentation."""

    def __init__(
        self,
        hotkey_label: str = "Ctrl+Shift+Space",
        ready_auto_hide_seconds: float = 1.5,
        overlay_density: str = "detailed",
    ) -> None:
        self._hotkey_label = hotkey_label
        self._ready_auto_hide_seconds = ready_auto_hide_seconds
        self._overlay_density = (
            overlay_density
            if overlay_density in {"compact", "detailed"}
            else "detailed"
        )

    def _overlay_secondary(
        self,
        state: AppState,
        text: str | None,
    ) -> str | None:
        """Return secondary copy based on the selected presentation density."""
        if self._overlay_density == "compact" and state is not AppState.ERROR:
            return None
        return text

    def _overlay_hint(
        self,
        state: AppState,
        text: str | None,
    ) -> str | None:
        """Return tertiary helper copy for states that benefit from it."""
        if not text:
            return None
        if self._overlay_density == "compact" and state is not AppState.ERROR:
            return None
        return text

    def _ready_auto_hide(self) -> float | None:
        """Translate the configured ready-state timeout into overlay behavior."""
        if self._ready_auto_hide_seconds <= 0:
            return None
        return self._ready_auto_hide_seconds

    def present(self, snapshot: AppStateSnapshot) -> AppStatePresentation:
        """Build the UI presentation for a state snapshot."""
        if snapshot.state is AppState.LOADING_MODEL:
            return AppStatePresentation(
                state=snapshot.state,
                tray_title="Loading model...",
                overlay_badge="Loading",
                overlay_primary="WhisperTray is warming up in the background.",
                overlay_secondary=self._overlay_secondary(snapshot.state, None),
                icon_color="yellow",
                overlay_hint=self._overlay_hint(
                    snapshot.state,
                    "The tray icon turns green when dictation is ready.",
                ),
                overlay_density=self._overlay_density,
            )

        if snapshot.state is AppState.RECORDING:
            return AppStatePresentation(
                state=snapshot.state,
                tray_title="Recording...",
                overlay_badge="Listening",
                overlay_primary="Release the hotkey to start transcription.",
                overlay_secondary=self._overlay_secondary(snapshot.state, None),
                icon_color="tomato",
                overlay_hint=self._overlay_hint(
                    snapshot.state,
                    "Keep holding the hotkey while you speak naturally.",
                ),
                overlay_density=self._overlay_density,
            )

        if snapshot.state is AppState.PROCESSING:
            return AppStatePresentation(
                state=snapshot.state,
                tray_title="Processing...",
                overlay_badge="Processing",
                overlay_primary="Processing speech...",
                overlay_secondary=self._overlay_secondary(snapshot.state, None),
                icon_color="orange",
                overlay_hint=self._overlay_hint(
                    snapshot.state,
                    "Typing stays unblocked while the worker finishes.",
                ),
                overlay_density=self._overlay_density,
                flash_processing=True,
            )

        if snapshot.state is AppState.TRANSCRIBED:
            badge = "PASTED" if snapshot.auto_pasted else "COPIED"
            secondary = (
                "Pasted and still available in the clipboard."
                if snapshot.auto_pasted
                else "Copied to the clipboard."
            )
            return AppStatePresentation(
                state=snapshot.state,
                tray_title=f"WhisperTray - {badge.title()} transcript",
                overlay_badge=badge,
                overlay_primary=format_transcript(
                    snapshot.transcript,
                    density=self._overlay_density,
                ),
                overlay_secondary=self._overlay_secondary(snapshot.state, secondary),
                icon_color="lightgreen",
                overlay_hint=self._overlay_hint(
                    snapshot.state,
                    "Shown until clipboard changes",
                ),
                overlay_density=self._overlay_density,
            )

        if snapshot.state is AppState.ERROR:
            error = describe_error(snapshot.message)
            return AppStatePresentation(
                state=snapshot.state,
                tray_title=f"Error: {error.detail}",
                overlay_badge="Error",
                overlay_primary=error.primary,
                overlay_secondary=error.detail,
                icon_color="crimson",
                overlay_hint=error.hint,
                overlay_density=self._overlay_density,
            )

        device_label = "CPU" if snapshot.device == "cpu" else "GPU"
        return AppStatePresentation(
            state=AppState.READY,
            tray_title=f"WhisperTray ({device_label} mode) - Ready",
            overlay_badge="Ready",
            overlay_primary=f"Hold {self._hotkey_label} to dictate.",
            overlay_secondary=self._overlay_secondary(AppState.READY, None),
            icon_color="lightgreen",
            overlay_hint=self._overlay_hint(
                AppState.READY,
                "Release the hotkey to transcribe and paste.",
            ),
            overlay_auto_hide_seconds=self._ready_auto_hide(),
            overlay_density=self._overlay_density,
        )
