"""Internal backend protocols used by the app layer."""

from __future__ import annotations

from typing import Protocol

import numpy as np


class RecorderBackend(Protocol):
    """Audio capture backend used by the recording workflow."""

    def start_recording(self) -> None:
        """Start capturing audio."""

    def stop_recording(self) -> np.ndarray:
        """Stop capturing audio and return the recorded samples."""

    @property
    def is_recording(self) -> bool:
        """Return whether capture is currently active."""


class TranscriberBackend(Protocol):
    """Speech-to-text backend used by the transcription workflow."""

    def load_model(self) -> None:
        """Load or warm the transcription model."""

    def transcribe(
        self,
        audio_data: np.ndarray,
        language: str | None = None,
    ) -> str | None:
        """Transcribe a chunk of recorded audio."""

    @property
    def device(self) -> str:
        """Return the active inference device."""

    @property
    def is_ready(self) -> bool:
        """Return whether the backend is ready to transcribe."""


class ClipboardPasteBackend(Protocol):
    """Clipboard backend that can copy text and optionally paste it."""

    def copy_and_paste(self, text: str) -> object | None:
        """Copy the transcript and optionally trigger paste injection."""

    def owns_clipboard(self) -> bool:
        """Return whether the app still owns the current clipboard contents."""

    def toggle_auto_paste(self) -> bool:
        """Toggle auto-paste behavior and return the new state."""

    @property
    def auto_paste(self) -> bool:
        """Return whether auto-paste is currently enabled."""


class HotkeyBackend(Protocol):
    """Global-hotkey backend used by the app lifecycle."""

    def start(self) -> None:
        """Start listening for the configured hotkey."""

    def stop(self) -> None:
        """Stop listening for the configured hotkey."""

    @property
    def is_running(self) -> bool:
        """Return whether the backend is currently active."""
