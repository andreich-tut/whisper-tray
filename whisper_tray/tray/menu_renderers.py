"""Backend-specific tray menu renderers."""

from __future__ import annotations

from typing import Any

from whisper_tray.tray.menu_model import MenuEntry


def render_pystray_menu(entries: tuple[MenuEntry, ...]) -> Any:
    """Render the shared menu model as a pystray menu."""
    import pystray

    return pystray.Menu(*(_render_pystray_entry(entry) for entry in entries))


def _render_pystray_entry(entry: MenuEntry) -> Any:
    """Render one shared menu entry as a pystray MenuItem."""
    import pystray

    action: Any
    if entry.is_submenu:
        action = render_pystray_menu(entry.children)
    else:
        action = entry.action

    checked_fn = None
    if entry.checked is not None:
        checked_callback = entry.checked

        def checked(_item: object) -> bool:
            return checked_callback()

        checked_fn = checked

    return pystray.MenuItem(
        entry.label,
        action,
        checked=checked_fn,
        radio=entry.radio,
    )


def render_qt_menu(entries: tuple[MenuEntry, ...], icon: object) -> Any:
    """Render the shared menu model as a Qt tray menu."""
    from PySide6.QtGui import QActionGroup
    from PySide6.QtWidgets import QMenu

    root_menu = QMenu()
    action_groups: list[Any] = []
    _render_qt_entries(
        menu=root_menu,
        entries=entries,
        icon=icon,
        action_groups=action_groups,
        action_group_factory=QActionGroup,
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


def _render_qt_entries(
    *,
    menu: Any,
    entries: tuple[MenuEntry, ...],
    icon: object,
    action_groups: list[Any],
    action_group_factory: Any,
) -> None:
    """Append shared menu entries to a Qt menu."""
    radio_entries = tuple(entry for entry in entries if entry.radio)
    action_group = None
    if radio_entries:
        action_group = action_group_factory(menu)
        action_group.setExclusive(True)
        action_groups.append(action_group)

    for entry in entries:
        if entry.is_submenu:
            submenu = menu.addMenu(entry.label)
            _render_qt_entries(
                menu=submenu,
                entries=entry.children,
                icon=icon,
                action_groups=action_groups,
                action_group_factory=action_group_factory,
            )
            continue

        action = menu.addAction(entry.label)
        if entry.checked is not None:
            action.setCheckable(True)
            action.setChecked(bool(entry.checked()))
            setattr(action, "_checked_callback", entry.checked)
        if action_group is not None and entry.radio:
            action_group.addAction(action)
        if entry.action is not None:
            action.triggered.connect(
                lambda _=False, callback=entry.action: callback(icon, None)
            )
