"""State accessors and checked helpers for tray menus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TrayMenuState:
    """Normalized state getters used by tray menu renderers."""

    get_auto_paste_state: Callable[[], bool]
    get_language_state: Callable[[], str]
    get_overlay_enabled_state: Callable[[], bool]
    get_overlay_position_state: Callable[[], str]
    get_overlay_screen_state: Callable[[], str]
    get_overlay_auto_hide_state: Callable[[], float]
    get_overlay_density_state: Callable[[], str]

    def language_checked(self, language: str) -> bool:
        """Return whether the requested language is currently active."""
        return self.get_language_state() == language

    def overlay_position_checked(self, position: str) -> bool:
        """Return whether the requested overlay position is currently active."""
        return self.get_overlay_position_state() == position

    def overlay_screen_checked(self, screen: str) -> bool:
        """Return whether the requested overlay screen is currently active."""
        return self.get_overlay_screen_state() == screen

    def overlay_auto_hide_checked(self, seconds: float) -> bool:
        """Return whether the requested ready timeout is currently active."""
        return abs(self.get_overlay_auto_hide_state() - seconds) < 1e-9

    def overlay_density_checked(self, density: str) -> bool:
        """Return whether the requested overlay density is currently active."""
        return self.get_overlay_density_state() == density

    def overlay_position_checked_callback(self, position: str) -> Callable[[], bool]:
        """Return a checked callback for an overlay position option."""
        return lambda: self.overlay_position_checked(position)

    def overlay_screen_checked_callback(self, screen: str) -> Callable[[], bool]:
        """Return a checked callback for an overlay screen option."""
        return lambda: self.overlay_screen_checked(screen)

    def overlay_auto_hide_checked_callback(
        self,
        seconds: float,
    ) -> Callable[[], bool]:
        """Return a checked callback for an overlay auto-hide option."""
        return lambda: self.overlay_auto_hide_checked(seconds)

    def overlay_density_checked_callback(self, density: str) -> Callable[[], bool]:
        """Return a checked callback for an overlay density option."""
        return lambda: self.overlay_density_checked(density)


def build_tray_menu_state(
    *,
    get_auto_paste_state: Callable[[], bool] | None = None,
    get_language_state: Callable[[], str] | None = None,
    get_overlay_enabled_state: Callable[[], bool] | None = None,
    get_overlay_position_state: Callable[[], str] | None = None,
    get_overlay_screen_state: Callable[[], str] | None = None,
    get_overlay_auto_hide_state: Callable[[], float] | None = None,
    get_overlay_density_state: Callable[[], str] | None = None,
) -> TrayMenuState:
    """Build normalized tray-menu state getters with safe defaults."""
    return TrayMenuState(
        get_auto_paste_state=get_auto_paste_state or (lambda: False),
        get_language_state=get_language_state or (lambda: "auto"),
        get_overlay_enabled_state=get_overlay_enabled_state or (lambda: False),
        get_overlay_position_state=get_overlay_position_state
        or (lambda: "bottom-right"),
        get_overlay_screen_state=get_overlay_screen_state or (lambda: "primary"),
        get_overlay_auto_hide_state=get_overlay_auto_hide_state or (lambda: 1.5),
        get_overlay_density_state=get_overlay_density_state or (lambda: "detailed"),
    )
