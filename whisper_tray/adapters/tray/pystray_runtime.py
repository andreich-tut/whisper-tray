"""Pystray-backed tray runtime implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_tray.overlay import OverlayController
from whisper_tray.overlay.controller import OverlaySettings, create_overlay_controller

if TYPE_CHECKING:
    from whisper_tray.app import WhisperTrayApp


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
