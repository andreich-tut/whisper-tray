"""
Tray menu management module.

Handles the context menu for the system tray icon.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import pystray

from whisper_tray.types import TrayIcon as PystrayIcon
from whisper_tray.types import TrayMenuItem as PystrayMenuItem

logger = logging.getLogger(__name__)


class TrayMenu:
    """Manages the system tray context menu."""

    def __init__(
        self,
        on_toggle_auto_paste: Optional[Callable] = None,
        on_set_language_en: Optional[Callable] = None,
        on_set_language_ru: Optional[Callable] = None,
        on_set_language_auto: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
        get_auto_paste_state: Optional[Callable[[], bool]] = None,
        get_language_state: Optional[Callable[[], str]] = None,
    ) -> None:
        """
        Initialize tray menu.

        Args:
            on_toggle_auto_paste: Callback when auto-paste is toggled
            on_set_language_en: Callback when English is selected
            on_set_language_ru: Callback when Russian is selected
            on_set_language_auto: Callback when auto-detect is selected
            on_exit: Callback when exit is clicked
            get_auto_paste_state: Function to get current auto-paste state
            get_language_state: Function to get current language state
        """
        self._on_toggle_auto_paste = on_toggle_auto_paste
        self._on_set_language_en = on_set_language_en
        self._on_set_language_ru = on_set_language_ru
        self._on_set_language_auto = on_set_language_auto
        self._on_exit = on_exit
        self._get_auto_paste_state = get_auto_paste_state or (lambda: False)
        self._get_language_state = get_language_state or (lambda: "auto")

    def _wrap_callback(self, callback: Optional[Callable]) -> Callable:
        """Wrap callback to handle pystray's signature requirements."""

        def wrapped(icon: PystrayIcon, item: PystrayMenuItem) -> None:
            if callback:
                callback(icon, item)

        return wrapped

    def _get_language_checked(self, lang: str) -> bool:
        """Check if a language is currently selected."""
        return self._get_language_state() == lang

    def create_menu(self) -> pystray.Menu:
        """
        Create tray icon context menu.

        Returns:
            pystray.Menu instance with all menu items
        """
        # Create language submenu items
        language_menu = pystray.Menu(
            pystray.MenuItem(
                "English",
                self._wrap_callback(self._on_set_language_en),
                checked=lambda _: self._get_language_checked("en"),
            ),
            pystray.MenuItem(
                "Russian",
                self._wrap_callback(self._on_set_language_ru),
                checked=lambda _: self._get_language_checked("ru"),
            ),
            pystray.MenuItem(
                "Auto-Detect",
                self._wrap_callback(self._on_set_language_auto),
                checked=lambda _: self._get_language_checked("auto"),
            ),
        )

        return pystray.Menu(
            pystray.MenuItem("Language", language_menu),
            pystray.MenuItem(
                "Toggle Auto-Paste",
                self._wrap_callback(self._on_toggle_auto_paste),
                checked=lambda _: self._get_auto_paste_state(),
            ),
            pystray.MenuItem("Exit", self._wrap_callback(self._on_exit)),
        )
