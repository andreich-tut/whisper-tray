"""Tests for tray state rendering and updates."""

import threading
from types import SimpleNamespace

from whisper_tray.app import WhisperTrayApp
from whisper_tray.tray.icon import TrayIcon


class StrictFakeIcon:
    """Minimal icon stub that only allows the pystray attributes we expect."""

    __slots__ = ("icon", "title")

    def __init__(self) -> None:
        self.icon = None
        self.title = ""


def _build_app(
    *,
    model_ready: bool,
    device: str = "cpu",
    is_recording: bool = False,
    is_processing: bool = False,
) -> WhisperTrayApp:
    """Create a lightweight app instance without running subsystem init."""
    app = WhisperTrayApp.__new__(WhisperTrayApp)
    app._tray_icon = TrayIcon()
    app._tray_icon_ref = StrictFakeIcon()
    app._tray_update_lock = threading.Lock()
    app._is_recording = is_recording
    app._is_processing = is_processing
    app._transcriber = SimpleNamespace(  # type: ignore[assignment]
        is_ready=model_ready, device=device
    )
    return app


class TestWhisperTrayApp:
    """Test tray state updates on the app orchestrator."""

    def test_update_tray_icon_sets_ready_title(self) -> None:
        """Ready state should update both icon image and title."""
        app = _build_app(model_ready=True, device="cpu")

        app._update_tray_icon()

        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "WhisperTray (CPU mode) - Ready"
        assert app._tray_icon_ref.icon is not None

    def test_update_tray_icon_sets_loading_title(self) -> None:
        """Loading state should keep the loading hover text."""
        app = _build_app(model_ready=False)

        app._update_tray_icon()

        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "Loading model..."
        assert app._tray_icon_ref.icon is not None

    def test_update_tray_icon_sets_processing_title(self) -> None:
        """Processing state should surface the processing hover text."""
        app = _build_app(model_ready=True, is_processing=True)

        app._update_tray_icon()

        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "Processing..."
        assert app._tray_icon_ref.icon is not None
