"""Clipboard ownership monitor."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from whisper_tray.state import AppState

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp


class ClipboardMonitorCoordinator:
    """Watch clipboard ownership and revert transcript state after external changes."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def clipboard_monitor_loop(self) -> None:
        """Revert the transcript state after the clipboard changes elsewhere."""
        while not self._app._clipboard_monitor_stop.wait(0.25):
            if self._app._state_snapshot.state is not AppState.TRANSCRIBED:
                continue
            if self._app._clipboard.owns_clipboard():
                continue
            self._app._publish_state(AppState.READY)

    def start_clipboard_monitor(self) -> None:
        """Start the lightweight clipboard ownership monitor."""
        self._app._clipboard_monitor_stop.clear()
        self._app._clipboard_monitor = threading.Thread(
            target=self.clipboard_monitor_loop,
            daemon=True,
            name="clipboard-monitor",
        )
        self._app._clipboard_monitor.start()

    def stop_clipboard_monitor(self) -> None:
        """Stop the clipboard ownership monitor."""
        self._app._clipboard_monitor_stop.set()
        if self._app._clipboard_monitor and self._app._clipboard_monitor.is_alive():
            self._app._clipboard_monitor.join(timeout=1.0)
        self._app._clipboard_monitor = None
