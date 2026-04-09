"""
Clipboard and paste operations module.

Handles copying text to clipboard and simulating paste keyboard shortcuts.
Cross-platform: uses Cmd+V on macOS, Ctrl+V elsewhere.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator

import pyperclip

try:
    from pynput.keyboard import Controller as KeyboardController
    from pynput.keyboard import Key

    _PYNPUT_IMPORT_ERROR: Exception | None = None
except ImportError as exc:
    KeyboardController = None
    Key = None
    _PYNPUT_IMPORT_ERROR = exc

logger = logging.getLogger(__name__)

_WINDOWS_HOTKEY_RELEASE_DELAY_SECONDS = 0.15
_WINDOWS_KEYBOARD_INPUT = 1
_WINDOWS_KEYEVENTF_KEYUP = 0x0002
_WINDOWS_VK_CONTROL = 0x11
_WINDOWS_VK_SHIFT = 0x10
_WINDOWS_VK_INSERT = 0x2D
_WINDOWS_VK_V = 0x56


@dataclass(frozen=True)
class PasteAttemptResult:
    """Result of trying to paste the latest clipboard contents."""

    succeeded: bool
    method: str


def _send_windows_shortcut(*virtual_keys: int) -> bool:
    """Send a key chord with Win32 SendInput when it is available."""
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return False

    user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
    if user32 is None:
        return False

    ulong_ptr = ctypes.c_size_t

    class KeybdInput(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ulong_ptr),
        ]

    class InputUnion(ctypes.Union):
        _fields_ = [("ki", KeybdInput)]

    class Input(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("value", InputUnion),
        ]

    user32.SendInput.argtypes = (
        wintypes.UINT,
        ctypes.POINTER(Input),
        ctypes.c_int,
    )
    user32.SendInput.restype = wintypes.UINT

    def make_input(virtual_key: int, *, key_up: bool = False) -> Input:
        return Input(
            type=_WINDOWS_KEYBOARD_INPUT,
            ki=KeybdInput(
                wVk=virtual_key,
                wScan=0,
                dwFlags=_WINDOWS_KEYEVENTF_KEYUP if key_up else 0,
                time=0,
                dwExtraInfo=ulong_ptr(),
            ),
        )

    if not virtual_keys:
        return False

    events = [make_input(key) for key in virtual_keys]
    events.extend(make_input(key, key_up=True) for key in reversed(virtual_keys))
    inputs = (Input * len(events))(*events)
    input_pointer = ctypes.cast(inputs, ctypes.POINTER(Input))

    try:
        sent = int(
            user32.SendInput(
                len(inputs),
                input_pointer,
                ctypes.sizeof(Input),
            )
        )
    except Exception:
        logger.warning(
            "Failed to inject the native Windows shortcut.",
            exc_info=True,
        )
        return False

    if sent != len(inputs):
        logger.warning(
            "Native Windows shortcut injected %s/%s events.",
            sent,
            len(inputs),
        )
        return False

    return True


def _send_windows_paste_shortcut() -> bool:
    """Paste with a native Win32 Ctrl+V injection when available."""
    return _send_windows_shortcut(_WINDOWS_VK_CONTROL, _WINDOWS_VK_V)


def _send_windows_shift_insert_shortcut() -> bool:
    """Paste with a native Win32 Shift+Insert injection when available."""
    return _send_windows_shortcut(_WINDOWS_VK_SHIFT, _WINDOWS_VK_INSERT)


def _send_pyautogui_shortcut(*keys: str) -> bool:
    """Fallback to PyAutoGUI when lower-level keyboard backends refuse to cooperate."""
    try:
        import pyautogui
    except Exception:
        return False

    try:
        pyautogui.hotkey(*keys)
    except Exception:
        logger.warning(
            "PyAutoGUI auto-paste via %s failed.",
            "+".join(keys),
            exc_info=True,
        )
        return False

    return True


@dataclass(frozen=True)
class _FallbackKey:
    """Small stand-in for pynput keys when the backend is unavailable."""

    name: str


class _UnavailableKeyboardController:
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
        if KeyboardController is None or Key is None:
            self._keyboard_controller = _UnavailableKeyboardController()
            self._paste_modifier = (
                _FallbackKey("cmd")
                if sys.platform == "darwin"
                else _FallbackKey("ctrl")
            )
            return

        self._keyboard_controller = KeyboardController()
        # Platform-aware paste modifier: Cmd on macOS, Ctrl elsewhere
        self._paste_modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl

    def _send_controller_paste_shortcut(self) -> bool:
        """Use pynput's controller as the cross-platform default shortcut path."""
        try:
            with self._keyboard_controller.pressed(self._paste_modifier):
                self._keyboard_controller.press("v")
                self._keyboard_controller.release("v")
        except Exception:
            return False
        return True

    def _auto_paste_clipboard(self) -> PasteAttemptResult:
        """Send the platform-specific paste shortcut for the current clipboard."""
        attempts: list[tuple[str, Callable[[], bool]]] = []

        if sys.platform == "win32":
            attempts.append(("native Ctrl+V", _send_windows_paste_shortcut))

        attempts.append(("controller Ctrl+V", self._send_controller_paste_shortcut))

        if sys.platform == "win32":
            attempts.extend(
                [
                    ("native Shift+Insert", _send_windows_shift_insert_shortcut),
                    (
                        "PyAutoGUI Ctrl+V",
                        lambda: _send_pyautogui_shortcut("ctrl", "v"),
                    ),
                    (
                        "PyAutoGUI Shift+Insert",
                        lambda: _send_pyautogui_shortcut("shift", "insert"),
                    ),
                ]
            )

        attempted_methods: list[str] = []
        for method, callback in attempts:
            attempted_methods.append(method)
            try:
                if not callback():
                    continue
            except Exception:
                logger.warning("Auto-paste via %s failed.", method, exc_info=True)
                continue

            logger.info("Text auto-pasted via %s", method)
            return PasteAttemptResult(succeeded=True, method=method)

        logger.warning(
            "Auto-paste failed after trying %s. The transcription is still "
            "available in the clipboard.",
            ", ".join(attempted_methods),
        )
        return PasteAttemptResult(succeeded=False, method=attempted_methods[-1])

    def copy_and_paste(self, text: str) -> PasteAttemptResult | None:
        """
        Copy text to clipboard and optionally auto-paste.

        Args:
            text: Text to copy and paste
        """
        # Copy to clipboard
        pyperclip.copy(text)
        logger.info("Text copied to clipboard")

        # Auto-paste if enabled
        if not self.auto_paste:
            return None

        time.sleep(self.paste_delay)
        if sys.platform == "win32":
            # Let the record-hotkey release settle before we inject Ctrl+V.
            time.sleep(_WINDOWS_HOTKEY_RELEASE_DELAY_SECONDS)
        # Micro-sleep for clipboard registration
        time.sleep(0.05)
        return self._auto_paste_clipboard()

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
