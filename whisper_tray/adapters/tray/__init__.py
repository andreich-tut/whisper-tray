"""Tray adapter entry points."""

from whisper_tray.adapters.tray.menu import TrayMenu
from whisper_tray.adapters.tray.pystray_runtime import PystrayTrayRuntime
from whisper_tray.adapters.tray.qt.overlay_host import (
    QtOverlayController,
    QtOverlayHost,
)
from whisper_tray.adapters.tray.qt.runtime import QtTrayRuntime
from whisper_tray.adapters.tray.qt.tray_handle import QtTrayIconHandle
from whisper_tray.adapters.tray.renderers import render_pystray_menu, render_qt_menu
from whisper_tray.adapters.tray.runtime import TrayRuntime, should_use_qt_tray

__all__ = [
    "PystrayTrayRuntime",
    "QtOverlayController",
    "QtOverlayHost",
    "QtTrayIconHandle",
    "QtTrayRuntime",
    "TrayMenu",
    "TrayRuntime",
    "render_pystray_menu",
    "render_qt_menu",
    "should_use_qt_tray",
]
