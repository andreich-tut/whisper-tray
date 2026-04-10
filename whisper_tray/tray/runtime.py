"""Tray runtime backends for pystray and Qt."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from whisper_tray.overlay import NullOverlayController, OverlayController
from whisper_tray.overlay.controller import (
    OverlaySettings,
    _pyside6_is_available,
    create_overlay_controller,
)

if TYPE_CHECKING:
    from whisper_tray.app import WhisperTrayApp

logger = logging.getLogger(__name__)


class TrayRuntime(Protocol):
    """Backend interface for tray event-loop implementations."""

    def prepare(self, app: "WhisperTrayApp") -> None:
        """Create tray resources before the app starts background work."""

    def run(self) -> None:
        """Enter the backend event loop and block until exit."""

    def create_overlay_controller(
        self,
        settings: OverlaySettings,
    ) -> OverlayController:
        """Create an overlay controller compatible with this tray runtime."""


def should_use_qt_tray() -> bool:
    """Return whether the optional Qt tray runtime is available."""
    return _pyside6_is_available()


class PystrayTrayRuntime:
    """Existing pystray-based tray runtime."""

    def __init__(self) -> None:
        self._icon: Any | None = None

    def prepare(self, app: "WhisperTrayApp") -> None:
        """Create the tray icon and menu before the pystray loop starts."""
        import pystray

        icon_image = app._tray_icon.get_icon_image_for_state(
            app._state_presentation.state,
            flash_on=app._processing_flash_on,
        )
        tray_title = app._get_tray_title()
        menu = app._setup_tray_menu()
        self._icon = pystray.Icon(
            "WhisperTray",
            icon_image,
            tray_title,
            menu.create_menu(),
        )
        app._tray_icon_ref = self._icon

    def run(self) -> None:
        """Block on the pystray event loop."""
        if self._icon is None:
            raise RuntimeError("Pystray runtime has not been prepared.")
        self._icon.run()

    def create_overlay_controller(
        self,
        settings: OverlaySettings,
    ) -> OverlayController:
        """Create the threaded overlay used by the legacy pystray runtime."""
        return create_overlay_controller(settings)


def _pil_image_to_qicon(image: Any) -> Any:
    """Convert a PIL image into a QIcon without importing Qt at module load."""
    from PySide6.QtGui import QIcon, QImage, QPixmap

    rgba = image.convert("RGBA")
    buffer = rgba.tobytes("raw", "RGBA")
    image_format = (
        QImage.Format.Format_RGBA8888
        if hasattr(QImage, "Format")
        else getattr(QImage, "Format_RGBA8888")
    )
    qimage = QImage(buffer, rgba.width, rgba.height, image_format).copy()
    return QIcon(QPixmap.fromImage(qimage))


class QtTrayIconHandle:
    """Thread-safe tray handle that marshals updates onto the Qt UI thread."""

    def __init__(self, tray_icon: Any) -> None:
        from PySide6.QtCore import QObject, Signal
        from PySide6.QtWidgets import QApplication

        self._menu: Any | None = None
        self._title = ""

        class Bridge(QObject):
            set_icon = Signal(object)
            set_title = Signal(str)
            show_message = Signal(str)
            refresh_menu = Signal()
            stop_requested = Signal()

            def __init__(self, owner: "QtTrayIconHandle", qt_tray_icon: Any) -> None:
                super().__init__()
                self._owner = owner
                self._tray_icon = qt_tray_icon
                self.set_icon.connect(self._set_icon)
                self.set_title.connect(self._set_title)
                self.show_message.connect(self._show_message)
                self.refresh_menu.connect(self._refresh_menu)
                self.stop_requested.connect(self._stop_requested)

            def _set_icon(self, image: Any) -> None:
                self._tray_icon.setIcon(_pil_image_to_qicon(image))

            def _set_title(self, title: str) -> None:
                self._tray_icon.setToolTip(title)

            def _show_message(self, message: str) -> None:
                self._tray_icon.showMessage("WhisperTray", message)

            def _refresh_menu(self) -> None:
                menu = self._owner._menu
                sync = getattr(menu, "_sync_checkmarks", None)
                if callable(sync):
                    sync()

            @staticmethod
            def _stop_requested() -> None:
                app = QApplication.instance()
                if app is not None:
                    app.quit()

        self._bridge = Bridge(self, tray_icon)

    def attach_menu(self, menu: Any) -> None:
        """Attach the Qt menu after it is constructed."""
        self._menu = menu

    @property
    def icon(self) -> Any | None:
        """Expose the last icon value for API compatibility."""
        return None

    @icon.setter
    def icon(self, image: Any) -> None:
        """Update the tray icon image."""
        self._bridge.set_icon.emit(image)

    @property
    def title(self) -> str:
        """Return the most recent tooltip text."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Update the tray tooltip text."""
        self._title = value
        self._bridge.set_title.emit(value)

    def notify(self, message: str) -> None:
        """Show a native Qt tray notification."""
        self._bridge.show_message.emit(message)

    def update_menu(self) -> None:
        """Refresh dynamic menu checkmarks."""
        self._bridge.refresh_menu.emit()

    def stop(self) -> None:
        """Request shutdown of the Qt event loop."""
        self._bridge.stop_requested.emit()


