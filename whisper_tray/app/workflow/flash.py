"""Processing flash timer for the tray icon."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from whisper_tray.state import AppState, AppStateSnapshot

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp


class FlashTimerCoordinator:
    """Flash the tray icon while the transcription worker is busy."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def start_flash_timer(self) -> None:
        """Start the background thread that flashes the icon during processing."""
        self._app._processing_flash_on = True
        self._app._flash_event.clear()
        self._app._publish_state(AppState.PROCESSING)

        def flash_loop() -> None:
            while not self._app._flash_event.is_set():
                self._app._processing_flash_on = not self._app._processing_flash_on
                self._app._update_tray_icon()
                self._app._flash_event.wait(0.5)

        self._app._flash_timer = threading.Thread(
            target=flash_loop,
            daemon=True,
            name="tray-processing-flash",
        )
        self._app._flash_timer.start()

    def stop_flash_timer(
        self,
        next_snapshot: AppStateSnapshot | None = None,
    ) -> None:
        """Stop the flash timer and publish the next stable state."""
        self._app._flash_event.set()
        if self._app._flash_timer and self._app._flash_timer.is_alive():
            self._app._flash_timer.join(timeout=1.0)
        self._app._flash_timer = None
        self._app._processing_flash_on = False
        self._app._publish_snapshot(
            next_snapshot or self._app._build_snapshot(self._app._get_idle_state())
        )
