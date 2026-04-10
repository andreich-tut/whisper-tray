"""Tests for audio recording module."""

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from whisper_tray.audio.recorder import AudioRecorder
from whisper_tray.config import AudioConfig


@pytest.fixture(autouse=True)
def _clear_audio_env() -> None:
    """Keep recorder tests independent from config-focused env overrides."""
    env_vars = [
        "SAMPLE_RATE",
        "MIN_RECORDING_DURATION",
        "VAD_THRESHOLD",
        "VAD_SILENCE_DURATION_MS",
    ]
    saved = {var: os.environ.pop(var, None) for var in env_vars}
    try:
        yield
    finally:
        for var, value in saved.items():
            if value is not None:
                os.environ[var] = value


class TestAudioRecorder:
    """Test audio recorder."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default config."""
        recorder = AudioRecorder()
        assert recorder.config.sample_rate == 16000

    def test_init_with_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = AudioConfig(sample_rate=44100)
        recorder = AudioRecorder(config)
        assert recorder.config.sample_rate == 44100

    def test_not_recording_initially(self) -> None:
        """Test that recorder is not recording initially."""
        recorder = AudioRecorder()
        assert recorder.is_recording is False

    @patch("whisper_tray.audio.recorder.sd")
    def test_start_recording(self, mock_sd: MagicMock) -> None:
        """Test starting recording."""
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start_recording()

        mock_sd.InputStream.assert_called_once()
        mock_stream.start.assert_called_once()
        assert recorder.is_recording is True

    @patch("whisper_tray.audio.recorder.sd")
    def test_stop_recording(self, mock_sd: MagicMock) -> None:
        """Test stopping recording."""
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start_recording()
        audio_data = recorder.stop_recording()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert isinstance(audio_data, np.ndarray)
