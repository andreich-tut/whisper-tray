"""Qt tray handle that marshals updates onto the UI thread."""

from __future__ import annotations

from typing import Any

from whisper_tray.tray.qt_icon import pil_image_to_qicon


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
                self._tray_icon.setIcon(pil_image_to_qicon(image))

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
