"""Tests for overlay controller behavior and fallbacks."""

import sys
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from whisper_tray.overlay.controller import (
    NullOverlayController,
    create_overlay_controller,
)
from whisper_tray.overlay.pyside_overlay import (
    _DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
    _GWL_EXSTYLE,
    _HWND_TOPMOST,
    _PROCESS_PER_MONITOR_DPI_AWARE,
    _SWP_FRAMECHANGED,
    _SWP_NOACTIVATE,
    _SWP_NOMOVE,
    _SWP_NOSIZE,
    _WS_EX_APPWINDOW,
    _WS_EX_LAYERED,
    _WS_EX_NOACTIVATE,
    _WS_EX_TOOLWINDOW,
    _WS_EX_TRANSPARENT,
    apply_windows_overlay_styles,
    create_overlay_window,
    enable_windows_per_monitor_dpi_awareness,
    geometry_contains_geometry,
    resolve_overlay_coordinates,
    resolve_overlay_layout,
    resolve_overlay_reposition_screen,
    resolve_overlay_screen,
    resolve_overlay_theme,
    resolve_windows_overlay_ex_style,
    should_use_card_shadow,
    should_use_window_opacity_fade,
    update_last_resolved_screen,
)
from whisper_tray.state import AppState, AppStatePresenter, AppStateSnapshot


class RecordingRuntime:
    """Minimal runtime that records forwarded presentations."""

    def __init__(
        self,
        commands: Any,
        position: str,
        screen_target: str,
        seen: list[tuple[str, str, Any]],
        received: threading.Event,
    ) -> None:
        self._commands = commands
        self._position = position
        self._screen_target = screen_target
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
        position: str,
        screen_target: str,
    ) -> None:
        self._commands = commands
        self._position = position
        self._screen_target = screen_target

    def run(self, startup_callback: Any) -> None:
        """Signal startup failure and raise like a broken Qt runtime."""
        startup_callback(False)
        raise RuntimeError("overlay boot failed")


class FakeUser32:
    """Tiny Win32 API stub for overlay style tests."""

    def __init__(self, initial_style: int = 0) -> None:
        self.style = initial_style
        self.get_calls: list[tuple[int, int]] = []
        self.set_calls: list[tuple[int, int, int]] = []
        self.pos_calls: list[tuple[int, int, int, int, int, int, int]] = []

    def GetWindowLongPtrW(self, hwnd: int, index: int) -> int:
        """Return the stored window style."""
        self.get_calls.append((hwnd, index))
        return self.style

    def SetWindowLongPtrW(self, hwnd: int, index: int, value: int) -> int:
        """Record the updated extended style."""
        self.set_calls.append((hwnd, index, value))
        self.style = value
        return 1

    def SetWindowPos(
        self,
        hwnd: int,
        insert_after: int,
        x: int,
        y: int,
        width: int,
        height: int,
        flags: int,
    ) -> int:
        """Record topmost/no-activate window updates."""
        self.pos_calls.append((hwnd, insert_after, x, y, width, height, flags))
        return 1


class FakeDpiUser32:
    """Tiny Win32 DPI API stub for startup-awareness tests."""

    def __init__(
        self,
        *,
        context_result: int = 1,
        legacy_result: int = 1,
    ) -> None:
        self.context_result = context_result
        self.legacy_result = legacy_result
        self.context_calls: list[int] = []
        self.legacy_calls = 0

    def SetProcessDpiAwarenessContext(self, value: int) -> int:
        """Record the modern per-monitor DPI awareness request."""
        self.context_calls.append(value)
        return self.context_result

    def SetProcessDPIAware(self) -> int:
        """Record the legacy DPI-awareness fallback."""
        self.legacy_calls += 1
        return self.legacy_result


class FakeShcore:
    """Tiny shcore.dll stub for mid-generation DPI-awareness fallback tests."""

    def __init__(self, result: int = 0) -> None:
        self.result = result
        self.calls: list[int] = []

    def SetProcessDpiAwareness(self, value: int) -> int:
        """Record the requested DPI-awareness level."""
        self.calls.append(value)
        return self.result


