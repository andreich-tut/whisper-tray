"""Backend-specific tray menu renderers."""

from whisper_tray.adapters.tray.renderers import render_pystray_menu, render_qt_menu

__all__ = [
    "render_pystray_menu",
    "render_qt_menu",
]
