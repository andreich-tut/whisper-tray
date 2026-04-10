"""Compatibility facade for backend-neutral tray menu callbacks."""

from whisper_tray.core.tray_menu.callbacks import (
    MenuAction,
    OverlayTimeoutAction,
    OverlayValueAction,
    TrayMenuCallbacks,
)

__all__ = [
    "MenuAction",
    "OverlayTimeoutAction",
    "OverlayValueAction",
    "TrayMenuCallbacks",
]
