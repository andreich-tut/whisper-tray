"""Overlay-related configuration values."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import ClassVar

from whisper_tray.config.defaults import read_bool_env

logger = logging.getLogger(__name__)


@dataclass
class OverlayConfig:
    """Configuration for the optional on-screen overlay."""

    VALID_POSITIONS: ClassVar[set[str]] = {
        "top-left",
        "top-right",
        "bottom-left",
        "bottom-right",
    }
    VALID_DENSITIES: ClassVar[set[str]] = {"compact", "detailed"}
    VALID_SCREENS: ClassVar[set[str]] = {"primary", "cursor"}

    enabled: bool = field(
        default_factory=lambda: read_bool_env("OVERLAY_ENABLED", default=False)
    )
    auto_hide_seconds: float = field(
        default_factory=lambda: float(os.getenv("OVERLAY_AUTO_HIDE_SECONDS", "1.5"))
    )
    position: str = field(
        default_factory=lambda: os.getenv("OVERLAY_POSITION", "bottom-right")
    )
    screen: str = field(default_factory=lambda: os.getenv("OVERLAY_SCREEN", "primary"))
    density: str = field(
        default_factory=lambda: os.getenv("OVERLAY_DENSITY", "detailed")
    )

    def __post_init__(self) -> None:
        """Validate overlay settings."""
        if self.auto_hide_seconds < 0:
            logger.warning(
                "Negative overlay auto-hide duration: %s. Setting to 1.5",
                self.auto_hide_seconds,
            )
            self.auto_hide_seconds = 1.5

        if self.position not in self.VALID_POSITIONS:
            logger.warning(
                "Unknown overlay position: %s. Setting to bottom-right.",
                self.position,
            )
            self.position = "bottom-right"

        if self.screen not in self.VALID_SCREENS:
            logger.warning(
                "Unknown overlay screen target: %s. Setting to primary.",
                self.screen,
            )
            self.screen = "primary"

        if self.density not in self.VALID_DENSITIES:
            logger.warning(
                "Unknown overlay density: %s. Setting to detailed.",
                self.density,
            )
            self.density = "detailed"
