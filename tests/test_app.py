"""Tests for the main app transcription state flow."""

from __future__ import annotations

import queue
import threading
from types import SimpleNamespace

import numpy as np

from whisper_tray.app import WhisperTrayApp
from whisper_tray.state import AppState, AppStatePublisher, AppStateSnapshot


def test_transcription_worker_publishes_transcribed_snapshot() -> None:
    """Successful transcription should publish the transcript-aware success state."""
    app = WhisperTrayApp.__new__(WhisperTrayApp)
    app._worker_stop = threading.Event()
    app._transcription_queue = queue.Queue()
    app._transcription_queue.put((np.zeros(16, dtype=np.float32), "en"))
    app._transcriber = SimpleNamespace(device="cpu")  # type: ignore[assignment]
    app._clipboard = SimpleNamespace(  # type: ignore[assignment]
        copy_and_paste=lambda text: None,
    )
    app._flash_event = threading.Event()
    app._flash_timer = None
    app._processing_flash_on = True
    app._notify_user = lambda message: None  # type: ignore[method-assign]
    app._state_publisher = AppStatePublisher(
        AppStateSnapshot(state=AppState.PROCESSING, device="cpu")
    )
    published: list[AppStateSnapshot] = []
    app._state_publisher.subscribe(published.append)

    def transcribe(audio_data: np.ndarray, language: str) -> str:
        del audio_data, language
        app._worker_stop.set()
        return "hello from whisper tray"

    app._transcriber.transcribe = transcribe  # type: ignore[method-assign,assignment]

    app._transcription_worker_loop()

    assert published[-1] == AppStateSnapshot(
        state=AppState.TRANSCRIBED,
        device="cpu",
        transcript="hello from whisper tray",
        auto_pasted=False,
    )


def test_hotkey_flow_publishes_recording_then_processing_states() -> None:
    """Pressing and releasing the hotkey should surface live overlay states."""
    app = WhisperTrayApp.__new__(WhisperTrayApp)
    app._transcriber = SimpleNamespace(  # type: ignore[assignment]
        is_ready=True,
        device="cpu",
    )
    app._model_load_complete = threading.Event()
    app._recorder = SimpleNamespace(  # type: ignore[assignment]
        start_recording=lambda: None,
        stop_recording=lambda: np.zeros(16000, dtype=np.float32),
    )
    app._notify_user = lambda message: None  # type: ignore[method-assign]
    app._current_language = "en"
    app._transcription_queue = queue.Queue()
    app.config = SimpleNamespace(  # type: ignore[assignment]
        audio=SimpleNamespace(sample_rate=16000, min_recording_duration=0.3),
    )
    app._state_publisher = AppStatePublisher(
        AppStateSnapshot(state=AppState.READY, device="cpu")
    )
    published: list[AppStateSnapshot] = []
    app._state_publisher.subscribe(published.append)
    app._start_flash_timer = lambda: app._publish_state(  # type: ignore[method-assign]
        AppState.PROCESSING
    )

    app._on_hotkey_pressed()
    app._on_hotkey_released()

    assert [snapshot.state for snapshot in published[-2:]] == [
        AppState.RECORDING,
        AppState.PROCESSING,
    ]
    assert app._transcription_queue.get_nowait()[1] == "en"
