"""Session-level actions: hotkey setup, auto-paste, and exit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from whisper_tray.adapters.hotkey.pynput_listener import HotkeyListener

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp


class SessionActions:
    """Handle session-level tray actions and startup helpers."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def setup_hotkey_listener(self) -> None:
        """Set up the global hotkey listener."""
        self._app._hotkey_listener = HotkeyListener(
            hotkey=self._app.config.hotkey.hotkey,
            on_press=self._app._on_hotkey_pressed,
            on_release=self._app._on_hotkey_released,
        )

    def on_toggle_auto_paste(self, icon: object, item: object | None) -> None:
        """Handle toggle auto-paste menu actions."""
        del icon, item
        new_state = self._app._clipboard.toggle_auto_paste()
        self._app._notify_user(f"Auto-paste {'enabled' if new_state else 'disabled'}")

    @staticmethod
    def on_exit(icon: object, item: object | None) -> None:
        """Handle exit menu actions."""
        del item
        stop = getattr(icon, "stop", None)
        if callable(stop):
            stop()
