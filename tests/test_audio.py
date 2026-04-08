"""Tests for audio recording module."""

from unittest.mock import MagicMock, patch

import numpy as np

from whisper_tray.audio.recorder import AudioRecorder
from whisper_tray.config import AudioConfig


class TestAudioRecorder:
    """Test audio recorder."""

    def test_init_with_defaults(self):
        """Test initialization with default config."""
        recorder = AudioRecorder()
        assert recorder.config.sample_rate == 16000

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = AudioConfig(sample_rate=44100)
        recorder = AudioRecorder(config)
        assert recorder.config.sample_rate == 44100

    def test_not_recording_initially(self):
        """Test that recorder is not recording initially."""
        recorder = AudioRecorder()
        assert recorder.is_recording is False

    @patch("whisper_tray.audio.recorder.sd")
    def test_start_recording(self, mock_sd):
        """Test starting recording."""
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start_recording()

        mock_sd.InputStream.assert_called_once()
        mock_stream.start.assert_called_once()
        assert recorder.is_recording is True

    @patch("whisper_tray.audio.recorder.sd")
    def test_stop_recording(self, mock_sd):
        """Test stopping recording."""
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start_recording()
        audio_data = recorder.stop_recording()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert isinstance(audio_data, np.ndarray)
