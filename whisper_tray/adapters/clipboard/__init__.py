"""Clipboard adapter entry points."""

from whisper_tray.adapters.clipboard.core import ClipboardManager, PasteAttemptResult

__all__ = [
    "ClipboardManager",
    "PasteAttemptResult",
]
