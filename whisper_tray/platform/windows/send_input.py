"""Win32 SendInput clipboard helper facade."""

from whisper_tray.clipboard.windows import (
    send_windows_paste_shortcut,
    send_windows_shift_insert_shortcut,
)

__all__ = [
    "send_windows_paste_shortcut",
    "send_windows_shift_insert_shortcut",
]
