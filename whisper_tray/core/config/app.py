"""Composite application configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from whisper_tray.core.config.audio import AudioConfig
from whisper_tray.core.config.hotkey import HotkeyConfig
from whisper_tray.core.config.logging import apply_cpu_thread_limits, log_config
from whisper_tray.core.config.model import ModelConfig
from whisper_tray.core.config.overlay import OverlayConfig
from whisper_tray.core.config.ui import UiConfig


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
