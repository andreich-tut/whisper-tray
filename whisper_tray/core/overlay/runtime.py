"""Backend-neutral overlay protocols and threaded controller."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

from whisper_tray.core.state import AppStatePresentation

logger = logging.getLogger(__name__)


class OverlayController(Protocol):
    """Minimal interface for overlay implementations."""

    def show_state(self, presentation: AppStatePresentation) -> None:
        """Render the latest UI state."""

    def close(self) -> None:
        """Release any overlay resources."""


class OverlayCommandKind(Enum):
    """Command types sent to a live overlay runtime."""

    SHOW = "show"
    CLOSE = "close"


@dataclass(frozen=True)
class OverlayCommand:
    """Thread-safe overlay command passed to the UI runtime."""

    kind: OverlayCommandKind
    presentation: AppStatePresentation | None = None


OverlayStartupCallback = Callable[[bool], None]


@dataclass(frozen=True)
class OverlaySettings:
    """Explicit runtime settings for the optional overlay surface."""

    enabled: bool
    position: str = "bottom-right"
    screen_target: str = "primary"


class OverlayRuntime(Protocol):
    """Runtime implementation that owns the actual overlay event loop."""

    def run(self, startup_callback: OverlayStartupCallback) -> None:
        """Start the runtime and block until it exits."""


OverlayRuntimeFactory = Callable[
    [queue.Queue[OverlayCommand], OverlaySettings],
    OverlayRuntime,
]


@dataclass
class NullOverlayController:
    """No-op overlay used until a UI backend is available."""

    last_presentation: AppStatePresentation | None = None

    def show_state(self, presentation: AppStatePresentation) -> None:
        """Remember the latest state without rendering a window."""
        self.last_presentation = presentation

    def close(self) -> None:
        """No-op cleanup."""


class ThreadedOverlayController:
    """Thread-safe controller that proxies state updates to a UI runtime."""

    _STARTUP_TIMEOUT_SECONDS = 2.0

    def __init__(
        self,
        runtime_factory: OverlayRuntimeFactory,
        *,
        settings: OverlaySettings,
    ) -> None:
        self._commands: queue.Queue[OverlayCommand] = queue.Queue()
        self._closed = threading.Event()
        self._startup_complete = threading.Event()
        self._startup_succeeded = False
        self._thread = threading.Thread(
            target=self._run_runtime,
            args=(runtime_factory, settings),
            daemon=True,
            name="overlay-ui",
        )
        self._thread.start()
        if not self._startup_complete.wait(self._STARTUP_TIMEOUT_SECONDS):
            self.close()
            raise RuntimeError("Overlay runtime did not confirm startup.")
        if not self._startup_succeeded:
            self.close()
            raise RuntimeError("Overlay runtime failed to start.")

    def _run_runtime(
        self,
        runtime_factory: OverlayRuntimeFactory,
        settings: OverlaySettings,
    ) -> None:
        """Create and run the overlay backend."""
        try:
            runtime = runtime_factory(self._commands, settings)
            runtime.run(self._mark_startup)
            self._mark_startup(True)
        except Exception:
            self._mark_startup(False)
            logger.warning("Overlay runtime stopped unexpectedly", exc_info=True)

    def _mark_startup(self, succeeded: bool) -> None:
        """Record whether the runtime finished bootstrapping."""
        if self._startup_complete.is_set():
            return
        self._startup_succeeded = succeeded
        self._startup_complete.set()

    def show_state(self, presentation: AppStatePresentation) -> None:
        """Queue a presentation update for the overlay runtime."""
        if self._closed.is_set():
            return
        self._commands.put(
            OverlayCommand(
                kind=OverlayCommandKind.SHOW,
                presentation=presentation,
            )
        )

    def close(self) -> None:
        """Request the overlay runtime to exit and wait briefly for cleanup."""
        if self._closed.is_set():
            return
        self._closed.set()
        self._commands.put(OverlayCommand(kind=OverlayCommandKind.CLOSE))
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
