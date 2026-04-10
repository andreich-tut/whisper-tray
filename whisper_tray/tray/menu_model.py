"""Shared tray menu model and option constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

CheckedCallback = Callable[[], bool]
ActionCallback = Callable[[object, object | None], None]


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


@dataclass(frozen=True)
class MenuEntry:
    """Declarative tray menu entry used by both renderers."""

    label: str
    action: ActionCallback | None = None
    checked: CheckedCallback | None = None
    radio: bool = False
    children: tuple["MenuEntry", ...] = field(default_factory=tuple)

    @property
    def is_submenu(self) -> bool:
        """Return whether the entry contains nested menu items."""
        return bool(self.children)
