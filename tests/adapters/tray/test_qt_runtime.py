"""Tests for the shared Qt tray overlay host."""

from __future__ import annotations

import sys
from typing import Any, Callable

import pytest

from whisper_tray.adapters.tray import QtOverlayHost
from whisper_tray.core.overlay import OverlaySettings
from whisper_tray.state import AppState, AppStatePresentation


class FakeQtSignal:
    """Minimal Qt-like signal for overlay host tests."""

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


def test_qt_overlay_host_reuses_single_window_for_anchor_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared Qt overlay host should keep one window and update its anchor."""
    created_windows: list[FakeOverlayWindow] = []

    class FakeRuntimeOverlayWindow(FakeOverlayWindow):
        """Replacement overlay window used to isolate the Qt host test."""

        def __init__(self, position: str, screen_target: str) -> None:
            super().__init__(position=position, screen_target=screen_target)
            created_windows.append(self)

    fake_qtcore = __import__("types").SimpleNamespace(
        QObject=FakeQtObject, Signal=fake_qt_signal
    )
    monkeypatch.setitem(sys.modules, "PySide6", __import__("types").SimpleNamespace())
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", fake_qtcore)
    monkeypatch.setattr(
        "whisper_tray.adapters.tray.qt.overlay_host.OverlayWindow",
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
