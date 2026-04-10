"""High-level tray menu facade with backend-specific renderers."""

from __future__ import annotations

from typing import Any, Callable

from whisper_tray.core.tray_menu.callbacks import TrayMenuCallbacks
from whisper_tray.core.tray_menu.definition import build_menu_entries
from whisper_tray.core.tray_menu.model import MenuEntry
from whisper_tray.core.tray_menu.state import build_tray_menu_state
from whisper_tray.tray.menu_renderers import render_pystray_menu, render_qt_menu


class TrayMenu:
    """Manages the system tray context menu."""

    def __init__(
        self,
        on_toggle_auto_paste: Callable | None = None,
        on_set_language_en: Callable | None = None,
        on_set_language_ru: Callable | None = None,
        on_set_language_auto: Callable | None = None,
        on_toggle_overlay: Callable | None = None,
        on_set_overlay_position: Callable | None = None,
        on_set_overlay_screen: Callable | None = None,
        on_set_overlay_auto_hide: Callable | None = None,
        on_set_overlay_density: Callable | None = None,
        on_exit: Callable | None = None,
        get_auto_paste_state: Callable[[], bool] | None = None,
        get_language_state: Callable[[], str] | None = None,
        get_overlay_enabled_state: Callable[[], bool] | None = None,
        get_overlay_position_state: Callable[[], str] | None = None,
        get_overlay_screen_state: Callable[[], str] | None = None,
        get_overlay_auto_hide_state: Callable[[], float] | None = None,
        get_overlay_density_state: Callable[[], str] | None = None,
    ) -> None:
        self._callbacks = TrayMenuCallbacks(
            on_toggle_auto_paste=on_toggle_auto_paste,
            on_set_language_en=on_set_language_en,
            on_set_language_ru=on_set_language_ru,
            on_set_language_auto=on_set_language_auto,
            on_toggle_overlay=on_toggle_overlay,
            on_set_overlay_position=on_set_overlay_position,
            on_set_overlay_screen=on_set_overlay_screen,
            on_set_overlay_auto_hide=on_set_overlay_auto_hide,
            on_set_overlay_density=on_set_overlay_density,
            on_exit=on_exit,
        )
        self._state = build_tray_menu_state(
            get_auto_paste_state=get_auto_paste_state,
            get_language_state=get_language_state,
            get_overlay_enabled_state=get_overlay_enabled_state,
            get_overlay_position_state=get_overlay_position_state,
            get_overlay_screen_state=get_overlay_screen_state,
            get_overlay_auto_hide_state=get_overlay_auto_hide_state,
            get_overlay_density_state=get_overlay_density_state,
        )

    def _build_menu_entries(self) -> tuple[MenuEntry, ...]:
        """Build the shared tray menu structure for all backends."""
        return build_menu_entries(
            callbacks=self._callbacks,
            state=self._state,
        )

    def create_menu(self) -> Any:
        """Create the pystray tray icon context menu."""
        return render_pystray_menu(self._build_menu_entries())

    def create_qt_menu(self, icon: object) -> Any:
        """Create a Qt tray menu with refreshable checked-state callbacks."""
        return render_qt_menu(self._build_menu_entries(), icon)
