"""Tests for configuration management."""

import logging
import os
from pathlib import Path
from typing import Generator

import pytest

import whisper_tray.config as config_module
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
    """Clear environment variables that could affect tests."""
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
        "OVERLAY_STYLE",
        "TRAY_BACKEND",
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
        """Test default model configuration (CPU-first)."""
        config = ModelConfig()
        assert config.model_size == "small"
        assert config.device == "cpu"
        assert config.compute_type == "int8"
        assert config.language is None
        assert config.beam_size == 1  # greedy decoding by default
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


class TestOverlayConfig:
    """Test overlay configuration."""

    def test_defaults(self) -> None:
        """Overlay should stay disabled until a UI backend is installed."""
        config = OverlayConfig()
        assert config.enabled is False
        assert config.auto_hide_seconds == 1.5
        assert config.position == "bottom-right"
        assert config.screen == "primary"
        assert config.density == "detailed"
        assert config.overlay_style == "card"

    def test_env_var_bindings(self) -> None:
        """Overlay config should read environment variables."""
        os.environ["OVERLAY_ENABLED"] = "true"
        os.environ["OVERLAY_AUTO_HIDE_SECONDS"] = "0"
        os.environ["OVERLAY_POSITION"] = "top-left"
        os.environ["OVERLAY_SCREEN"] = "cursor"
        os.environ["OVERLAY_DENSITY"] = "compact"
        os.environ["OVERLAY_STYLE"] = "blob"

        config = OverlayConfig()
        assert config.enabled is True
        assert config.auto_hide_seconds == 0
        assert config.position == "top-left"
        assert config.screen == "cursor"
        assert config.density == "compact"
        assert config.overlay_style == "blob"

    def test_invalid_position_falls_back_to_bottom_right(self) -> None:
        """Unknown positions should degrade to the default corner."""
        config = OverlayConfig(position="center")

        assert config.position == "bottom-right"

    def test_invalid_density_falls_back_to_detailed(self) -> None:
        """Unknown densities should degrade to the default presentation."""
        config = OverlayConfig(density="wide")

        assert config.density == "detailed"

    def test_invalid_screen_falls_back_to_primary(self) -> None:
        """Unknown screen targets should degrade to the primary display."""
        config = OverlayConfig(screen="secondary")

        assert config.screen == "primary"

    def test_invalid_style_falls_back_to_blob(self) -> None:
        """Unknown overlay styles should degrade to the card presentation."""
        config = OverlayConfig(overlay_style="glass")

        assert config.overlay_style == "card"


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


class TestEnvDiscovery:
    """Test `.env` lookup behavior across source and frozen runs."""

    def test_env_candidate_paths_include_package_env_for_frozen_build(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Frozen builds should look next to the exe and in repo-style package paths."""
        monkeypatch.setattr(config_module, "__file__", "/repo/whisper_tray/config.py")
        monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
        monkeypatch.setattr(
            config_module.sys,
            "executable",
            "/repo/dist/WhisperTray/WhisperTray.exe",
        )
        monkeypatch.setattr(
            config_module.Path,
            "cwd",
            staticmethod(lambda: Path("/repo/runtime")),
        )

        candidates = config_module._env_candidate_paths()

        assert Path("/repo/dist/WhisperTray/.env") in candidates
        assert Path("/repo/.env") in candidates
        assert Path("/repo/whisper_tray/.env") in candidates

    def test_env_candidate_paths_include_root_and_package_paths_in_source_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Source runs should keep searching the cwd, project root, and package dir."""
        monkeypatch.setattr(config_module, "__file__", "/repo/whisper_tray/config.py")
        monkeypatch.delattr(config_module.sys, "frozen", raising=False)
        monkeypatch.setattr(
            config_module.Path,
            "cwd",
            staticmethod(lambda: Path("/repo")),
        )

        candidates = config_module._env_candidate_paths()

        assert candidates[0] == Path("/repo/.env")
        assert Path("/repo/whisper_tray/.env") in candidates
