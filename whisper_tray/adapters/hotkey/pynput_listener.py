"""
Hotkey detection module.

Handles global keyboard event listening using pynput.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Callable, Optional, Set

try:
    from pynput import keyboard

    _PYNPUT_IMPORT_ERROR: Exception | None = None
except ImportError as exc:
    keyboard = SimpleNamespace(Listener=None)
    _PYNPUT_IMPORT_ERROR = exc

# pynput has no official type distribution; use Any stubs at this boundary
PynputKey = Any
PynputKeyCode = Any

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Manages global hotkey detection."""

    def __init__(
        self,
        hotkey: Set[str],
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None,
    ) -> None:
        """
        Initialize hotkey listener.

        Args:
            hotkey: Set of key names for the hotkey
                (e.g., {'ctrl', 'space'})
            on_press: Callback when hotkey combination is pressed
            on_release: Callback when hotkey combination is released
        """
        self.hotkey = hotkey
        self._on_press_callback = on_press
        self._on_release_callback = on_release
        self._current_keys: Set[str] = set()
        self._listener: Optional[keyboard.Listener] = None
        self._is_held: bool = False  # Track if hotkey is currently held down

    @staticmethod
    def _get_key_name(key: PynputKey | PynputKeyCode) -> str:
        """Extract key name from pynput key object."""
        if hasattr(key, "char") and key.char is not None:
            return str(key.char).lower()
        elif hasattr(key, "name"):
            key_name = str(key.name).lower()
            # Normalize modifier keys (ctrl_l/ctrl_r -> ctrl, etc.)
            if key_name.startswith("ctrl"):
                return "ctrl"
            elif key_name.startswith("shift"):
                return "shift"
            elif key_name.startswith("alt"):
                return "alt"
            elif key_name.startswith("cmd") or key_name.startswith("win"):
                return "cmd"
            elif "space" in key_name:
                return "space"
            return key_name
        else:
            # Handle special keys
            key_str = str(key).lower()
            if "ctrl" in key_str:
                return "ctrl"
            elif "shift" in key_str:
                return "shift"
            elif "space" in key_str or "bar" in key_str:
                return "space"
            elif "alt" in key_str:
                return "alt"
            elif "cmd" in key_str or "win" in key_str:
                return "cmd"
            return key_str

    def _on_press(self, key: PynputKey | PynputKeyCode) -> None:
        """Handle key press events."""
        key_name = self._get_key_name(key)
        self._current_keys.add(key_name)

        # Check if hotkey combination is pressed
        # Only trigger when the combination is first completed, not on every key repeat
        if self.hotkey.issubset(self._current_keys) and not self._is_held:
            self._is_held = True
            logger.info("Hotkey activated")
            if self._on_press_callback:
                self._on_press_callback()

    def _on_release(self, key: PynputKey | PynputKeyCode) -> None:
        """Handle key release events."""
        key_name = self._get_key_name(key)

        # Check if hotkey combination is broken
        was_held = self.hotkey.issubset(self._current_keys)
        self._current_keys.discard(key_name)

        if was_held and not self.hotkey.issubset(self._current_keys):
            self._is_held = False
            logger.info("Hotkey deactivated")
            if self._on_release_callback:
                self._on_release_callback()

    def start(self) -> None:
        """Start listening for keyboard events."""
        if keyboard.Listener is None:
            raise RuntimeError(
                "pynput keyboard backend is unavailable. "
                "Global hotkeys require a supported desktop session."
            ) from _PYNPUT_IMPORT_ERROR

        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()
        logger.info("Keyboard listener started")

    def stop(self) -> None:
        """Stop listening for keyboard events."""
        if self._listener:
            self._listener.stop()
            logger.info("Keyboard listener stopped")

    @property
    def is_running(self) -> bool:
        """Check if listener is currently running."""
        return self._listener is not None and self._listener.running