class QtOverlayController:
    """Main-thread overlay controller that reuses the shared Qt app runtime."""

    def __init__(
        self,
        bridge: Any,
        *,
        settings: OverlaySettings,
    ) -> None:
        self._bridge = bridge
        self._settings = settings
        self._closed = False
        self._bridge.configure.emit(
            settings.enabled,
            settings.position,
            settings.screen_target,
        )

    def show_state(self, presentation: Any) -> None:
        """Render the latest presentation on the shared overlay window."""
        if self._closed or not self._settings.enabled:
            return
        self._bridge.configure.emit(
            True,
            self._settings.position,
            self._settings.screen_target,
        )
        self._bridge.show_presentation.emit(presentation)

    def close(self) -> None:
        """Hide the shared overlay window for this controller instance."""
        if self._closed:
            return
        self._closed = True
        self._bridge.hide_overlay.emit()


class QtOverlayHost:
    """Shared overlay host that lives on the same Qt event loop as the tray."""

    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal

        from whisper_tray.overlay.pyside_overlay import OverlayWindow

        window = OverlayWindow(
            position="bottom-right",
            screen_target="primary",
        )

        class Bridge(QObject):
            configure = Signal(bool, str, str)
            show_presentation = Signal(object)
            hide_overlay = Signal()
            close_window = Signal()

            def __init__(self, overlay_window: Any) -> None:
                super().__init__()
                self._enabled = False
                self._position = "bottom-right"
                self._screen_target = "primary"
                self._window = overlay_window
                self.configure.connect(self._configure)
                self.show_presentation.connect(self._show_presentation)
                self.hide_overlay.connect(self._hide_overlay)
                self.close_window.connect(self._close_window)

            def _configure(
                self,
                enabled: bool,
                position: str,
                screen_target: str,
            ) -> None:
                self._enabled = enabled
                self._position = position
                self._screen_target = screen_target
                self._window.update_anchor(position, screen_target)
                if not enabled:
                    self._window.hide_now()

            def _show_presentation(self, presentation: Any) -> None:
                if not self._enabled:
                    return
                self._window.update_anchor(self._position, self._screen_target)
                self._window.show_presentation(presentation)

            def _hide_overlay(self) -> None:
                self._window.hide_now()

            def _close_window(self) -> None:
                self._window.close()

        self._bridge = Bridge(window)

    def create_controller(
        self,
        settings: OverlaySettings,
    ) -> OverlayController:
        """Create a new controller facade for the shared overlay window."""
        if not settings.enabled:
            return NullOverlayController()
        return QtOverlayController(
            self._bridge,
            settings=settings,
        )

    def close(self) -> None:
        """Close the underlying overlay window."""
        self._bridge.close_window.emit()


class QtTrayRuntime:
    """Qt-based tray runtime that shares one QApplication with the overlay."""

    def __init__(self) -> None:
        self._app: Any | None = None
        self._tray_icon: Any | None = None
        self._overlay_host: QtOverlayHost | None = None

    def prepare(self, app: "WhisperTrayApp") -> None:
        """Create the Qt application, tray icon, menu, and overlay host."""
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon

        from whisper_tray.overlay.pyside_overlay import (
            enable_windows_per_monitor_dpi_awareness,
        )

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