class FakeGeometry:
    """Tiny QRect-like stub for overlay coordinate tests."""

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def x(self) -> int:
        """Return the left edge."""
        return self._x

    def y(self) -> int:
        """Return the top edge."""
        return self._y

    def width(self) -> int:
        """Return the width."""
        return self._width

    def height(self) -> int:
        """Return the height."""
        return self._height


class FakeScreen:
    """Minimal QScreen-like object for screen fallback tests."""

    def __init__(
        self,
        *,
        geometry: FakeGeometry,
        available_geometry: FakeGeometry | None = None,
        device_pixel_ratio: float = 1.0,
    ) -> None:
        self._geometry = geometry
        self._available_geometry = available_geometry or geometry
        self._device_pixel_ratio = device_pixel_ratio

    def geometry(self) -> FakeGeometry:
        """Return the full screen geometry."""
        return self._geometry

    def availableGeometry(self) -> FakeGeometry:
        """Return the work-area geometry."""
        return self._available_geometry

    def devicePixelRatio(self) -> float:
        """Return the fake screen DPI scale."""
        return self._device_pixel_ratio


def test_create_overlay_controller_returns_null_when_disabled() -> None:
    """Disabled overlay should not start any UI backend."""
    controller = create_overlay_controller(
        False,
        position="top-left",
        screen_target="primary",
    )

    assert isinstance(controller, NullOverlayController)


def test_create_overlay_controller_falls_back_when_backend_module_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing optional UI dependency should degrade to the no-op controller."""
    monkeypatch.setattr(
        "whisper_tray.overlay.controller._pyside6_is_available",
        lambda: True,
    )
    monkeypatch.setitem(sys.modules, "whisper_tray.overlay.pyside_overlay", None)

    controller = create_overlay_controller(
        True,
        position="top-left",
        screen_target="primary",
    )

    assert isinstance(controller, NullOverlayController)


def test_create_overlay_controller_falls_back_when_pyside6_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing PySide6 should short-circuit before starting a UI thread."""
    monkeypatch.setattr(
        "whisper_tray.overlay.controller._pyside6_is_available",
        lambda: False,
    )

    controller = create_overlay_controller(
        True,
        position="bottom-right",
        screen_target="primary",
    )

    assert isinstance(controller, NullOverlayController)


def test_threaded_overlay_controller_forwards_state_updates() -> None:
    """Enabled overlays should forward presentations to the runtime thread."""
    seen: list[tuple[str, str, object]] = []
    received = threading.Event()

    def runtime_factory(
        commands: object,
        position: str,
        screen_target: str,
    ) -> RecordingRuntime:
        return RecordingRuntime(
            commands,
            position,
            screen_target,
            seen,
            received,
        )

    controller = create_overlay_controller(
        True,
        position="top-left",
        screen_target="cursor",
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
        True,
        position="top-left",
        screen_target="primary",
        runtime_factory=FailingRuntime,
    )

    assert isinstance(controller, NullOverlayController)


def test_resolve_overlay_screen_prefers_cursor_when_requested() -> None:
    """Cursor-targeted overlays should use the screen under the pointer."""
    primary = object()
    cursor = object()

    selected = resolve_overlay_screen(
        screen_target="cursor",
        primary_screen=primary,
        cursor_screen=cursor,
        screens=[primary, cursor],
    )

    assert selected is cursor


def test_resolve_overlay_screen_returns_none_when_cursor_lookup_fails() -> None:
    """Cursor mode should let richer fallback logic happen in reposition code."""
    primary = object()

    selected = resolve_overlay_screen(
        screen_target="cursor",
        primary_screen=primary,
        cursor_screen=None,
        screens=[primary],
    )

    assert selected is None


def test_resolve_overlay_reposition_screen_reuses_last_cursor_screen() -> None:
    """Cursor mode should reuse the last resolved screen when lookups go missing."""
    primary = FakeScreen(geometry=FakeGeometry(0, 0, 1920, 1080))
    previous_cursor = FakeScreen(geometry=FakeGeometry(1920, 0, 1920, 1080))

    selected = resolve_overlay_reposition_screen(
        screen_target="cursor",
        primary_screen=primary,
        cursor_screen=None,
        screens=[primary, previous_cursor],
        last_resolved_screen=previous_cursor,
        current_geometry=None,
    )

    assert selected is previous_cursor


