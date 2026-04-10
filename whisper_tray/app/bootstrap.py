"""App construction helpers for the WhisperTray lifecycle package."""

from __future__ import annotations

from whisper_tray.app.lifecycle import WhisperTrayApp
from whisper_tray.config import AppConfig


def create_app(config: AppConfig | None = None) -> WhisperTrayApp:
    """Build the main application with optional explicit configuration."""
    return WhisperTrayApp(config)
