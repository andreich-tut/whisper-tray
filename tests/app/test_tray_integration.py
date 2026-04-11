"""App-level integration tests for tray state, actions, and runtime selection."""

from __future__ import annotations

import queue
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from whisper_tray.adapters.tray import PystrayTrayRuntime, QtTrayRuntime, TrayRuntime
from whisper_tray.adapters.tray.icon import TrayIcon
from whisper_tray.app import OVERLAY_INSTALL_MESSAGE, WhisperTrayApp
from whisper_tray.core.overlay import NullOverlayController, OverlaySettings
from whisper_tray.state import (
    AppState,
    AppStatePresentation,
    AppStatePresenter,
    AppStateSnapshot,
)


class StrictFakeIcon:
    """Minimal icon stub that only allows the pystray attributes we expect."""

    __slots__ = ("icon", "title", "notifications", "menu_updates")

    def __init__(self) -> None:
        self.icon = None
        self.title = ""
        self.notifications: list[str] = []
        self.menu_updates = 0

    def notify(self, message: str) -> None:
        """Record tray notifications instead of showing them."""
        self.notifications.append(message)

    def update_menu(self) -> None:
        """Record menu refresh requests."""
        self.menu_updates += 1


class RecordingOverlay:
    """Simple overlay stub for app state fan-out tests."""

    def __init__(self) -> None:
        self.presentations: list[Any] = []
        self.closed: bool = False

    def show_state(self, presentation: Any) -> None:
        """Record the latest presentation."""
        self.presentations.append(presentation)

    def close(self) -> None:
        """Record cleanup for overlay lifecycle assertions."""
        self.closed = True


def _make_presentation(state: AppState) -> AppStatePresentation:
    """Build a minimal AppStatePresentation for test use."""
    return AppStatePresentation(
        state=state,
        tray_title=state.value,
        overlay_badge="",
        overlay_primary="",
        overlay_secondary=None,
        icon_color="gray",
        overlay_hint=None,
    )


class FailingQtRuntime(QtTrayRuntime):
    """Qt tray runtime stub that fails during prepare."""

    def prepare(self, app: WhisperTrayApp) -> None:
        """Raise like a broken shared Qt tray startup."""
        raise RuntimeError("qt tray failed to prepare")


class RecordingPystrayRuntime(PystrayTrayRuntime):
    """Pystray runtime stub that records fallback preparation."""

    def __init__(self) -> None:
        self.prepared_apps: list[WhisperTrayApp] = []

    def prepare(self, app: WhisperTrayApp) -> None:
        """Record which app instance prepared the fallback runtime."""
        self.prepared_apps.append(app)


def _build_app(
    *,
    state: AppState,
    device: str = "cpu",
    overlay_enabled: bool = False,
    overlay_position: str = "bottom-right",
    overlay_screen: str = "primary",
    overlay_auto_hide_seconds: float = 1.5,
    overlay_density: str = "detailed",
    tray_backend: str = "auto",
) -> WhisperTrayApp:
    """Create a lightweight app instance without running subsystem init."""
    app = WhisperTrayApp.__new__(WhisperTrayApp)
    app._tray_icon = TrayIcon()
    app._tray_icon_ref = StrictFakeIcon()
    app._tray_update_lock = threading.Lock()
    app._processing_flash_on = True
    app._transcription_queue = queue.Queue()
    app._model_load_complete = threading.Event()
    app._transcriber = SimpleNamespace(  # type: ignore[assignment]
        is_ready=state is not AppState.LOADING_MODEL,
        device=device,
    )
    app.config = SimpleNamespace(  # type: ignore[assignment]
        hotkey=SimpleNamespace(hotkey={"ctrl", "shift", "space"}),
        overlay=SimpleNamespace(
            enabled=overlay_enabled,
            position=overlay_position,
            screen=overlay_screen,
            auto_hide_seconds=overlay_auto_hide_seconds,
            density=overlay_density,
        ),
        ui=SimpleNamespace(tray_backend=tray_backend),
    )
    app._overlay = RecordingOverlay()
    app._tray_runtime = None
    app._state_presenter = AppStatePresenter(
        ready_auto_hide_seconds=overlay_auto_hide_seconds,
        overlay_density=overlay_density,
    )
    app._state_snapshot = AppStateSnapshot(state=state, device=device)
    app._state_presentation = app._state_presenter.present(app._state_snapshot)
    return app


