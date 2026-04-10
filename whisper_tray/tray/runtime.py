"""Public tray runtime facade."""

from whisper_tray.tray.pystray_runtime import PystrayTrayRuntime
from whisper_tray.tray.qt_overlay_host import QtOverlayController, QtOverlayHost
from whisper_tray.tray.qt_runtime import QtTrayRuntime
from whisper_tray.tray.qt_tray_handle import QtTrayIconHandle
from whisper_tray.tray.runtime_protocol import TrayRuntime, should_use_qt_tray

__all__ = [
    "PystrayTrayRuntime",
    "QtOverlayController",
    "QtOverlayHost",
    "QtTrayIconHandle",
    "QtTrayRuntime",
    "TrayRuntime",
    "should_use_qt_tray",
]
