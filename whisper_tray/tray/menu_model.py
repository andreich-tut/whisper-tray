"""Compatibility facade for backend-neutral tray menu models."""

from whisper_tray.core.tray_menu.model import (
    OVERLAY_AUTO_HIDE_OPTIONS,
    OVERLAY_DENSITIES,
    OVERLAY_POSITIONS,
    OVERLAY_SCREENS,
    ActionCallback,
    CheckedCallback,
    MenuEntry,
)

__all__ = [
    "ActionCallback",
    "CheckedCallback",
    "MenuEntry",
    "OVERLAY_AUTO_HIDE_OPTIONS",
    "OVERLAY_DENSITIES",
    "OVERLAY_POSITIONS",
    "OVERLAY_SCREENS",
]
