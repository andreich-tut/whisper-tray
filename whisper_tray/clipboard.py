"""
Clipboard and paste operations module.

Handles copying text to clipboard and simulating paste keyboard shortcuts.
Cross-platform: uses Cmd+V on macOS, Ctrl+V elsewhere.
"""

from __future__ import annotations

import logging
import sys
import time

import pyperclip
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key

logger = logging.getLogger(__name__)


class ClipboardManager:
    """Manages clipboard operations and paste simulation."""

    def __init__(self, paste_delay: float = 0.1, auto_paste: bool = True) -> None:
        """
        Initialize clipboard manager.

        Args:
            paste_delay: Seconds to wait before auto-pasting
            auto_paste: Whether to automatically paste after copying
        """
        self.paste_delay = paste_delay
        self.auto_paste = auto_paste
        self._keyboard_controller = KeyboardController()
        # Platform-aware paste modifier: Cmd on macOS, Ctrl elsewhere
        self._paste_modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl

    def copy_and_paste(self, text: str) -> None:
        """
        Copy text to clipboard and optionally auto-paste.

        Args:
            text: Text to copy and paste
        """
        # Copy to clipboard
        pyperclip.copy(text)
        logger.info("Text copied to clipboard")

        # Auto-paste if enabled
        if self.auto_paste:
            time.sleep(self.paste_delay)
            # Micro-sleep for clipboard registration
            time.sleep(0.05)
            # Simulate platform-aware paste (Cmd+V on macOS, Ctrl+V elsewhere)
            with self._keyboard_controller.pressed(self._paste_modifier):
                self._keyboard_controller.press("v")
                self._keyboard_controller.release("v")
            logger.info("Text auto-pasted")

    def toggle_auto_paste(self) -> bool:
        """
        Toggle auto-paste setting.

        Returns:
            New auto_paste state
        """
        self.auto_paste = not self.auto_paste
        status = "enabled" if self.auto_paste else "disabled"
        logger.info(f"Auto-paste {status}")
        return self.auto_paste