class TestTrayIconUpdates:
    """Tests for tray icon and title updates from app state."""

    def test_update_tray_icon_sets_ready_title(self) -> None:
        """Ready state should update both icon image and title."""
        app = _build_app(state=AppState.READY, device="cpu")

        app._update_tray_icon()

        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "WhisperTray (CPU mode) - Ready"
        assert app._tray_icon_ref.icon is not None

    def test_update_tray_icon_sets_loading_title(self) -> None:
        """Loading state should keep the loading hover text."""
        app = _build_app(state=AppState.LOADING_MODEL)

        app._update_tray_icon()

        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "Loading model..."
        assert app._tray_icon_ref.icon is not None

    def test_update_tray_icon_sets_processing_title(self) -> None:
        """Processing state should surface the processing hover text."""
        app = _build_app(state=AppState.PROCESSING)

        app._update_tray_icon()

        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "Processing..."
        assert app._tray_icon_ref.icon is not None

    def test_get_idle_state_prefers_processing_when_worker_busy(self) -> None:
        """Busy transcription work should keep the app in processing state."""
        app = _build_app(state=AppState.READY)
        app._transcription_queue.put(("audio", "en"))

        assert app._get_idle_state() is AppState.PROCESSING

    def test_on_state_changed_forwards_presentation_to_overlay(self) -> None:
        """Shared state changes should update the overlay presentation."""
        app = _build_app(state=AppState.LOADING_MODEL)
        overlay = RecordingOverlay()
        app._overlay = overlay
        app._state_presenter = AppStatePresenter(hotkey_label="Ctrl+Shift+Space")

        app._on_state_changed(AppStateSnapshot(state=AppState.READY, device="cpu"))

        assert (
            overlay.presentations[0].overlay_primary
            == "Hold Ctrl+Shift+Space to dictate."
        )
        assert app._tray_icon_ref is not None
        assert app._tray_icon_ref.title == "WhisperTray (CPU mode) - Ready"


