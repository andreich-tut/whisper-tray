"""Callback wrappers for tray menu actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

MenuAction = Callable[[object, object], None]
OverlayValueAction = Callable[[str, object, object], None]
OverlayTimeoutAction = Callable[[float, object, object], None]


@dataclass
class TrayMenuCallbacks:
    """Typed callback bundle for tray menu actions."""

    on_toggle_auto_paste: MenuAction | None = None
    on_set_language_en: MenuAction | None = None
    on_set_language_ru: MenuAction | None = None
    on_set_language_auto: MenuAction | None = None
    on_toggle_overlay: MenuAction | None = None
    on_set_overlay_position: OverlayValueAction | None = None
    on_set_overlay_screen: OverlayValueAction | None = None
    on_set_overlay_auto_hide: OverlayTimeoutAction | None = None
    on_set_overlay_density: OverlayValueAction | None = None
    on_exit: MenuAction | None = None

    @staticmethod
    def wrap(callback: MenuAction | None) -> MenuAction:
        """Wrap callbacks with a uniform `(icon, item)` signature."""

        def wrapped(icon: object, item: object) -> None:
            if callback is not None:
                callback(icon, item)

        return wrapped

    def wrap_overlay_position(self, position: str) -> MenuAction:
        """Wrap an overlay-position callback with its selected value."""

        def wrapped(icon: object, item: object) -> None:
            if self.on_set_overlay_position is not None:
                self.on_set_overlay_position(position, icon, item)

        return wrapped

    def wrap_overlay_screen(self, screen: str) -> MenuAction:
        """Wrap an overlay-screen callback with its selected value."""

        def wrapped(icon: object, item: object) -> None:
            if self.on_set_overlay_screen is not None:
                self.on_set_overlay_screen(screen, icon, item)

        return wrapped

    def wrap_overlay_auto_hide(self, seconds: float) -> MenuAction:
        """Wrap an overlay auto-hide callback with its selected timeout."""

        def wrapped(icon: object, item: object) -> None:
            if self.on_set_overlay_auto_hide is not None:
                self.on_set_overlay_auto_hide(seconds, icon, item)

        return wrapped

    def wrap_overlay_density(self, density: str) -> MenuAction:
        """Wrap an overlay-density callback with its selected value."""

        def wrapped(icon: object, item: object) -> None:
            if self.on_set_overlay_density is not None:
                self.on_set_overlay_density(density, icon, item)

        return wrapped
