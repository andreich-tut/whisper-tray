"""
Tray menu management module.

Handles the context menu for the system tray icon.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from whisper_tray.types import TrayIcon as PystrayIcon
from whisper_tray.types import TrayMenu as PystrayMenu
from whisper_tray.types import TrayMenuItem as PystrayMenuItem

logger = logging.getLogger(__name__)


class TrayMenu:
    """Manages the system tray context menu."""

    OVERLAY_POSITIONS = (
        ("top-left", "Top Left"),
        ("top-right", "Top Right"),
        ("bottom-left", "Bottom Left"),
        ("bottom-right", "Bottom Right"),
    )
    OVERLAY_AUTO_HIDE_OPTIONS = (
        (0.0, "Stay Visible"),
        (1.5, "1.5 Seconds"),
        (3.0, "3 Seconds"),
        (5.0, "5 Seconds"),
    )
    OVERLAY_SCREENS = (
        ("primary", "Primary Display"),
        ("cursor", "Cursor Display"),
    )
    OVERLAY_DENSITIES = (
        ("detailed", "Detailed"),
        ("compact", "Compact"),
    )

    def __init__(
        self,
        on_toggle_auto_paste: Optional[Callable] = None,
        on_set_language_en: Optional[Callable] = None,
        on_set_language_ru: Optional[Callable] = None,
        on_set_language_auto: Optional[Callable] = None,
        on_toggle_overlay: Optional[Callable] = None,
        on_set_overlay_position: Optional[Callable] = None,
        on_set_overlay_screen: Optional[Callable] = None,
        on_set_overlay_auto_hide: Optional[Callable] = None,
        on_set_overlay_density: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
        get_auto_paste_state: Optional[Callable[[], bool]] = None,
        get_language_state: Optional[Callable[[], str]] = None,
        get_overlay_enabled_state: Optional[Callable[[], bool]] = None,
        get_overlay_position_state: Optional[Callable[[], str]] = None,
        get_overlay_screen_state: Optional[Callable[[], str]] = None,
        get_overlay_auto_hide_state: Optional[Callable[[], float]] = None,
        get_overlay_density_state: Optional[Callable[[], str]] = None,
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

    def _wrap_callback(self, callback: Optional[Callable]) -> Callable:
        """Wrap callback to handle pystray's signature requirements."""

        def wrapped(icon: PystrayIcon, item: PystrayMenuItem) -> None:
            if callback:
                callback(icon, item)

        return wrapped

    def _wrap_overlay_position_callback(self, position: str) -> Callable:
        """Wrap an overlay position callback with the selected corner."""

        def wrapped(icon: PystrayIcon, item: PystrayMenuItem) -> None:
            if self._on_set_overlay_position:
                self._on_set_overlay_position(position, icon, item)

        return wrapped

    def _wrap_overlay_auto_hide_callback(self, seconds: float) -> Callable:
        """Wrap an overlay auto-hide callback with the selected timeout."""

        def wrapped(icon: PystrayIcon, item: PystrayMenuItem) -> None:
            if self._on_set_overlay_auto_hide:
                self._on_set_overlay_auto_hide(seconds, icon, item)

        return wrapped

    def _wrap_overlay_screen_callback(self, screen: str) -> Callable:
        """Wrap an overlay screen callback with the selected display target."""

        def wrapped(icon: PystrayIcon, item: PystrayMenuItem) -> None:
            if self._on_set_overlay_screen:
                self._on_set_overlay_screen(screen, icon, item)

        return wrapped

    def _wrap_overlay_density_callback(self, density: str) -> Callable:
        """Wrap an overlay density callback with the selected view mode."""

        def wrapped(icon: PystrayIcon, item: PystrayMenuItem) -> None:
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

    def _qt_overlay_position_checked(self, position: str) -> Callable[[], bool]:
        """Build a Qt-friendly checked callback for the selected corner."""

        def checked() -> bool:
            return self._get_overlay_position_checked(position)

        return checked

    def _qt_overlay_auto_hide_checked(self, seconds: float) -> Callable[[], bool]:
        """Build a Qt-friendly checked callback for the selected timeout."""

        def checked() -> bool:
            return self._get_overlay_auto_hide_checked(seconds)

        return checked

    def _qt_overlay_screen_checked(self, screen: str) -> Callable[[], bool]:
        """Build a Qt-friendly checked callback for the selected display."""

        def checked() -> bool:
            return self._get_overlay_screen_checked(screen)

        return checked

    def _qt_overlay_density_checked(self, density: str) -> Callable[[], bool]:
        """Build a Qt-friendly checked callback for the selected density."""

        def checked() -> bool:
            return self._get_overlay_density_checked(density)

        return checked

    def create_menu(self) -> PystrayMenu:
        """
        Create tray icon context menu.

        Returns:
            pystray.Menu instance with all menu items
        """
        import pystray

        # Create language submenu items
        language_menu = pystray.Menu(
            pystray.MenuItem(
                "English",
                self._wrap_callback(self._on_set_language_en),
                checked=lambda _: self._get_language_checked("en"),
                radio=True,
            ),
            pystray.MenuItem(
                "Russian",
                self._wrap_callback(self._on_set_language_ru),
                checked=lambda _: self._get_language_checked("ru"),
                radio=True,
            ),
            pystray.MenuItem(
                "Auto-Detect",
                self._wrap_callback(self._on_set_language_auto),
                checked=lambda _: self._get_language_checked("auto"),
                radio=True,
            ),
        )
        overlay_position_menu = pystray.Menu(
            *(
                pystray.MenuItem(
                    label,
                    self._wrap_overlay_position_callback(position),
                    checked=lambda _, value=position: (
                        self._get_overlay_position_checked(value)
                    ),
                    radio=True,
                )
                for position, label in self.OVERLAY_POSITIONS
            )
        )
        overlay_auto_hide_menu = pystray.Menu(
            *(
                pystray.MenuItem(
                    label,
                    self._wrap_overlay_auto_hide_callback(seconds),
                    checked=lambda _, value=seconds: (
                        self._get_overlay_auto_hide_checked(value)
                    ),
                    radio=True,
                )
                for seconds, label in self.OVERLAY_AUTO_HIDE_OPTIONS
            )
        )
        overlay_screen_menu = pystray.Menu(
            *(
                pystray.MenuItem(
                    label,
                    self._wrap_overlay_screen_callback(screen),
                    checked=lambda _, value=screen: self._get_overlay_screen_checked(
                        value
                    ),
                    radio=True,
                )
                for screen, label in self.OVERLAY_SCREENS
            )
        )
        overlay_density_menu = pystray.Menu(
            *(
                pystray.MenuItem(
                    label,
                    self._wrap_overlay_density_callback(density),
                    checked=lambda _, value=density: self._get_overlay_density_checked(
                        value
                    ),
                    radio=True,
                )
                for density, label in self.OVERLAY_DENSITIES
            )
        )
        overlay_menu = pystray.Menu(
            pystray.MenuItem(
                "Enabled",
                self._wrap_callback(self._on_toggle_overlay),
                checked=lambda _: self._get_overlay_enabled_state(),
            ),
            pystray.MenuItem("Position", overlay_position_menu),
            pystray.MenuItem("Display", overlay_screen_menu),
            pystray.MenuItem("Ready Auto-Hide", overlay_auto_hide_menu),
            pystray.MenuItem("View", overlay_density_menu),
        )

        return pystray.Menu(
            pystray.MenuItem("Language", language_menu),
            pystray.MenuItem(
                "Toggle Auto-Paste",
                self._wrap_callback(self._on_toggle_auto_paste),
                checked=lambda _: self._get_auto_paste_state(),
            ),
            pystray.MenuItem("Overlay", overlay_menu),
            pystray.MenuItem("Exit", self._wrap_callback(self._on_exit)),
        )

    def create_qt_menu(self, icon: object) -> Any:
        """
        Create a Qt tray menu with the same behavior as the pystray menu.

        Args:
            icon: Tray handle passed back into action callbacks

        Returns:
            QMenu instance with dynamic checked-state refresh support
        """
        from PySide6.QtGui import QActionGroup
        from PySide6.QtWidgets import QMenu

        root_menu = QMenu()
        action_groups: list[Any] = []

        language_menu = root_menu.addMenu("Language")
        language_group = QActionGroup(language_menu)
        language_group.setExclusive(True)
        action_groups.append(language_group)
        self._add_qt_action(
            language_menu,
            "English",
            self._wrap_callback(self._on_set_language_en),
            checked=lambda: self._get_language_checked("en"),
            icon=icon,
            action_group=language_group,
        )
        self._add_qt_action(
            language_menu,
            "Russian",
            self._wrap_callback(self._on_set_language_ru),
            checked=lambda: self._get_language_checked("ru"),
            icon=icon,
            action_group=language_group,
        )
        self._add_qt_action(
            language_menu,
            "Auto-Detect",
            self._wrap_callback(self._on_set_language_auto),
            checked=lambda: self._get_language_checked("auto"),
            icon=icon,
            action_group=language_group,
        )

        self._add_qt_action(
            root_menu,
            "Toggle Auto-Paste",
            self._wrap_callback(self._on_toggle_auto_paste),
            checked=self._get_auto_paste_state,
            icon=icon,
        )

        overlay_menu = root_menu.addMenu("Overlay")
        self._add_qt_action(
            overlay_menu,
            "Enabled",
            self._wrap_callback(self._on_toggle_overlay),
            checked=self._get_overlay_enabled_state,
            icon=icon,
        )

        overlay_position_menu = overlay_menu.addMenu("Position")
        overlay_position_group = QActionGroup(overlay_position_menu)
        overlay_position_group.setExclusive(True)
        action_groups.append(overlay_position_group)
        for position, label in self.OVERLAY_POSITIONS:
            self._add_qt_action(
                overlay_position_menu,
                label,
                self._wrap_overlay_position_callback(position),
                checked=self._qt_overlay_position_checked(position),
                icon=icon,
                action_group=overlay_position_group,
            )

        overlay_screen_menu = overlay_menu.addMenu("Display")
        overlay_screen_group = QActionGroup(overlay_screen_menu)
        overlay_screen_group.setExclusive(True)
        action_groups.append(overlay_screen_group)
        for screen, label in self.OVERLAY_SCREENS:
            self._add_qt_action(
                overlay_screen_menu,
                label,
                self._wrap_overlay_screen_callback(screen),
                checked=self._qt_overlay_screen_checked(screen),
                icon=icon,
                action_group=overlay_screen_group,
            )

        overlay_auto_hide_menu = overlay_menu.addMenu("Ready Auto-Hide")
        overlay_auto_hide_group = QActionGroup(overlay_auto_hide_menu)
        overlay_auto_hide_group.setExclusive(True)
        action_groups.append(overlay_auto_hide_group)
        for seconds, label in self.OVERLAY_AUTO_HIDE_OPTIONS:
            self._add_qt_action(
                overlay_auto_hide_menu,
                label,
                self._wrap_overlay_auto_hide_callback(seconds),
                checked=self._qt_overlay_auto_hide_checked(seconds),
                icon=icon,
                action_group=overlay_auto_hide_group,
            )

        overlay_density_menu = overlay_menu.addMenu("View")
        overlay_density_group = QActionGroup(overlay_density_menu)
        overlay_density_group.setExclusive(True)
        action_groups.append(overlay_density_group)
        for density, label in self.OVERLAY_DENSITIES:
            self._add_qt_action(
                overlay_density_menu,
                label,
                self._wrap_overlay_density_callback(density),
                checked=self._qt_overlay_density_checked(density),
                icon=icon,
                action_group=overlay_density_group,
            )

        self._add_qt_action(
            root_menu,
            "Exit",
            self._wrap_callback(self._on_exit),
            icon=icon,
        )

        def sync_menu(menu: Any) -> None:
            for action in menu.actions():
                checked = getattr(action, "_checked_callback", None)
                if callable(checked):
                    action.setChecked(bool(checked()))
                submenu = action.menu()
                if submenu is not None:
                    sync_menu(submenu)

        def sync_callback() -> None:
            sync_menu(root_menu)

        setattr(root_menu, "_sync_checkmarks", sync_callback)
        setattr(root_menu, "_action_groups", action_groups)
        root_menu.aboutToShow.connect(sync_callback)
        return root_menu

    @staticmethod
    def _add_qt_action(
        menu: Any,
        label: str,
        callback: Callable,
        *,
        checked: Callable[[], bool] | None = None,
        icon: object,
        action_group: Any | None = None,
    ) -> Any:
        """Add a Qt action and keep its checked state refreshable."""
        action = menu.addAction(label)
        if checked is not None:
            action.setCheckable(True)
            action.setChecked(bool(checked()))
            setattr(action, "_checked_callback", checked)
        if action_group is not None:
            action_group.addAction(action)
        action.triggered.connect(lambda _=False: callback(icon, None))
        return action
