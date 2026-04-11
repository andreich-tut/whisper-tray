"""Tests for overlay controller creation and fallback behavior."""

from __future__ import annotations

import sys
import threading
from typing import Any

import pytest

from whisper_tray.adapters.overlay.controller import create_overlay_controller
from whisper_tray.core.overlay import NullOverlayController, OverlaySettings
from whisper_tray.state import AppState, AppStatePresenter, AppStateSnapshot


class RecordingRuntime:
    """Minimal runtime that records forwarded presentations."""

    def __init__(
        self,
        commands: Any,
        settings: OverlaySettings,
        seen: list[tuple[str, str, Any]],
        received: threading.Event,
    ) -> None:
        self._commands = commands
        self._position = settings.position
        self._screen_target = settings.screen_target
        self._seen = seen
        self._received = received

    def run(self, startup_callback: Any) -> None:
        """Drain commands until the controller requests shutdown."""
        startup_callback(True)
        while True:
            command = self._commands.get(timeout=1.0)
            if command.kind.value == "close":
                return

            self._seen.append(
                (self._position, self._screen_target, command.presentation)
            )
            self._received.set()


class FailingRuntime:
    """Runtime stub that fails during startup."""

    def __init__(
        self,
        commands: Any,
        settings: OverlaySettings,
    ) -> None:
        self._commands = commands
        self._position = settings.position
        self._screen_target = settings.screen_target

    def run(self, startup_callback: Any) -> None:
        """Signal startup failure and raise like a broken Qt runtime."""
        startup_callback(False)
        raise RuntimeError("overlay boot failed")


def test_create_overlay_controller_returns_null_when_disabled() -> None:
    """Disabled overlay should not start any UI backend."""
    controller = create_overlay_controller(
        OverlaySettings(
            enabled=False,
            position="top-left",
            screen_target="primary",
        ),
    )

    assert isinstance(controller, NullOverlayController)


def test_create_overlay_controller_falls_back_when_backend_module_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing optional UI dependency should degrade to the no-op controller."""
    monkeypatch.setattr(
        "whisper_tray.adapters.overlay.controller._pyside6_is_available",
        lambda: True,
    )
    monkeypatch.setitem(sys.modules, "whisper_tray.adapters.overlay.qt.runtime", None)

    controller = create_overlay_controller(
        OverlaySettings(
            enabled=True,
            position="top-left",
            screen_target="primary",
        ),
    )

    assert isinstance(controller, NullOverlayController)


def test_create_overlay_controller_falls_back_when_pyside6_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing PySide6 should short-circuit before starting a UI thread."""
    monkeypatch.setattr(
        "whisper_tray.adapters.overlay.controller._pyside6_is_available",
        lambda: False,
    )

    controller = create_overlay_controller(
        OverlaySettings(
            enabled=True,
            position="bottom-right",
            screen_target="primary",
        ),
    )

    assert isinstance(controller, NullOverlayController)


def test_threaded_overlay_controller_forwards_state_updates() -> None:
    """Enabled overlays should forward presentations to the runtime thread."""
    seen: list[tuple[str, str, object]] = []
    received = threading.Event()

    def runtime_factory(
        commands: object,
        settings: OverlaySettings,
    ) -> RecordingRuntime:
        return RecordingRuntime(
            commands,
            settings,
            seen,
            received,
        )

    controller = create_overlay_controller(
        OverlaySettings(
            enabled=True,
            position="top-left",
            screen_target="cursor",
        ),
        runtime_factory=runtime_factory,
    )
    presenter = AppStatePresenter()
    presentation = presenter.present(
        AppStateSnapshot(state=AppState.READY, device="cpu")
    )

    controller.show_state(presentation)

    assert received.wait(timeout=1.0) is True
    controller.close()

    assert seen == [("top-left", "cursor", presentation)]


def test_create_overlay_controller_falls_back_when_runtime_startup_fails() -> None:
    """Broken UI boot should degrade to the no-op controller."""
    controller = create_overlay_controller(
        OverlaySettings(
            enabled=True,
            position="top-left",
            screen_target="primary",
        ),
        runtime_factory=FailingRuntime,
    )

    assert isinstance(controller, NullOverlayController)
