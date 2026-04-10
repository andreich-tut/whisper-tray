"""Public configuration facade for WhisperTray."""

from __future__ import annotations

from whisper_tray.config.audio import AudioConfig
from whisper_tray.config.env import _env_candidate_paths, _load_env_file
from whisper_tray.config.hotkey import HotkeyConfig
from whisper_tray.config.logging import apply_cpu_thread_limits, log_config
from whisper_tray.config.model import ModelConfig
from whisper_tray.config.overlay import OverlayConfig
from whisper_tray.config.ui import UiConfig
from whisper_tray.core.config.app import AppConfig
from whisper_tray.platform.defaults import MODEL_PRESETS, ModelPreset, _apply_preset

_load_env_file()


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
    "_env_candidate_paths",
    "_load_env_file",
    "apply_cpu_thread_limits",
    "log_config",
]
