"""Hotkey and paste behavior configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from whisper_tray.config.defaults import read_bool_env

logger = logging.getLogger(__name__)


@dataclass
class HotkeyConfig:
    """Configuration for hotkey behavior."""

    hotkey: set[str] = field(
        default_factory=lambda: set(
            os.getenv("HOTKEY", "ctrl,shift,space").lower().split(",")
        )
    )
    paste_delay: float = field(
        default_factory=lambda: float(os.getenv("PASTE_DELAY", "0.1"))
    )
    auto_paste: bool = field(
        default_factory=lambda: read_bool_env("AUTO_PASTE", default=True)
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.paste_delay < 0:
            logger.warning(
                "Negative paste delay: %s. Setting to 0.1",
                self.paste_delay,
            )
            self.paste_delay = 0.1
