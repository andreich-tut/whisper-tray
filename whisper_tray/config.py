"""
Configuration management for WhisperTray.

Loads settings from environment variables, .env files, and provides defaults.
CPU-first design: GPU is optional acceleration only.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)


def _env_candidate_paths() -> tuple[Path, ...]:
    """Return the supported `.env` lookup locations in priority order."""
    module_dir = Path(__file__).resolve().parent
    module_parent = module_dir.parent
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve(strict=False)
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(path)

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        add(exe_dir / ".env")
        add(exe_dir.parent / ".env")
        add(exe_dir.parent.parent / ".env")
        add(exe_dir.parent.parent / "whisper_tray" / ".env")

    add(Path.cwd() / ".env")
    add(module_parent / ".env")
    add(module_dir / ".env")
    return tuple(candidates)


def _load_env_file() -> None:
    """Load the first matching `.env` file when python-dotenv is available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for candidate in _env_candidate_paths():
        if not candidate.is_file():
            continue
        if load_dotenv(candidate, override=False):
            logger.info("Loaded .env file from %s", candidate)
            return


_load_env_file()


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
class OverlayConfig:
    """Configuration for the optional on-screen overlay."""

    VALID_POSITIONS = {
        "top-left",
        "top-right",
        "bottom-left",
        "bottom-right",
    }
    VALID_DENSITIES = {
        "compact",
        "detailed",
    }
    VALID_SCREENS = {
        "primary",
        "cursor",
    }
    enabled: bool = field(
        default_factory=lambda: os.getenv("OVERLAY_ENABLED", "false").lower()
        in ("true", "1", "yes", "on")
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


@dataclass
class UiConfig:
    """Configuration for UI runtime selection and startup behavior."""

    VALID_TRAY_BACKENDS = {
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


@dataclass
class AppConfig:
    """Main application configuration combining all sub-configs."""

    model: ModelConfig = field(default_factory=ModelConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    ui: UiConfig = field(default_factory=UiConfig)

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
        logger.info(
            f"Overlay: enabled={self.overlay.enabled}, "
            f"position={self.overlay.position}, "
            f"screen={self.overlay.screen}, "
            f"auto-hide={self.overlay.auto_hide_seconds}s, "
            f"density={self.overlay.density}"
        )
        logger.info(f"UI: tray-backend={self.ui.tray_backend}")
