"""Clipboard ownership and paste orchestration."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from typing import Callable

import pyperclip

from whisper_tray.clipboard.controller import ClipboardPasteController
from whisper_tray.clipboard.pyautogui_fallback import send_pyautogui_shortcut
from whisper_tray.clipboard.windows import (
    send_windows_paste_shortcut,
    send_windows_shift_insert_shortcut,
)

logger = logging.getLogger(__name__)

_WINDOWS_HOTKEY_RELEASE_DELAY_SECONDS = 0.15


@dataclass(frozen=True)
class PasteAttemptResult:
    """Result of trying to paste the latest clipboard contents."""

    succeeded: bool
    method: str


class ClipboardManager:
    """Manages clipboard operations and paste simulation."""

    def __init__(self, paste_delay: float = 0.1, auto_paste: bool = True) -> None:
        """Initialize clipboard manager."""
        self.paste_delay = paste_delay
        self.auto_paste = auto_paste
        self._last_owned_text: str | None = None
        self._paste_controller = ClipboardPasteController()
        self._keyboard_controller = self._paste_controller.keyboard_controller
        self._paste_modifier = self._paste_controller.paste_modifier

    def _build_paste_attempts(self) -> list[tuple[str, Callable[[], bool]]]:
        """Build the ordered list of paste methods for the current platform."""
        attempts: list[tuple[str, Callable[[], bool]]] = []

        if sys.platform == "win32":
            attempts.append(("native Ctrl+V", send_windows_paste_shortcut))

        attempts.append(
            ("controller Ctrl+V", self._paste_controller.send_paste_shortcut)
        )

        if sys.platform == "win32":
            attempts.extend(
                [
                    ("native Shift+Insert", send_windows_shift_insert_shortcut),
                    (
                        "PyAutoGUI Ctrl+V",
                        lambda: send_pyautogui_shortcut("ctrl", "v"),
                    ),
                    (
                        "PyAutoGUI Shift+Insert",
                        lambda: send_pyautogui_shortcut("shift", "insert"),
                    ),
                ]
            )
        return attempts

    def _auto_paste_clipboard(self) -> PasteAttemptResult:
        """Send the platform-specific paste shortcut for the current clipboard."""
        attempted_methods: list[str] = []

        for method, callback in self._build_paste_attempts():
            attempted_methods.append(method)
            try:
                if not callback():
                    continue
            except Exception:
                logger.warning("Auto-paste via %s failed.", method, exc_info=True)
                continue

            logger.info("Text auto-pasted via %s", method)
            return PasteAttemptResult(succeeded=True, method=method)

        failed_method = attempted_methods[-1] if attempted_methods else "unavailable"
        logger.warning(
            "Auto-paste failed after trying %s. The transcription is still "
            "available in the clipboard.",
            ", ".join(attempted_methods),
        )
        return PasteAttemptResult(succeeded=False, method=failed_method)

    def copy_and_paste(self, text: str) -> PasteAttemptResult | None:
        """Copy text to clipboard and optionally auto-paste."""
        pyperclip.copy(text)
        self._last_owned_text = text
        logger.info("Text copied to clipboard")

        if not self.auto_paste:
            return None

        time.sleep(self.paste_delay)
        if sys.platform == "win32":
            # Let the record-hotkey release settle before we inject Ctrl+V.
            time.sleep(_WINDOWS_HOTKEY_RELEASE_DELAY_SECONDS)
        time.sleep(0.05)
        return self._auto_paste_clipboard()

    def owns_clipboard(self) -> bool:
        """Return whether WhisperTray still owns the active clipboard text."""
        if self._last_owned_text is None:
            return False

        try:
            return bool(pyperclip.paste() == self._last_owned_text)
        except pyperclip.PyperclipException:
            logger.debug("Clipboard ownership check failed", exc_info=True)
            return False

    def toggle_auto_paste(self) -> bool:
        """Toggle auto-paste setting."""
        self.auto_paste = not self.auto_paste
        status = "enabled" if self.auto_paste else "disabled"
        logger.info("Auto-paste %s", status)
        return self.auto_paste
