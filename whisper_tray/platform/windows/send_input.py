"""Native Windows paste helpers."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_WINDOWS_KEYBOARD_INPUT = 1
_WINDOWS_KEYEVENTF_KEYUP = 0x0002
_WINDOWS_VK_CONTROL = 0x11
_WINDOWS_VK_SHIFT = 0x10
_WINDOWS_VK_INSERT = 0x2D
_WINDOWS_VK_V = 0x56


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


def send_windows_paste_shortcut() -> bool:
    """Paste with a native Win32 Ctrl+V injection when available."""
    return _send_windows_shortcut(_WINDOWS_VK_CONTROL, _WINDOWS_VK_V)


def send_windows_shift_insert_shortcut() -> bool:
    """Paste with a native Win32 Shift+Insert injection when available."""
    return _send_windows_shortcut(_WINDOWS_VK_SHIFT, _WINDOWS_VK_INSERT)
