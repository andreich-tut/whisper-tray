"""High-level tray menu builder with backend-specific renderers."""

from __future__ import annotations

import logging
from typing import Any, Callable

from whisper_tray.tray.menu_model import (
    OVERLAY_AUTO_HIDE_OPTIONS,
    OVERLAY_DENSITIES,
    OVERLAY_POSITIONS,
    OVERLAY_SCREENS,
    MenuEntry,
)
from whisper_tray.tray.menu_renderers import render_pystray_menu, render_qt_menu

logger = logging.getLogger(__name__)


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
        """
        Initialize tray menu.

        Args:
            on_toggle_auto_paste: Callback when auto-paste is toggled
            on_set_language_en: Callback when English is selected
            on_set_language_ru: Callback when Russian is selected
            on_set_language_auto: Callback when auto-detect is selected
            on_toggle_overlay: Callback when overlay is toggled
            on_set_overlay_position: Callback when overlay position changes
            on_set_overlay_screen: Callback when overlay display changes
            on_set_overlay_auto_hide: Callback when overlay ready timeout changes
            on_set_overlay_density: Callback when overlay density changes
            on_exit: Callback when exit is clicked
            get_auto_paste_state: Function to get current auto-paste state
            get_language_state: Function to get current language state
            get_overlay_enabled_state: Function to get current overlay state
            get_overlay_position_state: Function to get current overlay position
            get_overlay_screen_state: Function to get current overlay display target
            get_overlay_auto_hide_state: Function to get current overlay ready timeout
            get_overlay_density_state: Function to get current overlay density
        """
        self._on_toggle_auto_paste = on_toggle_auto_paste
        self._on_set_language_en = on_set_language_en
        self._on_set_language_ru = on_set_language_ru
        self._on_set_language_auto = on_set_language_auto
        self._on_toggle_overlay = on_toggle_overlay
        self._on_set_overlay_position = on_set_overlay_position
        self._on_set_overlay_screen = on_set_overlay_screen
        self._on_set_overlay_auto_hide = on_set_overlay_auto_hide
        self._on_set_overlay_density = on_set_overlay_density
        self._on_exit = on_exit
        self._get_auto_paste_state = get_auto_paste_state or (lambda: False)
        self._get_language_state = get_language_state or (lambda: "auto")
        self._get_overlay_enabled_state = get_overlay_enabled_state or (lambda: False)
        self._get_overlay_position_state = get_overlay_position_state or (
            lambda: "bottom-right"
        )
        self._get_overlay_screen_state = get_overlay_screen_state or (lambda: "primary")
        self._get_overlay_auto_hide_state = get_overlay_auto_hide_state or (lambda: 1.5)
        self._get_overlay_density_state = get_overlay_density_state or (
            lambda: "detailed"
        )

    def _wrap_callback(
        self, callback: Callable | None
    ) -> Callable[[object, object], None]:
        """Wrap callbacks with a uniform `(icon, item)` signature."""

        def wrapped(icon: object, item: object) -> None:
            if callback:
                callback(icon, item)

        return wrapped

    def _wrap_overlay_position_callback(
        self,
        position: str,
    ) -> Callable[[object, object], None]:
        """Wrap an overlay position callback with the selected corner."""

        def wrapped(icon: object, item: object) -> None:
            if self._on_set_overlay_position:
                self._on_set_overlay_position(position, icon, item)

        return wrapped

    def _wrap_overlay_auto_hide_callback(
        self,
        seconds: float,
    ) -> Callable[[object, object], None]:
        """Wrap an overlay auto-hide callback with the selected timeout."""

        def wrapped(icon: object, item: object) -> None:
            if self._on_set_overlay_auto_hide:
                self._on_set_overlay_auto_hide(seconds, icon, item)

        return wrapped

    def _wrap_overlay_screen_callback(
        self,
        screen: str,
    ) -> Callable[[object, object], None]:
        """Wrap an overlay screen callback with the selected display target."""

        def wrapped(icon: object, item: object) -> None:
            if self._on_set_overlay_screen:
                self._on_set_overlay_screen(screen, icon, item)

        return wrapped

    def _wrap_overlay_density_callback(
        self,
        density: str,
    ) -> Callable[[object, object], None]:
        """Wrap an overlay density callback with the selected view mode."""

        def wrapped(icon: object, item: object) -> None:
            if self._on_set_overlay_density:
                self._on_set_overlay_density(density, icon, item)

        return wrapped

    def _get_language_checked(self, lang: str) -> bool:
        """Check if a language is currently selected."""
        return self._get_language_state() == lang

    def _get_overlay_position_checked(self, position: str) -> bool:
        """Check if an overlay corner is currently selected."""
        return self._get_overlay_position_state() == position

    def _get_overlay_auto_hide_checked(self, seconds: float) -> bool:
        """Check if an overlay ready timeout is currently selected."""
        return abs(self._get_overlay_auto_hide_state() - seconds) < 1e-9

    def _get_overlay_screen_checked(self, screen: str) -> bool:
        """Check if an overlay display target is currently selected."""
        return self._get_overlay_screen_state() == screen

    def _get_overlay_density_checked(self, density: str) -> bool:
        """Check if an overlay density is currently selected."""
        return self._get_overlay_density_state() == density

    def _overlay_position_checked_callback(self, position: str) -> Callable[[], bool]:
        """Build a checked-state callback for an overlay position option."""

        def checked() -> bool:
            return self._get_overlay_position_checked(position)

        return checked

    def _overlay_screen_checked_callback(self, screen: str) -> Callable[[], bool]:
        """Build a checked-state callback for an overlay screen option."""

        def checked() -> bool:
            return self._get_overlay_screen_checked(screen)

        return checked

    def _overlay_auto_hide_checked_callback(self, seconds: float) -> Callable[[], bool]:
        """Build a checked-state callback for an auto-hide option."""

        def checked() -> bool:
            return self._get_overlay_auto_hide_checked(seconds)

        return checked

    def _overlay_density_checked_callback(self, density: str) -> Callable[[], bool]:
        """Build a checked-state callback for an overlay density option."""

        def checked() -> bool:
            return self._get_overlay_density_checked(density)

        return checked

    def _build_menu_entries(self) -> tuple[MenuEntry, ...]:
        """Build the shared tray menu structure for all backends."""
        return (
            MenuEntry(
                label="Language",
                children=(
                    MenuEntry(
                        label="English",
                        action=self._wrap_callback(self._on_set_language_en),
                        checked=lambda: self._get_language_checked("en"),
                        radio=True,
                    ),
                    MenuEntry(
                        label="Russian",
                        action=self._wrap_callback(self._on_set_language_ru),
                        checked=lambda: self._get_language_checked("ru"),
                        radio=True,
                    ),
                    MenuEntry(
                        label="Auto-Detect",
                        action=self._wrap_callback(self._on_set_language_auto),
                        checked=lambda: self._get_language_checked("auto"),
                        radio=True,
                    ),
                ),
            ),
            MenuEntry(
                label="Toggle Auto-Paste",
                action=self._wrap_callback(self._on_toggle_auto_paste),
                checked=self._get_auto_paste_state,
            ),
            MenuEntry(
                label="Overlay",
                children=(
                    MenuEntry(
                        label="Enabled",
                        action=self._wrap_callback(self._on_toggle_overlay),
                        checked=self._get_overlay_enabled_state,
                    ),
                    MenuEntry(
                        label="Position",
                        children=tuple(
                            MenuEntry(
                                label=label,
                                action=self._wrap_overlay_position_callback(position),
                                checked=self._overlay_position_checked_callback(
                                    position
                                ),
                                radio=True,
                            )
                            for position, label in OVERLAY_POSITIONS
                        ),
                    ),
                    MenuEntry(
                        label="Display",
                        children=tuple(
                            MenuEntry(
                                label=label,
                                action=self._wrap_overlay_screen_callback(screen),
                                checked=self._overlay_screen_checked_callback(screen),
                                radio=True,
                            )
                            for screen, label in OVERLAY_SCREENS
                        ),
                    ),
                    MenuEntry(
                        label="Ready Auto-Hide",
                        children=tuple(
                            MenuEntry(
                                label=label,
                                action=self._wrap_overlay_auto_hide_callback(seconds),
                                checked=self._overlay_auto_hide_checked_callback(
                                    seconds
                                ),
                                radio=True,
                            )
                            for seconds, label in OVERLAY_AUTO_HIDE_OPTIONS
                        ),
                    ),
                    MenuEntry(
                        label="View",
                        children=tuple(
                            MenuEntry(
                                label=label,
                                action=self._wrap_overlay_density_callback(density),
                                checked=self._overlay_density_checked_callback(density),
                                radio=True,
                            )
                            for density, label in OVERLAY_DENSITIES
                        ),
                    ),
                ),
            ),
            MenuEntry(
                label="Exit",
                action=self._wrap_callback(self._on_exit),
            ),
        )

    def create_menu(self) -> Any:
        """Create the pystray tray icon context menu."""
        return render_pystray_menu(self._build_menu_entries())

    def create_qt_menu(self, icon: object) -> Any:
        """Create a Qt tray menu with refreshable checked-state callbacks."""
        return render_qt_menu(self._build_menu_entries(), icon)
