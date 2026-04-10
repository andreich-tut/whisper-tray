"""Qt-backed tray runtime implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_tray.adapters.tray.qt.overlay_host import QtOverlayHost
from whisper_tray.adapters.tray.qt.tray_handle import QtTrayIconHandle
from whisper_tray.overlay import OverlayController
from whisper_tray.overlay.controller import OverlaySettings
from whisper_tray.platform.windows.overlay_styles import (
    enable_windows_per_monitor_dpi_awareness,
)

if TYPE_CHECKING:
    from whisper_tray.app import WhisperTrayApp


class QtTrayRuntime:
    """Qt-based tray runtime that shares one QApplication with the overlay."""

    def __init__(self) -> None:
        self._app: Any | None = None
        self._tray_icon: Any | None = None
        self._overlay_host: QtOverlayHost | None = None

    def prepare(self, app: "WhisperTrayApp") -> None:
        """Create the Qt application, tray icon, menu, and overlay host."""
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon

        enable_windows_per_monitor_dpi_awareness()
        self._app = QApplication.instance() or QApplication([])
        if hasattr(self._app, "setQuitOnLastWindowClosed"):
            self._app.setQuitOnLastWindowClosed(False)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            raise RuntimeError("Qt system tray is unavailable on this desktop session.")

        tray_icon = QSystemTrayIcon()
        tray_handle = QtTrayIconHandle(tray_icon)
        menu = app._setup_tray_menu()
        qt_menu = menu.create_qt_menu(tray_handle)
        tray_handle.attach_menu(qt_menu)
        tray_icon.setContextMenu(qt_menu)

        icon_image = app._tray_icon.get_icon_image_for_state(
            app._state_presentation.state,
            flash_on=app._processing_flash_on,
        )
        tray_handle.icon = icon_image
        tray_handle.title = app._get_tray_title()
        tray_icon.show()

        self._tray_icon = tray_icon
        self._overlay_host = QtOverlayHost()
        app._tray_icon_ref = tray_handle

    def run(self) -> None:
        """Enter the Qt event loop until the tray handle requests shutdown."""
        if self._app is None:
            raise RuntimeError("Qt runtime has not been prepared.")

        try:
            self._app.exec()
        finally:
            if self._tray_icon is not None:
                self._tray_icon.hide()
            if self._overlay_host is not None:
                self._overlay_host.close()

    def create_overlay_controller(
        self,
        settings: OverlaySettings,
    ) -> OverlayController:
        """Create a main-thread overlay controller on the shared Qt runtime."""
        if self._overlay_host is None:
            raise RuntimeError("Qt runtime has not been prepared.")
        return self._overlay_host.create_controller(settings)
