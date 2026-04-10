"""Tests for configuration env-file discovery."""

import os
from pathlib import Path
from typing import Generator

import pytest

import whisper_tray.config.env as config_env


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


class TestEnvDiscovery:
    """Test `.env` lookup behavior across source and frozen runs."""

    def test_env_candidate_paths_include_package_env_for_frozen_build(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Frozen builds should look next to the exe and in repo-style package paths."""
        monkeypatch.setattr(
            config_env,
            "__file__",
            "/repo/whisper_tray/config/env.py",
        )
        monkeypatch.setattr(config_env.sys, "frozen", True, raising=False)
        monkeypatch.setattr(
            config_env.sys,
            "executable",
            "/repo/dist/WhisperTray/WhisperTray.exe",
        )
        monkeypatch.setattr(
            config_env.Path,
            "cwd",
            staticmethod(lambda: Path("/repo/runtime")),
        )

        candidates = config_env._env_candidate_paths()

        assert Path("/repo/dist/WhisperTray/.env") in candidates
        assert Path("/repo/.env") in candidates
        assert Path("/repo/whisper_tray/.env") in candidates

    def test_env_candidate_paths_include_root_and_package_paths_in_source_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Source runs should keep searching the cwd, project root, and package dir."""
        monkeypatch.setattr(
            config_env,
            "__file__",
            "/repo/whisper_tray/config/env.py",
        )
        monkeypatch.delattr(config_env.sys, "frozen", raising=False)
        monkeypatch.setattr(
            config_env.Path,
            "cwd",
            staticmethod(lambda: Path("/repo")),
        )

        candidates = config_env._env_candidate_paths()

        assert candidates[0] == Path("/repo/.env")
        assert Path("/repo/whisper_tray/.env") in candidates
