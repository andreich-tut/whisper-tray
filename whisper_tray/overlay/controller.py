"""Overlay controller abstractions and fallbacks."""

from __future__ import annotations

import logging
from importlib.util import find_spec

from whisper_tray.core.overlay import (
    NullOverlayController,
    OverlayController,
    OverlayRuntimeFactory,
    OverlaySettings,
    ThreadedOverlayController,
)

logger = logging.getLogger(__name__)


def _pyside6_is_available() -> bool:
    """Return whether the optional Qt overlay dependency is installed."""
    return find_spec("PySide6") is not None


def create_overlay_controller(
    settings: OverlaySettings,
    runtime_factory: OverlayRuntimeFactory | None = None,
) -> OverlayController:
    """
    Create an overlay controller.

    When the optional Qt dependency is installed, the overlay runs on its own UI
    thread so the existing pystray application loop can stay in place for now.
    """
    if not settings.enabled:
        return NullOverlayController()

    factory = runtime_factory
    if factory is None:
        if not _pyside6_is_available():
            logger.warning(
                "Overlay support requested, but PySide6 is not installed. "
                "Continuing without the overlay window."
            )
            return NullOverlayController()
        try:
            from whisper_tray.overlay.pyside_overlay import PySide6OverlayRuntime
        except ImportError:
            logger.warning(
                "Overlay support requested, but PySide6 is not installed. "
                "Continuing without the overlay window."
            )
            return NullOverlayController()
        factory = PySide6OverlayRuntime

    try:
        return ThreadedOverlayController(
            factory,
            settings=settings,
        )
    except Exception:
        logger.warning(
            "Overlay support requested, but the UI runtime failed to start. "
            "Continuing without the overlay window.",
            exc_info=True,
        )
        return NullOverlayController()
