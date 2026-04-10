"""Public configuration facade for WhisperTray."""

from __future__ import annotations

from dataclasses import dataclass, field

from whisper_tray.config.audio import AudioConfig
from whisper_tray.config.defaults import MODEL_PRESETS, ModelPreset, _apply_preset
from whisper_tray.config.env import _env_candidate_paths, _load_env_file
from whisper_tray.config.hotkey import HotkeyConfig
from whisper_tray.config.logging import apply_cpu_thread_limits, log_config
from whisper_tray.config.model import ModelConfig
from whisper_tray.config.overlay import OverlayConfig
from whisper_tray.config.ui import UiConfig


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
        apply_cpu_thread_limits()
        return cls()

    def log_config(self) -> None:
        """Log current configuration for debugging."""
        log_config(
            model=self.model,
            hotkey=self.hotkey,
            audio=self.audio,
            overlay=self.overlay,
            ui=self.ui,
        )


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
]
