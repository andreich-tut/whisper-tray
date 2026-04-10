"""Qt overlay host and controller implementations."""

from __future__ import annotations

from typing import Any

from whisper_tray.adapters.overlay.qt.runtime import OverlayWindow
from whisper_tray.core.overlay import (
    NullOverlayController,
    OverlayController,
    OverlaySettings,
)


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
