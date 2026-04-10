"""Backend-neutral overlay models, protocols, and controllers."""

from whisper_tray.core.overlay.runtime import (
    NullOverlayController,
    OverlayCommand,
    OverlayCommandKind,
    OverlayController,
    OverlayRuntime,
    OverlayRuntimeFactory,
    OverlaySettings,
    OverlayStartupCallback,
    ThreadedOverlayController,
)

__all__ = [
    "NullOverlayController",
    "OverlayCommand",
    "OverlayCommandKind",
    "OverlayController",
    "OverlayRuntime",
    "OverlayRuntimeFactory",
    "OverlaySettings",
    "OverlayStartupCallback",
    "ThreadedOverlayController",
]
