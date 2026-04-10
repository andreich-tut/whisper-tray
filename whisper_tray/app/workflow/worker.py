"""Transcription worker thread coordinator."""

from __future__ import annotations

import logging
import queue
import threading
from typing import TYPE_CHECKING

import numpy as np

from whisper_tray.state import AppState, AppStateSnapshot

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

logger = logging.getLogger(__name__)


class WorkerCoordinator:
    """Own the background transcription worker thread and audio transcription."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def transcription_worker_loop(self) -> None:
        """Background loop that processes transcription requests one at a time."""
        while not self._app._worker_stop.is_set():
            try:
                audio_data, lang = self._app._transcription_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            next_snapshot = self._app._build_snapshot(AppState.READY)
            try:
                next_snapshot = self.transcribe_audio(audio_data, lang)
            except Exception as exc:
                logger.error("Transcription worker error: %s", exc)
                next_snapshot = self._app._build_snapshot(
                    AppState.ERROR,
                    message=str(exc),
                )
            finally:
                self._app._transcription_queue.task_done()
                self._app._stop_flash_timer(next_snapshot=next_snapshot)

    def start_worker(self) -> None:
        """Start the single transcription worker thread."""
        self._app._worker_stop.clear()
        self._app._transcription_worker = threading.Thread(
            target=self.transcription_worker_loop,
            daemon=True,
            name="transcription-worker",
        )
        self._app._transcription_worker.start()

    def stop_worker(self) -> None:
        """Stop the transcription worker and drain queue."""
        self._app._worker_stop.set()
        self._app._flash_event.set()
        if self._app._flash_timer and self._app._flash_timer.is_alive():
            self._app._flash_timer.join(timeout=1.0)
        self._app._flash_timer = None

        while not self._app._transcription_queue.empty():
            try:
                self._app._transcription_queue.get_nowait()
                self._app._transcription_queue.task_done()
            except queue.Empty:
                break

        if self._app._transcription_worker:
            self._app._transcription_worker.join(timeout=2.0)

    def transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: str,
    ) -> AppStateSnapshot:
        """Transcribe audio and convert the result into a publishable snapshot."""
        text = self._app._transcriber.transcribe(audio_data, language)
        if not text:
            return self._app._build_snapshot(AppState.READY)

        logger.info("Recognized text: %s", text)
        paste_result = self._app._clipboard.copy_and_paste(text)
        if paste_result is not None and not paste_result.succeeded:
            self._app._notify_user("Auto-paste failed. Text is still in the clipboard.")

        return self._app._build_snapshot(
            AppState.TRANSCRIBED,
            transcript=text,
            auto_pasted=bool(paste_result and paste_result.succeeded),
        )

    def load_model_in_background(self) -> None:
        """Load the Whisper model in a background thread."""
        self._app._transcriber.load_model()
        self._app._model_load_complete.set()
        if self._app._transcriber.is_ready:
            self._app._publish_state(AppState.READY)
            return
        self._app._publish_state(AppState.ERROR, message="Model failed to load.")
