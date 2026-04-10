"""Formatting helpers for app-state presentation."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Sequence

from whisper_tray.state_models import AppState, AppStatePresentation, AppStateSnapshot


@dataclass(frozen=True)
class ErrorPresentation:
    """Actionable copy used by the overlay for error states."""

    primary: str
    detail: str
    hint: str


def format_hotkey(hotkey: Sequence[str] | set[str]) -> str:
    """Convert a hotkey set into a stable, user-facing label."""
    display_names = {
        "alt": "Alt",
        "cmd": "Cmd",
        "command": "Cmd",
        "ctrl": "Ctrl",
        "shift": "Shift",
        "space": "Space",
        "super": "Super",
        "win": "Win",
    }
    priority = {
        "ctrl": 0,
        "shift": 1,
        "alt": 2,
        "cmd": 3,
        "command": 3,
        "super": 4,
        "win": 4,
        "space": 5,
    }

    ordered = sorted(
        hotkey,
        key=lambda key: (priority.get(key, 100), display_names.get(key, key.title())),
    )
    return "+".join(display_names.get(key, key.title()) for key in ordered)


def describe_error(message: str | None) -> ErrorPresentation:
    """Convert a raw runtime error into user-facing recovery copy."""
    detail = (message or "").strip() or "Check whisper_tray.log for details."
    lowered = detail.lower()

    if (
        "model failed" in lowered
        or "load model" in lowered
        or ("model" in lowered and "load" in lowered)
    ):
        return ErrorPresentation(
            primary="Model unavailable",
            detail=detail,
            hint="Try a smaller model, switch to CPU, or restart WhisperTray.",
        )

    if (
        "recording failed" in lowered
        or "microphone" in lowered
        or "host error" in lowered
        or "audio" in lowered
    ):
        return ErrorPresentation(
            primary="Microphone unavailable",
            detail=detail,
            hint="Close other audio apps, reconnect the mic, or try DEVICE=cpu.",
        )

    if "transcription" in lowered:
        return ErrorPresentation(
            primary="Transcription failed",
            detail=detail,
            hint="Try dictating again. If it keeps happening, check whisper_tray.log.",
        )

    return ErrorPresentation(
        primary="Something went wrong",
        detail=detail,
        hint="Try again. If the error persists, check whisper_tray.log.",
    )


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

    @staticmethod
    def _truncate_line(text: str, max_chars: int) -> str:
        """Clamp a single line of overlay copy to a stable maximum width."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _format_transcript(self, transcript: str | None) -> str:
        """Format recognized text for the selected overlay density."""
        normalized = " ".join((transcript or "").split())
        if not normalized:
            return "Transcript ready"

        if self._overlay_density == "compact":
            return self._truncate_line(normalized, max_chars=56)

        wrapped = textwrap.wrap(normalized, width=42, break_long_words=False)
        if len(wrapped) <= 3:
            return "\n".join(wrapped)

        visible_lines = wrapped[:3]
        visible_lines[-1] = self._truncate_line(visible_lines[-1], max_chars=39)
        if not visible_lines[-1].endswith("..."):
            visible_lines[-1] = visible_lines[-1].rstrip() + "..."
        return "\n".join(visible_lines)

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
                overlay_primary=self._format_transcript(snapshot.transcript),
                overlay_secondary=self._overlay_secondary(
                    snapshot.state,
                    secondary,
                ),
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
