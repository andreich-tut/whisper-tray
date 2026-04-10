"""Workflow coordination package for recording, transcription, and background tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from whisper_tray.app.workflow.clipboard_monitor import ClipboardMonitorCoordinator
from whisper_tray.app.workflow.flash import FlashTimerCoordinator
from whisper_tray.app.workflow.recording import RecordingCoordinator
from whisper_tray.app.workflow.worker import WorkerCoordinator
from whisper_tray.state import AppState, AppStateSnapshot

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp

__all__ = ["AppWorkflowCoordinator"]


class AppWorkflowCoordinator:
    """Coordinate recording, transcription, clipboard, and flash-timer workflows."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app
        self._worker = WorkerCoordinator(app)
        self._recording = RecordingCoordinator(app)
        self._clipboard = ClipboardMonitorCoordinator(app)
        self._flash = FlashTimerCoordinator(app)

    # --- worker ---

    def transcription_worker_loop(self) -> None:
        """Background loop that processes transcription requests one at a time."""
        self._worker.transcription_worker_loop()

    def start_worker(self) -> None:
        """Start the single transcription worker thread."""
        self._worker.start_worker()

    def stop_worker(self) -> None:
        """Stop the transcription worker and drain queue."""
        self._worker.stop_worker()

    def transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: str,
    ) -> AppStateSnapshot:
        """Transcribe audio and convert the result into a publishable snapshot."""
        return self._worker.transcribe_audio(audio_data, language)

    def load_model_in_background(self) -> None:
        """Load the Whisper model in a background thread."""
        self._worker.load_model_in_background()

    # --- recording ---

    def get_idle_state(self) -> AppState:
        """Return the best non-recording state for the current app conditions."""
        return self._recording.get_idle_state()

    def on_hotkey_pressed(self) -> None:
        """Handle hotkey press events."""
        self._recording.on_hotkey_pressed()

    def on_hotkey_released(self) -> None:
        """Handle hotkey release events."""
        self._recording.on_hotkey_released()

    # --- clipboard monitor ---

    def clipboard_monitor_loop(self) -> None:
        """Revert the transcript state after the clipboard changes elsewhere."""
        self._clipboard.clipboard_monitor_loop()

    def start_clipboard_monitor(self) -> None:
        """Start the lightweight clipboard ownership monitor."""
        self._clipboard.start_clipboard_monitor()

    def stop_clipboard_monitor(self) -> None:
        """Stop the clipboard ownership monitor."""
        self._clipboard.stop_clipboard_monitor()

    # --- flash timer ---

    def start_flash_timer(self) -> None:
        """Start the background thread that flashes the icon during processing."""
        self._flash.start_flash_timer()

    def stop_flash_timer(
        self,
        next_snapshot: AppStateSnapshot | None = None,
    ) -> None:
        """Stop the flash timer and publish the next stable state."""
        self._flash.stop_flash_timer(next_snapshot=next_snapshot)
