"""
Configuration management for WhisperTray.

Loads settings from environment variables, .env files, and provides defaults.
CPU-first design: GPU is optional acceleration only.
"""

from __future__ import annotations

import logging
import os
import platform
from dataclasses import dataclass, field
from typing import Literal, Optional

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


# --- Platform-aware defaults ---


def _default_device() -> str:
    """Return 'cpu' on macOS (no CUDA), 'cpu' on Linux/Windows as safe default."""
    if platform.system() == "Darwin":
        return "cpu"
    return os.getenv("DEVICE", "cpu")


def _default_compute() -> str:
    """Return 'int8' for CPU, 'float16' for CUDA."""
    device = _default_device()
    if device == "cuda":
        return "float16"
    return "int8"


def _default_model() -> str:
    """Return 'small' as CPU-first default (good speed/quality balance)."""
    return os.getenv("MODEL_SIZE", "small")


# --- Preset definitions ---

ModelPreset = Literal["fast", "balanced", "accurate"]

MODEL_PRESETS: dict[ModelPreset, dict[str, str]] = {
    "fast": {
        "model_size": "base",
        "device": "cpu",
        "compute_type": "int8",
    },
    "balanced": {
        "model_size": "small",
        "device": "cpu",
        "compute_type": "int8",
    },
    "accurate": {
        "model_size": "medium",
        "device": "cpu",
        "compute_type": "int8",
    },
}


def _apply_preset(preset_name: str) -> dict[str, str]:
    """Return preset dict, or empty dict if unknown."""
    default: dict[str, str] = {}
    if preset_name in ("fast", "balanced", "accurate"):
        return MODEL_PRESETS[preset_name]  # type: ignore[index]
    return default


@dataclass
class ModelConfig:
    """Configuration for the Whisper model."""

    model_size: str = field(default_factory=_default_model)
    device: str = field(default_factory=_default_device)
    compute_type: str = field(default_factory=_default_compute)
    language: Optional[str] = field(default_factory=lambda: os.getenv("LANGUAGE", None))

    # Decoding optimization (for CPU-first latency)
    beam_size: int = field(default_factory=lambda: int(os.getenv("BEAM_SIZE", "1")))
    condition_on_previous_text: bool = field(
        default_factory=lambda: os.getenv("CONDITION_ON_PREVIOUS_TEXT", "false").lower()
        in ("true", "1", "yes", "on")
    )

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
                f"Unknown device: {self.device}. Valid options: "
                f"{', '.join(valid_devices)}. Defaulting to 'cpu'."
            )
            self.device = "cpu"

        if self.beam_size < 1:
            logger.warning(
                f"Invalid beam_size: {self.beam_size}. Setting to 1 (greedy)."
            )
            self.beam_size = 1


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

    sample_rate: int = field(
        default_factory=lambda: int(os.getenv("SAMPLE_RATE", "16000"))
    )
    min_recording_duration: float = field(
        default_factory=lambda: float(os.getenv("MIN_RECORDING_DURATION", "0.3"))
    )
    vad_threshold: float = field(
        default_factory=lambda: float(os.getenv("VAD_THRESHOLD", "0.5"))
    )
    vad_silence_duration_ms: int = field(
        default_factory=lambda: int(os.getenv("VAD_SILENCE_DURATION_MS", "500"))
    )


@dataclass
class AppConfig:
    """Main application configuration combining all sub-configs."""

    model: ModelConfig = field(default_factory=ModelConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        # Set CPU thread limit if not already set (prevents oversubscription)
        # This should be done early, before ONNX Runtime initializes threads
        cpu_threads = os.getenv("CPU_THREADS")
        if cpu_threads is not None:
            os.environ["OMP_NUM_THREADS"] = cpu_threads
            os.environ["ONNX_NUM_THREADS"] = cpu_threads
        return cls()

    def log_config(self) -> None:
        """Log current configuration for debugging."""
        logger.info(
            f"Model config: size={self.model.model_size}, "
            f"device={self.model.device}, compute={self.model.compute_type}, "
            f"language={self.model.language}"
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