class TestOverlayActions:
    """Tests for overlay toggle, position, screen, auto-hide, and density actions."""

    def test_toggle_overlay_recreates_live_overlay(self) -> None:
        """Enabling the overlay should create a live controller and refresh the menu."""
        app = _build_app(state=AppState.READY)
        live_overlay = RecordingOverlay()
        created: list[OverlaySettings] = []

        def fake_create_overlay_controller(settings: OverlaySettings) -> object:
            created.append(settings)
            return live_overlay if settings.enabled else NullOverlayController()

        app._tray_runtime = SimpleNamespace(
            create_overlay_controller=fake_create_overlay_controller
        )

        assert app._tray_icon_ref is not None
        original_overlay: Any = app._overlay
        app._on_toggle_overlay(app._tray_icon_ref, None)

        assert app.config.overlay.enabled is True
        assert created == [
            OverlaySettings(
                enabled=True,
                position="bottom-right",
                screen_target="primary",
            )
        ]
        assert original_overlay.closed is True
        pres = live_overlay.presentations[0]
        assert pres.overlay_primary == "Hold Ctrl+Shift+Space to dictate."
        assert app._overlay is live_overlay
        msg = "Overlay enabled (Bottom Right)"
        assert app._tray_icon_ref.notifications == [msg]
        assert app._tray_icon_ref.menu_updates == 1

    def test_toggle_overlay_rolls_back_when_ui_backend_missing(self) -> None:
        """Requested overlays should fall back cleanly when Qt is unavailable."""
        app = _build_app(state=AppState.READY)

        app._tray_runtime = SimpleNamespace(
            create_overlay_controller=lambda settings: NullOverlayController()
        )

        assert app._tray_icon_ref is not None
        original_overlay: Any = app._overlay
        app._on_toggle_overlay(app._tray_icon_ref, None)

        assert app.config.overlay.enabled is False
        assert original_overlay.closed is True
        assert isinstance(app._overlay, NullOverlayController)
        assert app._tray_icon_ref.notifications == [
            'Overlay unavailable. Install the UI extras with `pip install -e ".[ui]"`.'
        ]
        assert app._tray_icon_ref.menu_updates == 1

    def test_set_overlay_position_restarts_live_overlay(self) -> None:
        """Changing overlay position should restart the live overlay."""
        app = _build_app(state=AppState.READY, overlay_enabled=True)
        replacement_overlay = RecordingOverlay()
        created: list[OverlaySettings] = []

        def fake_create_overlay_controller(settings: OverlaySettings) -> object:
            created.append(settings)
            return replacement_overlay if settings.enabled else NullOverlayController()

        app._tray_runtime = SimpleNamespace(
            create_overlay_controller=fake_create_overlay_controller
        )

        assert app._tray_icon_ref is not None
        original_overlay: Any = app._overlay
        app._on_set_overlay_position("top-left", app._tray_icon_ref, None)

        assert app.config.overlay.position == "top-left"
        assert created == [
            OverlaySettings(
                enabled=True,
                position="top-left",
                screen_target="primary",
            )
        ]
        assert original_overlay.closed is True
        pres = replacement_overlay.presentations[0]
        assert pres.overlay_primary == "Hold Ctrl+Shift+Space to dictate."
        assert app._overlay is replacement_overlay
        assert app._tray_icon_ref.notifications == ["Overlay position: Top Left"]
        assert app._tray_icon_ref.menu_updates == 1

    def test_set_overlay_screen_restarts_live_overlay(self) -> None:
        """Changing overlay display should restart the live overlay on that target."""
        app = _build_app(state=AppState.READY, overlay_enabled=True)
        replacement_overlay = RecordingOverlay()
        created: list[OverlaySettings] = []

        def fake_create_overlay_controller(settings: OverlaySettings) -> object:
            created.append(settings)
            return replacement_overlay if settings.enabled else NullOverlayController()

        app._tray_runtime = SimpleNamespace(
            create_overlay_controller=fake_create_overlay_controller
        )

        assert app._tray_icon_ref is not None
        original_overlay: Any = app._overlay
        app._on_set_overlay_screen("cursor", app._tray_icon_ref, None)

        assert app.config.overlay.screen == "cursor"
        assert created == [
            OverlaySettings(
                enabled=True,
                position="bottom-right",
                screen_target="cursor",
            )
        ]
        assert original_overlay.closed is True
        pres = replacement_overlay.presentations[0]
        assert pres.overlay_primary == "Hold Ctrl+Shift+Space to dictate."
        assert app._overlay is replacement_overlay
        assert app._tray_icon_ref.notifications == ["Overlay display: Cursor Display"]
        assert app._tray_icon_ref.menu_updates == 1

    def test_set_overlay_auto_hide_updates_ready_presentation(self) -> None:
        """Changing the ready timeout should rerender the current presentation."""
        app = _build_app(state=AppState.READY)

        assert app._tray_icon_ref is not None
        app._on_set_overlay_auto_hide(0.0, app._tray_icon_ref, None)

        assert app.config.overlay.auto_hide_seconds == 0.0
        assert app._state_presentation.overlay_auto_hide_seconds is None
        pres = app._overlay.presentations[-1]  # type: ignore[attr-defined]
        assert pres.overlay_auto_hide_seconds is None
        assert app._tray_icon_ref.notifications == [
            "Overlay ready auto-hide: Stay Visible"
        ]
        assert app._tray_icon_ref.menu_updates == 1

    def test_set_overlay_density_updates_current_presentation(self) -> None:
        """Changing overlay density should rerender the current presentation."""
        app = _build_app(state=AppState.READY)

        assert app._tray_icon_ref is not None
        app._on_set_overlay_density("compact", app._tray_icon_ref, None)

        assert app.config.overlay.density == "compact"
        assert app._state_presentation.overlay_density == "compact"
        assert app._state_presentation.overlay_secondary is None
        pres = app._overlay.presentations[-1]  # type: ignore[attr-defined]
        assert pres.overlay_secondary is None
        assert app._tray_icon_ref.notifications == ["Overlay view: Compact"]
        assert app._tray_icon_ref.menu_updates == 1


