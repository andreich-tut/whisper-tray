"""Keyboard-controller paste helpers and safe fallbacks."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

try:
    from pynput.keyboard import Controller as KeyboardController
    from pynput.keyboard import Key

    _PYNPUT_IMPORT_ERROR: Exception | None = None
except ImportError as exc:
    KeyboardController = None
    Key = None
    _PYNPUT_IMPORT_ERROR = exc


@dataclass(frozen=True)
class FallbackKey:
    """Small stand-in for pynput keys when the backend is unavailable."""

    name: str


class UnavailableKeyboardController:
    """Keyboard controller placeholder for unsupported test environments."""

    @contextmanager
    def pressed(self, key: object) -> Iterator[None]:
        """Raise a clear runtime error when auto-paste is attempted."""
        raise RuntimeError(
            "pynput keyboard backend is unavailable. "
            "Auto-paste requires a supported desktop session."
        ) from _PYNPUT_IMPORT_ERROR
        yield

    def press(self, key: str) -> None:
        """Raise a clear runtime error when auto-paste is attempted."""
        raise RuntimeError(
            "pynput keyboard backend is unavailable. "
            "Auto-paste requires a supported desktop session."
        ) from _PYNPUT_IMPORT_ERROR

    def release(self, key: str) -> None:
        """Raise a clear runtime error when auto-paste is attempted."""
        raise RuntimeError(
            "pynput keyboard backend is unavailable. "
            "Auto-paste requires a supported desktop session."
        ) from _PYNPUT_IMPORT_ERROR


class ClipboardPasteController:
    """Pynput-backed paste injection with a safe unavailable fallback."""

    def __init__(self) -> None:
        if KeyboardController is None or Key is None:
            self.keyboard_controller = UnavailableKeyboardController()
            self.paste_modifier = (
                FallbackKey("cmd") if sys.platform == "darwin" else FallbackKey("ctrl")
            )
            return

        self.keyboard_controller = KeyboardController()
        self.paste_modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl

    def send_paste_shortcut(self) -> bool:
        """Use pynput's controller as the cross-platform default shortcut path."""
        try:
            with self.keyboard_controller.pressed(self.paste_modifier):
                self.keyboard_controller.press("v")
                self.keyboard_controller.release("v")
        except Exception:
            return False
        return True
