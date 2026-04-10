"""Tray renderer adapter facade."""

from whisper_tray.tray.menu_renderers import render_pystray_menu, render_qt_menu

__all__ = [
    "render_pystray_menu",
    "render_qt_menu",
]
