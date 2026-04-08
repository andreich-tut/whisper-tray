"""
Audio recording module.

Handles microphone input recording using sounddevice.
"""

from __future__ import annotations

import logging
import queue
from typing import Optional

import numpy as np
import sounddevice as sd

from whisper_tray.config import AudioConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Manages audio recording from the default microphone."""

    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        """
        Initialize audio recorder.

        Args:
            config: Audio configuration. Uses defaults if None.
        """
        self.config = config or AudioConfig()
        self._audio_queue: queue.Queue = queue.Queue()
        self._current_stream: Optional[sd.InputStream] = None

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
    ) -> None:
        """Callback for audio stream - pushes chunks to queue."""
        if status:
            logger.info(f"Audio stream status: {status}")
        self._audio_queue.put(indata.copy())

    def start_recording(self) -> None:
        """Start audio recording stream."""
        # Clear any old data
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start stream
        try:
            self._current_stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._current_stream.start()
            logger.info("Audio recording stream started successfully")
        except Exception as e:
            logger.error(f"Failed to start audio recording: {e}")
            raise

    def stop_recording(self) -> np.ndarray:
        """
        Stop recording and return concatenated audio.

        Returns:
            Flat numpy array of all recorded audio samples.
        """
        if self._current_stream is None:
            logger.warning("No active stream to stop")
            return np.array([], dtype=np.float32)

        # Stop and close stream
        self._current_stream.stop()
        self._current_stream.close()
        self._current_stream = None

        # Collect all chunks
        chunks = []
        while not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get_nowait()
                chunks.append(chunk)
            except queue.Empty:
                break

        # Concatenate into single array
        if chunks:
            audio_data = np.concatenate(chunks, axis=0)
            return audio_data.flatten()
        else:
            return np.array([], dtype=np.float32)

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._current_stream is not None