class TestTrayRuntimeSelection:
    """Tests for tray runtime backend selection and fallback behavior."""

    def test_create_tray_runtime_prefers_qt_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PySide6 installs should opt into the unified Qt tray runtime."""
        app = _build_app(state=AppState.READY)
        monkeypatch.setattr("whisper_tray.app.should_use_qt_tray", lambda: True)

        runtime = app._create_tray_runtime()

        assert isinstance(runtime, QtTrayRuntime)

    def test_create_tray_runtime_falls_back_to_pystray(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing Qt should keep the existing pystray runtime in place."""
        app = _build_app(state=AppState.READY)
        monkeypatch.setattr("whisper_tray.app.should_use_qt_tray", lambda: False)

        runtime = app._create_tray_runtime()

        assert isinstance(runtime, PystrayTrayRuntime)

    def test_create_tray_runtime_honors_pystray_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit pystray selection should skip Qt even when it is available."""
        app = _build_app(state=AppState.READY, tray_backend="pystray")
        monkeypatch.setattr("whisper_tray.app.should_use_qt_tray", lambda: True)

        runtime = app._create_tray_runtime()

        assert isinstance(runtime, PystrayTrayRuntime)

    def test_create_tray_runtime_logs_and_falls_back_when_qt_forced(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Explicit Qt selection should degrade safely when PySide6 is unavailable."""
        app = _build_app(state=AppState.READY, tray_backend="qt")
        monkeypatch.setattr("whisper_tray.app.should_use_qt_tray", lambda: False)

        runtime = app._create_tray_runtime()

        assert isinstance(runtime, PystrayTrayRuntime)
        assert "TRAY_BACKEND=qt requested" in caplog.text

    def test_prepare_tray_runtime_falls_back_to_pystray_without_disabling_overlay(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Qt tray startup failures keep overlay settings for pystray fallback."""
        app = _build_app(state=AppState.READY, overlay_enabled=True)
        failing_qt_runtime = FailingQtRuntime()
        fallback_runtime = RecordingPystrayRuntime()

        app._create_tray_runtime = (  # type: ignore[method-assign]
            lambda: failing_qt_runtime
        )
        monkeypatch.setattr(
            "whisper_tray.app.PystrayTrayRuntime",
            lambda: fallback_runtime,
        )

        app._prepare_tray_runtime()

        assert app._tray_runtime is fallback_runtime
        assert fallback_runtime.prepared_apps == [app]
        assert app.config.overlay.enabled is True

    def test_run_notifies_when_overlay_requested_but_unavailable(self) -> None:
        """Startup should surface overlay install failures."""
        app = _build_app(state=AppState.READY, overlay_enabled=True)
        app.config.hotkey.auto_paste = True

        class FakeTrayRuntime(TrayRuntime):
            """Minimal tray runtime stub for run loop tests."""

            def run(self) -> None:
                """No-op run implementation."""

            def prepare(self, app: WhisperTrayApp) -> None:
                """No-op prepare implementation."""

            def create_overlay_controller(
                self,
                settings: OverlaySettings,
            ) -> Any:
                """No-op overlay controller creation."""
                del settings
                return NullOverlayController()

        app._tray_runtime = FakeTrayRuntime()
        app._prepare_tray_runtime = lambda: None  # type: ignore[method-assign]

        class FakeApplyOverlaySettings:
            """Callable to mock _apply_overlay_settings."""

            def __call__(self, *, render_current_state: bool = True) -> bool:
                return False

        app._apply_overlay_settings = (  # type: ignore[method-assign]
            FakeApplyOverlaySettings()
        )
        app._start_worker = lambda: None  # type: ignore[method-assign]
        app._stop_worker = lambda: None  # type: ignore[method-assign]
        app._start_clipboard_monitor = lambda: None  # type: ignore[method-assign]
        app._stop_clipboard_monitor = lambda: None  # type: ignore[method-assign]
        app._setup_hotkey_listener = lambda: None  # type: ignore[method-assign]
        app._load_model_in_background = lambda: None  # type: ignore[method-assign]
        app._hotkey_listener = None
        app._overlay = RecordingOverlay()

        assert app._tray_icon_ref is not None

        app.run()

        assert app._tray_icon_ref.notifications == [OVERLAY_INSTALL_MESSAGE]
