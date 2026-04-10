"""Native Windows paste helpers."""

from whisper_tray.platform.windows.send_input import (
    send_windows_paste_shortcut,
    send_windows_shift_insert_shortcut,
)

__all__ = [
    "send_windows_paste_shortcut",
    "send_windows_shift_insert_shortcut",
]
