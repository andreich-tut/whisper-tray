"""Compatibility facade for tray runtime protocols."""

from whisper_tray.core.protocols.tray import TrayRuntime, should_use_qt_tray

__all__ = [
    "TrayRuntime",
    "should_use_qt_tray",
]
