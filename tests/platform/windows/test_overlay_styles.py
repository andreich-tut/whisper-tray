"""Tests for Windows-specific overlay DPI and window style helpers."""

from __future__ import annotations

from types import SimpleNamespace

from whisper_tray.platform.windows.overlay_styles import (
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
    enable_windows_per_monitor_dpi_awareness,
    resolve_windows_overlay_ex_style,
    should_use_card_shadow,
    should_use_window_opacity_fade,
)


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
