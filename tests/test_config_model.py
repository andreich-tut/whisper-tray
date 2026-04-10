"""Tests for model, audio, hotkey, and app config objects."""

import logging
import os
from typing import Generator

import pytest

from whisper_tray.config import (
    AppConfig,
    AudioConfig,
    HotkeyConfig,
    ModelConfig,
    OverlayConfig,
    UiConfig,
)


@pytest.fixture(autouse=True)
def _clear_env() -> Generator[None, None, None]:
    """Clear environment variables that could affect config tests."""
    env_vars = [
        "MODEL_SIZE",
        "DEVICE",
        "COMPUTE_TYPE",
        "LANGUAGE",
        "HOTKEY",
        "AUTO_PASTE",
        "PASTE_DELAY",
        "VAD_THRESHOLD",
        "VAD_SILENCE_DURATION_MS",
        "MIN_RECORDING_DURATION",
        "SAMPLE_RATE",
        "BEAM_SIZE",
        "CONDITION_ON_PREVIOUS_TEXT",
        "CPU_THREADS",
        "OVERLAY_ENABLED",
        "OVERLAY_AUTO_HIDE_SECONDS",
        "OVERLAY_POSITION",
        "OVERLAY_SCREEN",
        "OVERLAY_DENSITY",
        "TRAY_BACKEND",
    ]
    saved: dict[str, str | None] = {}
    for var in env_vars:
        saved[var] = os.environ.pop(var, None)
    yield
    for var, value in saved.items():
        if value is not None:
            os.environ[var] = value


class TestModelConfig:
    """Test model configuration."""

    def test_defaults(self) -> None:
        """Test default model configuration (CPU-first)."""
        config = ModelConfig()
        assert config.model_size == "small"
        assert config.device == "cpu"
        assert config.compute_type == "int8"
        assert config.language is None
        assert config.beam_size == 1
        assert config.condition_on_previous_text is False

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

    def test_beam_size_validation(self) -> None:
        """Test invalid beam_size is corrected."""
        config = ModelConfig(beam_size=0)
        assert config.beam_size == 1


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

    def test_env_var_bindings(self) -> None:
        """Test audio config reads from environment variables."""
        os.environ["SAMPLE_RATE"] = "44100"
        os.environ["MIN_RECORDING_DURATION"] = "0.5"
        os.environ["VAD_THRESHOLD"] = "0.7"
        os.environ["VAD_SILENCE_DURATION_MS"] = "300"

        config = AudioConfig()
        assert config.sample_rate == 44100
        assert config.min_recording_duration == 0.5
        assert config.vad_threshold == 0.7
        assert config.vad_silence_duration_ms == 300


class TestAppConfig:
    """Test application configuration."""

    def test_from_env(self) -> None:
        """Test creating config from environment."""
        config = AppConfig.from_env()
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.hotkey, HotkeyConfig)
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.overlay, OverlayConfig)
        assert isinstance(config.ui, UiConfig)

    def test_log_config(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging configuration."""
        caplog.set_level(logging.INFO)
        config = AppConfig()
        config.log_config()
        assert "Model config" in caplog.text
        assert "Overlay:" in caplog.text
        assert "UI: tray-backend=auto" in caplog.text


class TestUiConfig:
    """Test UI runtime selection configuration."""

    def test_defaults(self) -> None:
        """Auto runtime selection should be the default."""
        config = UiConfig()
        assert config.tray_backend == "auto"

    def test_env_var_bindings(self) -> None:
        """The tray runtime selection should read from the environment."""
        os.environ["TRAY_BACKEND"] = "pystray"

        config = UiConfig()

        assert config.tray_backend == "pystray"

    def test_invalid_backend_falls_back_to_auto(self) -> None:
        """Unknown runtime selections should degrade to auto."""
        config = UiConfig(tray_backend="mystery")
        assert config.tray_backend == "auto"
