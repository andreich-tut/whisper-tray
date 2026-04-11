"""Tests for pystray and Qt tray menu model."""

from __future__ import annotations

import sys
from typing import Any, Callable

import pytest

from whisper_tray.adapters.tray.menu import TrayMenu


class FakeMenu(tuple):
    """Small tuple-backed pystray menu stand-in for tests."""

    def __new__(cls, *items: object) -> "FakeMenu":
        return super().__new__(cls, items)


class FakeMenuItem:
    """Minimal menu item object used to inspect labels and callbacks."""

    def __init__(
        self,
        text: str,
        action: object,
        checked: object | None = None,
        radio: bool = False,
    ) -> None:
        self.text = text
        self.action = action
        self.checked = checked
        self.radio = radio


class FakeQtSignal:
    """Minimal Qt-like signal used to test Qt tray menu wiring."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> None:
        """Record connected callbacks."""
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        """Invoke all registered callbacks."""
        for callback in self._callbacks:
            callback(*args)


class FakeQtActionGroup:
    """Small QActionGroup stand-in for menu exclusivity tests."""

    def __init__(self, parent: object) -> None:
        self.parent = parent
        self.actions: list[FakeQtAction] = []
        self.exclusive = False

    def addAction(self, action: "FakeQtAction") -> None:
        """Record actions registered with the group."""
        self.actions.append(action)

    def setExclusive(self, value: bool) -> None:
        """Record whether the group is exclusive."""
        self.exclusive = value


class FakeQtAction:
    """Small QAction stand-in for menu creation tests."""

    def __init__(self, text: str, submenu: "FakeQtMenu | None" = None) -> None:
        self._text = text
        self._submenu = submenu
        self._checked = False
        self._checkable = False
        self.triggered = FakeQtSignal()

    def text(self) -> str:
        """Return the visible label."""
        return self._text

    def menu(self) -> "FakeQtMenu | None":
        """Return the attached submenu when one exists."""
        return self._submenu

    def setCheckable(self, value: bool) -> None:
        """Record whether the action is checkable."""
        self._checkable = value

    def setChecked(self, value: bool) -> None:
        """Record the current checked state."""
        self._checked = value

    def isChecked(self) -> bool:
        """Expose the current checked state for assertions."""
        return self._checked


class FakeQtMenu:
    """Small QMenu stand-in for Qt tray menu tests."""

    def __init__(self, title: str = "") -> None:
        self._title = title
        self._actions: list[FakeQtAction] = []
        self.aboutToShow = FakeQtSignal()

    def addAction(self, label: str) -> FakeQtAction:
        """Append an action to the menu."""
        action = FakeQtAction(label)
        self._actions.append(action)
        return action

    def addMenu(self, label: str) -> "FakeQtMenu":
        """Append a submenu and return it."""
        submenu = FakeQtMenu(label)
        self._actions.append(FakeQtAction(label, submenu))
        return submenu

    def actions(self) -> list[FakeQtAction]:
        """Return the current actions in insertion order."""
        return self._actions


class StrictFakeIcon:
    """Minimal icon stub that only allows the pystray attributes we expect."""

    __slots__ = ("icon", "title", "notifications", "menu_updates")

    def __init__(self) -> None:
        self.icon = None
        self.title = ""
        self.notifications: list[str] = []
        self.menu_updates = 0

    def notify(self, message: str) -> None:
        """Record tray notifications instead of showing them."""
        self.notifications.append(message)

    def update_menu(self) -> None:
        """Record menu refresh requests."""
        self.menu_updates += 1


class TestTrayMenu:
    """Tests for tray menu model construction and state reflection."""

    def test_tray_menu_includes_overlay_controls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Overlay enable and position controls should be present in the tray menu."""
        fake_pystray = __import__("types").SimpleNamespace(
            Menu=FakeMenu, MenuItem=FakeMenuItem
        )
        monkeypatch.setitem(sys.modules, "pystray", fake_pystray)

        menu = TrayMenu(
            get_overlay_enabled_state=lambda: True,
            get_overlay_position_state=lambda: "top-left",
            get_overlay_screen_state=lambda: "cursor",
            get_overlay_auto_hide_state=lambda: 0.0,
            get_overlay_density_state=lambda: "compact",
        ).create_menu()

        overlay_item = menu[2]
        overlay_menu = overlay_item.action
        enabled_item = overlay_menu[0]
        position_item = overlay_menu[1]
        display_item = overlay_menu[2]
        auto_hide_item = overlay_menu[3]
        view_item = overlay_menu[4]
        position_menu = position_item.action
        display_menu = display_item.action
        auto_hide_menu = auto_hide_item.action
        view_menu = view_item.action

        assert overlay_item.text == "Overlay"
        assert enabled_item.text == "Enabled"
        assert enabled_item.checked(None) is True
        assert position_item.text == "Position"
        assert [item.text for item in position_menu] == [
            "Top Left",
            "Top Right",
            "Bottom Left",
            "Bottom Right",
        ]
        assert all(item.radio is True for item in position_menu)
        assert position_menu[0].checked(None) is True
        assert position_menu[-1].checked(None) is False
        assert display_item.text == "Display"
        assert [item.text for item in display_menu] == [
            "Primary Display",
            "Cursor Display",
        ]
        assert all(item.radio is True for item in display_menu)
        assert display_menu[0].checked(None) is False
        assert display_menu[1].checked(None) is True
        assert auto_hide_item.text == "Ready Auto-Hide"
        assert [item.text for item in auto_hide_menu] == [
            "Stay Visible",
            "1.5 Seconds",
            "3 Seconds",
            "5 Seconds",
        ]
        assert all(item.radio is True for item in auto_hide_menu)
        assert auto_hide_menu[0].checked(None) is True
        assert auto_hide_menu[1].checked(None) is False
        assert view_item.text == "View"
        assert [item.text for item in view_menu] == ["Detailed", "Compact"]
        assert all(item.radio is True for item in view_menu)
        assert view_menu[0].checked(None) is False
        assert view_menu[1].checked(None) is True

    def test_qt_tray_menu_refreshes_overlay_checks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Qt tray menus should mirror the same dynamic overlay controls."""
        fake_qtwidgets = __import__("types").SimpleNamespace(QMenu=FakeQtMenu)
        fake_qtgui = __import__("types").SimpleNamespace(QActionGroup=FakeQtActionGroup)
        monkeypatch.setitem(
            sys.modules, "PySide6", __import__("types").SimpleNamespace()
        )
        monkeypatch.setitem(sys.modules, "PySide6.QtGui", fake_qtgui)
        monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", fake_qtwidgets)

        state: dict[str, Any] = {
            "overlay_enabled": False,
            "overlay_position": "bottom-right",
            "overlay_screen": "primary",
            "overlay_auto_hide": 1.5,
            "overlay_density": "detailed",
        }

        menu = TrayMenu(
            get_overlay_enabled_state=lambda: state["overlay_enabled"],
            get_overlay_position_state=lambda: state["overlay_position"],
            get_overlay_screen_state=lambda: state["overlay_screen"],
            get_overlay_auto_hide_state=lambda: state["overlay_auto_hide"],
            get_overlay_density_state=lambda: state["overlay_density"],
        ).create_qt_menu(StrictFakeIcon())

        state["overlay_enabled"] = True
        state["overlay_position"] = "top-left"
        state["overlay_screen"] = "cursor"
        state["overlay_auto_hide"] = 0.0
        state["overlay_density"] = "compact"
        menu.aboutToShow.emit()

        overlay_menu = menu.actions()[2].menu()
        assert overlay_menu is not None

        enabled_action = overlay_menu.actions()[0]
        position_menu = overlay_menu.actions()[1].menu()
        display_menu = overlay_menu.actions()[2].menu()
        auto_hide_menu = overlay_menu.actions()[3].menu()
        view_menu = overlay_menu.actions()[4].menu()

        assert enabled_action.isChecked() is True
        assert (
            position_menu is not None and position_menu.actions()[0].isChecked() is True
        )
        assert (
            display_menu is not None and display_menu.actions()[1].isChecked() is True
        )
        assert (
            auto_hide_menu is not None
            and auto_hide_menu.actions()[0].isChecked() is True
        )
        assert view_menu is not None and view_menu.actions()[1].isChecked() is True
        action_groups = getattr(menu, "_action_groups")
        assert len(action_groups) == 5
        assert all(group.exclusive is True for group in action_groups)
        assert [action.text() for action in action_groups[0].actions] == [
            "English",
            "Russian",
            "Auto-Detect",
        ]
