"""Core configuration models and helpers."""

from whisper_tray.core.config.app import AppConfig
from whisper_tray.core.config.audio import AudioConfig
from whisper_tray.core.config.hotkey import HotkeyConfig
from whisper_tray.core.config.logging import apply_cpu_thread_limits, log_config
from whisper_tray.core.config.model import ModelConfig
from whisper_tray.core.config.overlay import OverlayConfig
from whisper_tray.core.config.ui import UiConfig
from whisper_tray.platform.defaults import MODEL_PRESETS, ModelPreset, _apply_preset

__all__ = [
    "MODEL_PRESETS",
    "AppConfig",
    "AudioConfig",
    "HotkeyConfig",
    "ModelConfig",
    "ModelPreset",
    "OverlayConfig",
    "UiConfig",
    "_apply_preset",
    "apply_cpu_thread_limits",
    "log_config",
]
