"""Tests for tray state rendering and updates."""

from __future__ import annotations

import queue
import sys
import threading
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from whisper_tray.app import OVERLAY_INSTALL_MESSAGE, WhisperTrayApp
from whisper_tray.overlay.controller import NullOverlayController, OverlaySettings
from whisper_tray.state import (
    AppState,
    AppStatePresentation,
    AppStatePresenter,
    AppStateSnapshot,
)
from whisper_tray.tray.icon import TrayIcon
from whisper_tray.tray.menu import TrayMenu
from whisper_tray.tray.runtime import (
    PystrayTrayRuntime,
    QtOverlayHost,
    QtTrayRuntime,
    TrayRuntime,
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


class FakeMenu(tuple):
    """Small tuple-backed pystray menu stand-in for tests."""

    def __new__(cls, *items: object) -> "FakeMenu":
        return super().__new__(cls, items)


class FakeMenuItem:
    """Minimal menu item object used to inspect labels and callbacks."""

    def __init__(
        self,
        text: str,
        action: object,
        checked: object | None = None,
        radio: bool = False,
    ) -> None:
        self.text = text
        self.action = action
        self.checked = checked
        self.radio = radio


class FakeQtSignal:
    """Minimal Qt-like signal used to test Qt tray menu wiring."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> None:
        """Record connected callbacks."""
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        """Invoke all registered callbacks."""
        for callback in self._callbacks:
            callback(*args)


class FakeQtObject:
    """Tiny QObject stand-in for signal-driven Qt host tests."""

    def __init__(self) -> None:
        """Mirror QObject's trivial construction for test doubles."""


class FakeQtSignalDescriptor:
    """Descriptor that gives each fake QObject instance its own signal."""

    def __init__(self) -> None:
        self._storage_name = ""

    def __set_name__(self, owner: type[object], name: str) -> None:
        """Remember where to store the per-instance signal."""
        del owner
        self._storage_name = f"__signal_{name}"

    def __get__(self, instance: object, owner: type[object]) -> object:
        """Create a fresh signal for each QObject instance on demand."""
        del owner
        if instance is None:
            return self

        signal = getattr(instance, self._storage_name, None)
        if signal is None:
            signal = FakeQtSignal()
            setattr(instance, self._storage_name, signal)
        return signal


def fake_qt_signal(*_types: object) -> FakeQtSignalDescriptor:
    """Build a fake Qt signal descriptor regardless of the declared payload."""
    return FakeQtSignalDescriptor()


class FakeQtAction:
    """Small QAction stand-in for menu creation tests."""

    def __init__(self, text: str, submenu: "FakeQtMenu" | None = None) -> None:
        self._text = text
        self._submenu = submenu
        self._checked = False
        self._checkable = False
        self.triggered = FakeQtSignal()

    def text(self) -> str:
        """Return the visible label."""
        return self._text

    def menu(self) -> "FakeQtMenu" | None:
        """Return the attached submenu when one exists."""
        return self._submenu

    def setCheckable(self, value: bool) -> None:
        """Record whether the action is checkable."""
        self._checkable = value

    def setChecked(self, value: bool) -> None:
        """Record the current checked state."""
        self._checked = value

    def isChecked(self) -> bool:
        """Expose the current checked state for assertions."""
        return self._checked


class FakeQtActionGroup:
    """Small QActionGroup stand-in for menu exclusivity tests."""

    def __init__(self, parent: object) -> None:
        self.parent = parent
        self.actions: list[FakeQtAction] = []
        self.exclusive = False

    def addAction(self, action: FakeQtAction) -> None:
        """Record actions registered with the group."""
        self.actions.append(action)

    def setExclusive(self, value: bool) -> None:
        """Record whether the group is exclusive."""
        self.exclusive = value


class FakeQtMenu:
    """Small QMenu stand-in for Qt tray menu tests."""

    def __init__(self, title: str = "") -> None:
        self._title = title
        self._actions: list[FakeQtAction] = []
        self.aboutToShow = FakeQtSignal()

    def addAction(self, label: str) -> FakeQtAction:
        """Append an action to the menu."""
        action = FakeQtAction(label)
        self._actions.append(action)
        return action

    def addMenu(self, label: str) -> "FakeQtMenu":
        """Append a submenu and return it."""
        submenu = FakeQtMenu(label)
        self._actions.append(FakeQtAction(label, submenu))
        return submenu

    def actions(self) -> list[FakeQtAction]:
        """Return the current actions in insertion order."""
        return self._actions


class FakeOverlayWindow:
    """Overlay window stub that records lifecycle and presentation events."""

    def __init__(self, *, position: str, screen_target: str) -> None:
        self.position = position
        self.screen_target = screen_target
        self.anchor_updates: list[tuple[str, str]] = []
        self.presentations: list[Any] = []
        self.hide_calls = 0
        self.closed = False

    def update_anchor(self, position: str, screen_target: str) -> None:
        """Record where the overlay is being anchored."""
        self.anchor_updates.append((position, screen_target))

    def show_presentation(self, presentation: Any) -> None:
        """Record each rendered presentation."""
        self.presentations.append(presentation)

    def hide_now(self) -> None:
        """Record immediate-hide requests."""
        self.hide_calls += 1

    def close(self) -> None:
        """Record full window teardown."""
        self.closed = True


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


class TestWhisperTrayApp:
    """Test tray state updates on the app orchestrator."""

    def test_tray_menu_includes_overlay_controls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Overlay enable and position controls should be present in the tray menu."""
        fake_pystray = SimpleNamespace(Menu=FakeMenu, MenuItem=FakeMenuItem)
        monkeypatch.setitem(sys.modules, "pystray", fake_pystray)

        menu = TrayMenu(
            get_overlay_enabled_state=lambda: True,
            get_overlay_position_state=lambda: "top-left",
            get_overlay_screen_state=lambda: "cursor",
            get_overlay_auto_hide_state=lambda: 0.0,
            get_overlay_density_state=lambda: "compact",
        ).create_menu()

        overlay_item = menu[2]
        overlay_menu = overlay_item.action
        enabled_item = overlay_menu[0]
        position_item = overlay_menu[1]
        display_item = overlay_menu[2]
        auto_hide_item = overlay_menu[3]
        view_item = overlay_menu[4]
        position_menu = position_item.action
        display_menu = display_item.action
        auto_hide_menu = auto_hide_item.action
        view_menu = view_item.action

        assert overlay_item.text == "Overlay"
        assert enabled_item.text == "Enabled"
        assert enabled_item.checked(None) is True
        assert position_item.text == "Position"
        assert [item.text for item in position_menu] == [
            "Top Left",
            "Top Right",
            "Bottom Left",
            "Bottom Right",
        ]
        assert all(item.radio is True for item in position_menu)
        assert position_menu[0].checked(None) is True
        assert position_menu[-1].checked(None) is False
        assert display_item.text == "Display"
        assert [item.text for item in display_menu] == [
            "Primary Display",
            "Cursor Display",
        ]
        assert all(item.radio is True for item in display_menu)
        assert display_menu[0].checked(None) is False
        assert display_menu[1].checked(None) is True
        assert auto_hide_item.text == "Ready Auto-Hide"
        assert [item.text for item in auto_hide_menu] == [
            "Stay Visible",
            "1.5 Seconds",
            "3 Seconds",
            "5 Seconds",
        ]
        assert all(item.radio is True for item in auto_hide_menu)
        assert auto_hide_menu[0].checked(None) is True
        assert auto_hide_menu[1].checked(None) is False
        assert view_item.text == "View"
        assert [item.text for item in view_menu] == ["Detailed", "Compact"]
        assert all(item.radio is True for item in view_menu)
        assert view_menu[0].checked(None) is False
        assert view_menu[1].checked(None) is True

    def test_qt_tray_menu_refreshes_overlay_checks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Qt tray menus should mirror the same dynamic overlay controls."""
        fake_qtwidgets = SimpleNamespace(QMenu=FakeQtMenu)
        fake_qtgui = SimpleNamespace(QActionGroup=FakeQtActionGroup)
        monkeypatch.setitem(sys.modules, "PySide6", SimpleNamespace())
        monkeypatch.setitem(sys.modules, "PySide6.QtGui", fake_qtgui)
        monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", fake_qtwidgets)

        state: dict[str, Any] = {
            "overlay_enabled": False,
            "overlay_position": "bottom-right",
            "overlay_screen": "primary",
            "overlay_auto_hide": 1.5,
            "overlay_density": "detailed",
        }

        menu = TrayMenu(
            get_overlay_enabled_state=lambda: state["overlay_enabled"],
            get_overlay_position_state=lambda: state["overlay_position"],
            get_overlay_screen_state=lambda: state["overlay_screen"],
            get_overlay_auto_hide_state=lambda: state["overlay_auto_hide"],
            get_overlay_density_state=lambda: state["overlay_density"],
        ).create_qt_menu(StrictFakeIcon())

        state["overlay_enabled"] = True
        state["overlay_position"] = "top-left"
        state["overlay_screen"] = "cursor"
        state["overlay_auto_hide"] = 0.0
        state["overlay_density"] = "compact"
        menu.aboutToShow.emit()

        overlay_menu = menu.actions()[2].menu()
        assert overlay_menu is not None

        enabled_action = overlay_menu.actions()[0]
        position_menu = overlay_menu.actions()[1].menu()
        display_menu = overlay_menu.actions()[2].menu()
        auto_hide_menu = overlay_menu.actions()[3].menu()
        view_menu = overlay_menu.actions()[4].menu()

        assert enabled_action.isChecked() is True
        assert (
            position_menu is not None and position_menu.actions()[0].isChecked() is True
        )
        assert (
            display_menu is not None and display_menu.actions()[1].isChecked() is True
        )
        assert (
            auto_hide_menu is not None
            and auto_hide_menu.actions()[0].isChecked() is True
        )
        assert view_menu is not None and view_menu.actions()[1].isChecked() is True
        action_groups = getattr(menu, "_action_groups")
        assert len(action_groups) == 5
        assert all(group.exclusive is True for group in action_groups)
        assert [action.text() for action in action_groups[0].actions] == [
            "English",
            "Russian",
            "Auto-Detect",
        ]

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

    def test_toggle_overlay_rolls_back_when_ui_backend_missing(
        self,
    ) -> None:
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

    def test_qt_overlay_host_reuses_single_window_for_anchor_updates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The shared Qt overlay host should keep one window and update its anchor."""
        created_windows: list[FakeOverlayWindow] = []

        class FakeRuntimeOverlayWindow(FakeOverlayWindow):
            """Replacement overlay window used to isolate the Qt host test."""

            def __init__(self, position: str, screen_target: str) -> None:
                super().__init__(position=position, screen_target=screen_target)
                created_windows.append(self)

        fake_qtcore = SimpleNamespace(QObject=FakeQtObject, Signal=fake_qt_signal)
        monkeypatch.setitem(sys.modules, "PySide6", SimpleNamespace())
        monkeypatch.setitem(sys.modules, "PySide6.QtCore", fake_qtcore)
        monkeypatch.setattr(
            "whisper_tray.overlay.pyside_overlay.OverlayWindow",
            FakeRuntimeOverlayWindow,
        )

        host = QtOverlayHost()
        assert len(created_windows) == 1

        first_controller = host.create_controller(
            OverlaySettings(
                enabled=True,
                position="bottom-right",
                screen_target="primary",
            )
        )
        first_controller.show_state(_make_presentation(AppState.READY))
        assert len(created_windows) == 1
        assert created_windows[0].anchor_updates[-1] == ("bottom-right", "primary")
        assert len(created_windows[0].presentations) == 1

        moved_controller = host.create_controller(
            OverlaySettings(
                enabled=True,
                position="top-left",
                screen_target="cursor",
            )
        )
        moved_controller.show_state(_make_presentation(AppState.PROCESSING))
        assert len(created_windows) == 1
        assert created_windows[0].anchor_updates[-1] == ("top-left", "cursor")
        assert created_windows[0].presentations[-1].state == AppState.PROCESSING

        host.close()
        assert created_windows[0].closed is True