def test_resolve_overlay_reposition_screen_falls_back_to_primary_last() -> None:
    """Primary fallback should only happen after cursor and sticky-screen misses."""
    primary = FakeScreen(geometry=FakeGeometry(0, 0, 1920, 1080))

    selected = resolve_overlay_reposition_screen(
        screen_target="cursor",
        primary_screen=primary,
        cursor_screen=None,
        screens=[primary],
        last_resolved_screen=None,
        current_geometry=None,
    )

    assert selected is primary


def test_update_last_resolved_screen_invalidates_anchor_on_screen_change() -> None:
    """Changing screens should clear the cached anchor so reposition can move again."""
    first_screen = object()
    second_screen = object()

    last_screen, last_anchor = update_last_resolved_screen(
        last_resolved_screen=first_screen,
        new_screen=second_screen,
        last_anchor=(100, 200),
    )

    assert last_screen is second_screen
    assert last_anchor is None


def test_resolve_overlay_coordinates_places_top_left_with_margin() -> None:
    """Top-left overlays should hug the available geometry with the given margin."""
    coords = resolve_overlay_coordinates(
        position="top-left",
        geometry=FakeGeometry(100, 200, 1600, 900),
        width=280,
        height=120,
        margin=24,
    )

    assert coords == (124, 224)


def test_resolve_overlay_coordinates_places_bottom_right_with_margin() -> None:
    """Bottom-right overlays should stay above the taskbar-safe bottom edge."""
    coords = resolve_overlay_coordinates(
        position="bottom-right",
        geometry=FakeGeometry(10, 20, 1200, 700),
        width=300,
        height=140,
        margin=24,
    )

    assert coords == (886, 556)


def test_resolve_overlay_layout_expands_error_cards() -> None:
    """Error states should get a bit more room for actionable recovery copy."""
    presenter = AppStatePresenter()
    ready = presenter.present(AppStateSnapshot(state=AppState.READY, device="cpu"))
    error = presenter.present(
        AppStateSnapshot(
            state=AppState.ERROR,
            device="cpu",
            message="Model failed to load.",
        )
    )

    assert (
        resolve_overlay_layout(error).max_width
        > resolve_overlay_layout(ready).max_width
    )


def test_resolve_overlay_layout_keeps_ready_card_compact() -> None:
    """Ready cards should stay small enough for unobtrusive corner status."""
    presenter = AppStatePresenter()
    ready = presenter.present(AppStateSnapshot(state=AppState.READY, device="cpu"))
    compact = AppStatePresenter(overlay_density="compact").present(
        AppStateSnapshot(state=AppState.READY, device="cpu")
    )

    ready_layout = resolve_overlay_layout(ready)
    compact_layout = resolve_overlay_layout(compact)

    assert ready_layout.max_width <= 400
    assert compact_layout.max_width <= 300


def test_geometry_contains_geometry_uses_overlay_center() -> None:
    """Geometry fallback should identify the screen containing the overlay center."""
    outer = FakeGeometry(0, 0, 1920, 1080)
    inner = FakeGeometry(900, 400, 200, 120)

    assert geometry_contains_geometry(outer, inner) is True


def test_resolve_overlay_theme_falls_back_to_neutral_palette() -> None:
    """Unknown colors should still produce a readable default overlay theme."""
    theme = resolve_overlay_theme("mystery")

    assert theme.accent == "#e8eef6"
    assert theme.accent_soft == "rgba(232, 238, 246, 0.12)"


def test_windows_overlay_uses_window_opacity_fade() -> None:
    """Windows layered overlays should animate the top-level window directly."""
    assert should_use_window_opacity_fade("Windows") is True
    assert should_use_window_opacity_fade("Linux") is False


def test_windows_overlay_skips_card_shadow() -> None:
    """Windows card overlays should avoid the fragile drop-shadow effect."""
    assert should_use_card_shadow("Windows") is False
    assert should_use_card_shadow("Linux") is True


