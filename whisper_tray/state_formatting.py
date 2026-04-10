"""Compatibility facade for backend-neutral formatting helpers."""

from whisper_tray.core.presentation.formatting import (
    format_hotkey,
    format_transcript,
    truncate_line,
)

__all__ = [
    "format_hotkey",
    "format_transcript",
    "truncate_line",
]
