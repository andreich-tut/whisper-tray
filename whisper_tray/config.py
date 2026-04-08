"""
Configuration management for WhisperTray.

Loads settings from environment variables, .env files, and provides defaults.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Load .env from current directory or parent directory
    _env_loaded = load_dotenv()
    if _env_loaded:
        logger.info("Loaded .env file")
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables only


@dataclass
class ModelConfig:
    """Configuration for the Whisper model."""

    model_size: str = field(default_factory=lambda: os.getenv("MODEL_SIZE", "large-v3"))
    device: str = field(default_factory=lambda: os.getenv("DEVICE", "cuda"))
    compute_type: str = field(
        default_factory=lambda: os.getenv("COMPUTE_TYPE", "float16")
    )
    language: Optional[str] = field(default_factory=lambda: os.getenv("LANGUAGE", None))

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        valid_models = ["tiny", "base", "small", "medium", "large", "large-v3"]
        if self.model_size not in valid_models:
            logger.warning(
                f"Unknown model size: {self.model_size}. "
                f"Valid options: {', '.join(valid_models)}"
            )

        valid_devices = ["cuda", "cpu"]
        if self.device not in valid_devices:
            logger.warning(
                f"Unknown device: {self.device}. Falling back to 'cuda'. "
                f"Valid options: {', '.join(valid_devices)}"
            )
            self.device = "cuda"


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
        default_factory=lambda: os.getenv("AUTO_PASTE", "true").lower()
        in ("true", "1", "yes", "on")
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.paste_delay < 0:
            logger.warning(f"Negative paste delay: {self.paste_delay}. Setting to 0.1")
            self.paste_delay = 0.1


@dataclass
class AudioConfig:
    """Configuration for audio recording."""

    sample_rate: int = 16000
    min_recording_duration: float = 0.3
    vad_threshold: float = 0.5
    vad_silence_duration_ms: int = 500


@dataclass
class AppConfig:
    """Main application configuration combining all sub-configs."""

    model: ModelConfig = field(default_factory=ModelConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        return cls()

    def log_config(self) -> None:
        """Log current configuration for debugging."""
        logger.info(
            f"Model config: size={self.model.model_size}, "
            f"device={self.model.device}, compute={self.model.compute_type}"
        )
        logger.info(f"Hotkey: {'+'.join(sorted(self.hotkey.hotkey))}")
        logger.info(
            f"Auto-paste: {self.hotkey.auto_paste}, "
            f"delay: {self.hotkey.paste_delay}s"
        )
        logger.info(
            f"Audio: {self.audio.sample_rate}Hz, "
            f"min duration: {self.audio.min_recording_duration}s"
        )
