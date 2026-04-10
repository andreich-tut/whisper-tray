"""Core application state types and publisher."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class AppState(Enum):
    """High-level application states visible to the user."""

    LOADING_MODEL = "loading_model"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    TRANSCRIBED = "transcribed"
    ERROR = "error"


@dataclass(frozen=True)
class AppStateSnapshot:
    """Thread-safe snapshot of the current app state."""

    state: AppState
    device: str = "cpu"
    message: str | None = None
    transcript: str | None = None
    auto_pasted: bool = False


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
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> AppStateSnapshot:
        """Publish a new state snapshot to all listeners."""
        snapshot = AppStateSnapshot(
            state=state,
            device=device,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )
        return self.publish_snapshot(snapshot)

    def publish_snapshot(self, snapshot: AppStateSnapshot) -> AppStateSnapshot:
        """Publish a pre-built state snapshot to all listeners."""
        with self._lock:
            self._snapshot = snapshot
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(snapshot)
        return snapshot