def test_enable_windows_per_monitor_dpi_awareness_prefers_v2_context() -> None:
    """Modern Windows builds should opt into per-monitor v2 awareness first."""
    user32 = FakeDpiUser32()
    shcore = FakeShcore(result=1)
    ctypes_module = SimpleNamespace(
        windll=SimpleNamespace(user32=user32, shcore=shcore),
        get_last_error=lambda: 0,
    )

    enabled = enable_windows_per_monitor_dpi_awareness(
        ctypes_module=ctypes_module,
        system_name="Windows",
    )

    assert enabled is True
    assert user32.context_calls == [_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2]
    assert shcore.calls == []
    assert user32.legacy_calls == 0


def test_enable_windows_per_monitor_dpi_awareness_falls_back_to_shcore() -> None:
    """Older Windows APIs should still get per-monitor DPI awareness when available."""
    shcore = FakeShcore()
    ctypes_module = SimpleNamespace(
        windll=SimpleNamespace(user32=SimpleNamespace(), shcore=shcore),
        get_last_error=lambda: 0,
    )

    enabled = enable_windows_per_monitor_dpi_awareness(
        ctypes_module=ctypes_module,
        system_name="Windows",
    )

    assert enabled is True
    assert shcore.calls == [_PROCESS_PER_MONITOR_DPI_AWARE]


def test_enable_windows_per_monitor_dpi_awareness_treats_access_denied_as_ready() -> (
    None
):
    """Already-DPI-aware Windows processes should count as successfully configured."""
    user32 = FakeDpiUser32(context_result=0)
    ctypes_module = SimpleNamespace(
        windll=SimpleNamespace(user32=user32, shcore=None),
        get_last_error=lambda: 5,
    )

    enabled = enable_windows_per_monitor_dpi_awareness(
        ctypes_module=ctypes_module,
        system_name="Windows",
    )

    assert enabled is True
    assert user32.context_calls == [_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2]
    assert user32.legacy_calls == 0


def test_resolve_windows_overlay_ex_style_adds_passive_overlay_bits() -> None:
    """Windows overlay styling should make the window layered and click-through."""
    base_style = _WS_EX_APPWINDOW

    resolved = resolve_windows_overlay_ex_style(base_style)

    assert resolved & _WS_EX_LAYERED
    assert resolved & _WS_EX_TRANSPARENT
    assert resolved & _WS_EX_TOOLWINDOW
    assert resolved & _WS_EX_NOACTIVATE
    assert not resolved & _WS_EX_APPWINDOW


def test_apply_windows_overlay_styles_updates_extended_style() -> None:
    """Update Win32 style and keep the window topmost."""
    user32 = FakeUser32(initial_style=0x10)

    applied = apply_windows_overlay_styles(1234, user32=user32)

    assert applied is True
    assert user32.get_calls == [(1234, _GWL_EXSTYLE)]
    assert user32.set_calls == [
        (1234, _GWL_EXSTYLE, resolve_windows_overlay_ex_style(0x10))
    ]
    assert user32.pos_calls == [
        (
            1234,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )
    ]


def test_apply_windows_overlay_styles_returns_false_without_required_api() -> None:
    """The helper should fail closed when the native Win32 entry points are missing."""
    applied = apply_windows_overlay_styles(1234, user32=object())

    assert applied is False


def test_create_overlay_window_returns_card_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The overlay factory should instantiate the anchored overlay window."""
    pytest.importorskip("PySide6")
    created: list[tuple[str, str]] = []

    class FakeCardWindow:
        """Minimal overlay-window stub used to observe constructor selection."""

        def __init__(self, position: str, screen_target: str) -> None:
            created.append((position, screen_target))

    monkeypatch.setattr(
        "whisper_tray.overlay.pyside_overlay.OverlayWindow",
        FakeCardWindow,
    )

    window = create_overlay_window(
        position="top-left",
        screen_target="cursor",
    )

    assert isinstance(window, FakeCardWindow)
    assert created == [("top-left", "cursor")]
