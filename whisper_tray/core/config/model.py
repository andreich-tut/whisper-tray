"""Model configuration and validation."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from whisper_tray.platform.defaults import (
    default_compute_type,
    default_device,
    default_model_size,
    read_bool_env,
)

logger = logging.getLogger(__name__)

_VALID_MODELS = ("tiny", "base", "small", "medium", "large", "large-v3")
_VALID_DEVICES = ("cuda", "cpu")


def _default_language() -> str | None:
    """Return the requested transcription language, if any."""
    return os.getenv("LANGUAGE") or None


@dataclass
class ModelConfig:
    """Configuration for the Whisper model."""

    model_size: str = field(default_factory=default_model_size)
    device: str = field(default_factory=default_device)
    compute_type: str = field(default_factory=default_compute_type)
    language: str | None = field(default_factory=_default_language)
    beam_size: int = field(default_factory=lambda: int(os.getenv("BEAM_SIZE", "1")))
    condition_on_previous_text: bool = field(
        default_factory=lambda: read_bool_env("CONDITION_ON_PREVIOUS_TEXT")
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.model_size not in _VALID_MODELS:
            logger.warning(
                "Unknown model size: %s. Valid options: %s",
                self.model_size,
                ", ".join(_VALID_MODELS),
            )

        if self.device not in _VALID_DEVICES:
            logger.warning(
                "Unknown device: %s. Valid options: %s. Defaulting to cpu.",
                self.device,
                ", ".join(_VALID_DEVICES),
            )
            self.device = "cpu"

        if self.beam_size < 1:
            logger.warning(
                "Invalid beam_size: %s. Setting to 1 (greedy).",
                self.beam_size,
            )
            self.beam_size = 1
