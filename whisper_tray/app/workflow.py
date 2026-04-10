"""Workflow helpers for recording, transcription, and background tasks."""

from __future__ import annotations

import logging
import queue
import threading
from typing import TYPE_CHECKING

import numpy as np

from whisper_tray.state import AppState, AppStateSnapshot

if TYPE_CHECKING:
    from whisper_tray.app import WhisperTrayApp

logger = logging.getLogger(__name__)


class AppWorkflowCoordinator:
    """Own latency-sensitive recording and transcription workflows."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def transcription_worker_loop(self) -> None:
        """Background worker that processes transcription requests one at a time."""
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

    def get_idle_state(self) -> AppState:
        """Return the best non-recording state for the current app conditions."""
        if self._app._transcription_queue.unfinished_tasks > 0:
            return AppState.PROCESSING
        if self._app._transcriber.is_ready:
            return AppState.READY
        if self._app._model_load_complete.is_set():
            return AppState.ERROR
        return AppState.LOADING_MODEL

    def clipboard_monitor_loop(self) -> None:
        """Revert the transcript state after the clipboard changes elsewhere."""
        while not self._app._clipboard_monitor_stop.wait(0.25):
            if self._app._state_snapshot.state is not AppState.TRANSCRIBED:
                continue
            if self._app._clipboard.owns_clipboard():
                continue
            self._app._publish_state(AppState.READY)

    def start_clipboard_monitor(self) -> None:
        """Start the lightweight clipboard ownership monitor."""
        self._app._clipboard_monitor_stop.clear()
        self._app._clipboard_monitor = threading.Thread(
            target=self.clipboard_monitor_loop,
            daemon=True,
            name="clipboard-monitor",
        )
        self._app._clipboard_monitor.start()

    def stop_clipboard_monitor(self) -> None:
        """Stop the clipboard ownership monitor."""
        self._app._clipboard_monitor_stop.set()
        if self._app._clipboard_monitor and self._app._clipboard_monitor.is_alive():
            self._app._clipboard_monitor.join(timeout=1.0)
        self._app._clipboard_monitor = None

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

    def start_flash_timer(self) -> None:
        """Start background thread that flashes the icon during processing."""
        self._app._processing_flash_on = True
        self._app._flash_event.clear()
        self._app._publish_state(AppState.PROCESSING)

        def flash_loop() -> None:
            while not self._app._flash_event.is_set():
                self._app._processing_flash_on = not self._app._processing_flash_on
                self._app._update_tray_icon()
                self._app._flash_event.wait(0.5)

        self._app._flash_timer = threading.Thread(
            target=flash_loop,
            daemon=True,
            name="tray-processing-flash",
        )
        self._app._flash_timer.start()

    def stop_flash_timer(
        self,
        next_snapshot: AppStateSnapshot | None = None,
    ) -> None:
        """Stop the flash timer and publish the next stable state."""
        self._app._flash_event.set()
        if self._app._flash_timer and self._app._flash_timer.is_alive():
            self._app._flash_timer.join(timeout=1.0)
        self._app._flash_timer = None
        self._app._processing_flash_on = False
        self._app._publish_snapshot(
            next_snapshot or self._app._build_snapshot(self.get_idle_state())
        )

    def load_model_in_background(self) -> None:
        """Load the Whisper model in a background thread."""
        self._app._transcriber.load_model()
        self._app._model_load_complete.set()
        if self._app._transcriber.is_ready:
            self._app._publish_state(AppState.READY)
            return
        self._app._publish_state(AppState.ERROR, message="Model failed to load.")
