"""UI runtime selection configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class UiConfig:
    """Configuration for UI runtime selection and startup behavior."""

    VALID_TRAY_BACKENDS: ClassVar[set[str]] = {
        "auto",
        "pystray",
        "qt",
    }

    tray_backend: str = field(
        default_factory=lambda: os.getenv("TRAY_BACKEND", "auto").lower()
    )

    def __post_init__(self) -> None:
        """Validate tray runtime selection."""
        if self.tray_backend not in self.VALID_TRAY_BACKENDS:
            logger.warning(
                "Unknown tray backend: %s. Setting to auto.",
                self.tray_backend,
            )
            self.tray_backend = "auto"
