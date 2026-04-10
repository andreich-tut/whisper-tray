"""Internal protocols for backend integrations."""

from whisper_tray.core.protocols.backends import (
    ClipboardPasteBackend,
    HotkeyBackend,
    RecorderBackend,
    TranscriberBackend,
)
from whisper_tray.core.protocols.tray import TrayRuntime, should_use_qt_tray

__all__ = [
    "ClipboardPasteBackend",
    "HotkeyBackend",
    "RecorderBackend",
    "TranscriberBackend",
    "TrayRuntime",
    "should_use_qt_tray",
]
