"""Hotkey recording and idle-state helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from whisper_tray.state import AppState

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

logger = logging.getLogger(__name__)


class RecordingCoordinator:
    """Handle hotkey press/release events and determine idle state."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def get_idle_state(self) -> AppState:
        """Return the best non-recording state for the current app conditions."""
        if self._app._transcription_queue.unfinished_tasks > 0:
            return AppState.PROCESSING
        if self._app._transcriber.is_ready:
            return AppState.READY
        if self._app._model_load_complete.is_set():
            return AppState.ERROR
        return AppState.LOADING_MODEL

    def on_hotkey_pressed(self) -> None:
        """Handle hotkey press events."""
        if not self._app._transcriber.is_ready:
            logger.info("Model not ready, ignoring hotkey")
            if self._app._model_load_complete.is_set():
                self._app._publish_state(
                    AppState.ERROR, message="Model failed to load."
                )
            return

        try:
            self._app._recorder.start_recording()
            logger.info("Recording started...")
            self._app._publish_state(AppState.RECORDING)
        except Exception as exc:
            logger.error("Failed to start recording on hotkey press: %s", exc)
            self._app._publish_state(
                AppState.ERROR,
                message="Recording failed. Try closing apps or using DEVICE=cpu.",
            )
            self._app._notify_user(
                "Recording failed: insufficient memory. "
                "Try closing apps or using DEVICE=cpu"
            )

    def on_hotkey_released(self) -> None:
        """Handle hotkey release events."""
        audio_data = self._app._recorder.stop_recording()
        logger.info("Recording stopped. Captured %s samples.", len(audio_data))

        duration = len(audio_data) / self._app.config.audio.sample_rate
        if duration < self._app.config.audio.min_recording_duration:
            logger.info(
                "Ignoring short recording (%0.2fs < %ss)",
                duration,
                self._app.config.audio.min_recording_duration,
            )
            self._app._publish_state(self.get_idle_state())
            return

        if self._app._transcription_queue.unfinished_tasks >= 1:
            logger.info("Transcription busy, dropping this utterance")
            self._app._publish_state(self.get_idle_state())
            return

        self._app._start_flash_timer()
        self._app._transcription_queue.put((audio_data, self._app._current_language))
