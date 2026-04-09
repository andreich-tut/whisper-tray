"""
Application state and presentation models.

This module centralizes state transitions so tray and future overlay UI
can react to the same structured events.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence


class AppState(Enum):
    """High-level application states visible to the user."""

    LOADING_MODEL = "loading_model"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass(frozen=True)
class AppStateSnapshot:
    """Thread-safe snapshot of the current app state."""

    state: AppState
    device: str = "cpu"
    message: str | None = None


@dataclass(frozen=True)
class AppStatePresentation:
    """UI-facing representation used by tray and overlay components."""

    state: AppState
    tray_title: str
    overlay_badge: str
    overlay_primary: str
    overlay_secondary: str | None
    icon_color: str
    overlay_hint: str | None = None
    overlay_auto_hide_seconds: float | None = None
    overlay_density: str = "detailed"
    flash_processing: bool = False


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

    def present(self, snapshot: AppStateSnapshot) -> AppStatePresentation:
        """Build the UI presentation for a state snapshot."""
        if snapshot.state is AppState.LOADING_MODEL:
            return AppStatePresentation(
                state=snapshot.state,
                tray_title="Loading model...",
                overlay_badge="Loading",
                overlay_primary="Loading model...",
                overlay_secondary=self._overlay_secondary(
                    snapshot.state,
                    "WhisperTray is warming up in the background.",
                ),
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
                overlay_primary="Listening...",
                overlay_secondary=self._overlay_secondary(
                    snapshot.state,
                    "Release the hotkey to start transcription.",
                ),
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
                overlay_secondary=self._overlay_secondary(
                    snapshot.state,
                    "Transcribing your latest recording.",
                ),
                icon_color="orange",
                overlay_hint=self._overlay_hint(
                    snapshot.state,
                    "Typing stays unblocked while the worker finishes.",
                ),
                overlay_density=self._overlay_density,
                flash_processing=True,
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
            overlay_primary="Ready",
            overlay_secondary=self._overlay_secondary(
                AppState.READY,
                f"Hold {self._hotkey_label} to dictate.",
            ),
            icon_color="lightgreen",
            overlay_hint=self._overlay_hint(
                AppState.READY,
                "Release the hotkey to transcribe and paste.",
            ),
            overlay_auto_hide_seconds=self._ready_auto_hide(),
            overlay_density=self._overlay_density,
        )


StateListener = Callable[[AppStateSnapshot], None]


class AppStatePublisher:
    """Thread-safe state publisher for tray and overlay observers."""

    def __init__(self, initial_snapshot: AppStateSnapshot) -> None:
        self._snapshot = initial_snapshot
        self._listeners: list[StateListener] = []
        self._lock = threading.Lock()

    @property
    def snapshot(self) -> AppStateSnapshot:
        """Return the latest published state snapshot."""
        with self._lock:
            return self._snapshot

    def subscribe(self, listener: StateListener, *, emit_current: bool = True) -> None:
        """Register a listener that will be notified on state changes."""
        with self._lock:
            self._listeners.append(listener)
            snapshot = self._snapshot
        if emit_current:
            listener(snapshot)

    def publish(
        self,
        state: AppState,
        *,
        device: str,
        message: str | None = None,
    ) -> AppStateSnapshot:
        """Publish a new state snapshot to all listeners."""
        snapshot = AppStateSnapshot(state=state, device=device, message=message)
        with self._lock:
            self._snapshot = snapshot
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(snapshot)
        return snapshot
