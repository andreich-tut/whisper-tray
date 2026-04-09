"""Tests for configuration management."""

import logging
import os
from typing import Generator

import pytest

from whisper_tray.config import AppConfig, AudioConfig, HotkeyConfig, ModelConfig


@pytest.fixture(autouse=True)
def clear_env() -> Generator[None, None, None]:
    """Clear environment variables that could affect tests."""
    env_vars = [
        "MODEL_SIZE",
        "DEVICE",
        "COMPUTE_TYPE",
        "LANGUAGE",
        "HOTKEY",
        "AUTO_PASTE",
        "PASTE_DELAY",
    ]
    saved = {}
    for var in env_vars:
        saved[var] = os.environ.pop(var, None)
    yield
    for var, value in saved.items():
        if value is not None:
            os.environ[var] = value


class TestModelConfig:
    """Test model configuration."""

    def test_defaults(self) -> None:
        """Test default model configuration."""
        config = ModelConfig()
        assert config.model_size == "large-v3"
        assert config.device == "cuda"
        assert config.compute_type == "float16"
        assert config.language is None

    def test_custom_values(self) -> None:
        """Test custom model configuration."""
        config = ModelConfig(
            model_size="base",
            device="cpu",
            compute_type="int8",
            language="en",
        )
        assert config.model_size == "base"
        assert config.device == "cpu"
        assert config.compute_type == "int8"
        assert config.language == "en"


class TestHotkeyConfig:
    """Test hotkey configuration."""

    def test_defaults(self) -> None:
        """Test default hotkey configuration."""
        config = HotkeyConfig()
        assert "ctrl" in config.hotkey
        assert "space" in config.hotkey
        assert config.auto_paste is True
        assert config.paste_delay == 0.1

    def test_custom_hotkey(self) -> None:
        """Test custom hotkey configuration."""
        config = HotkeyConfig(hotkey={"ctrl", "alt", "a"})
        assert len(config.hotkey) == 3
        assert "ctrl" in config.hotkey
        assert "alt" in config.hotkey
        assert "a" in config.hotkey

    def test_auto_paste_disabled(self) -> None:
        """Test auto-paste disabled."""
        config = HotkeyConfig(auto_paste=False)
        assert config.auto_paste is False


class TestAudioConfig:
    """Test audio configuration."""

    def test_defaults(self) -> None:
        """Test default audio configuration."""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.min_recording_duration == 0.3
        assert config.vad_threshold == 0.5
        assert config.vad_silence_duration_ms == 500


class TestAppConfig:
    """Test application configuration."""

    def test_from_env(self) -> None:
        """Test creating config from environment."""
        config = AppConfig.from_env()
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.hotkey, HotkeyConfig)
        assert isinstance(config.audio, AudioConfig)

    def test_log_config(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging configuration."""
        caplog.set_level(logging.INFO)
        config = AppConfig()
        config.log_config()
        assert "Model config" in caplog.text
