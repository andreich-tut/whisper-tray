"""Backend-neutral tray menu state and definitions."""

from whisper_tray.core.tray_menu.callbacks import TrayMenuCallbacks
from whisper_tray.core.tray_menu.definition import build_menu_entries
from whisper_tray.core.tray_menu.model import (
    OVERLAY_AUTO_HIDE_OPTIONS,
    OVERLAY_DENSITIES,
    OVERLAY_POSITIONS,
    OVERLAY_SCREENS,
    ActionCallback,
    CheckedCallback,
    MenuEntry,
)
from whisper_tray.core.tray_menu.state import TrayMenuState, build_tray_menu_state

__all__ = [
    "ActionCallback",
    "CheckedCallback",
    "MenuEntry",
    "OVERLAY_AUTO_HIDE_OPTIONS",
    "OVERLAY_DENSITIES",
    "OVERLAY_POSITIONS",
    "OVERLAY_SCREENS",
    "TrayMenuCallbacks",
    "TrayMenuState",
    "build_menu_entries",
    "build_tray_menu_state",
]
