"""Platform-specific helpers for the PySide overlay backend."""

from __future__ import annotations

import platform

_GWL_EXSTYLE = -20
_HWND_TOPMOST = -1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_APPWINDOW = 0x00040000
_WS_EX_LAYERED = 0x00080000
_WS_EX_NOACTIVATE = 0x08000000
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
_PROCESS_PER_MONITOR_DPI_AWARE = 2
_ERROR_ACCESS_DENIED = 5
_HRESULT_ACCESS_DENIED = -2147024891
_HRESULT_ACCESS_DENIED_UNSIGNED = 0x80070005


def is_windows_platform(system_name: str | None = None) -> bool:
    """Return whether the current runtime should use Win32 overlay polish."""
    return (system_name or platform.system()) == "Windows"


def should_use_window_opacity_fade(system_name: str | None = None) -> bool:
    """Return whether overlay fades should animate the top-level window."""
    return is_windows_platform(system_name)


def should_use_card_shadow(system_name: str | None = None) -> bool:
    """Return whether the card overlay should use a drop shadow effect."""
    return not is_windows_platform(system_name)


def should_disable_native_window_shadow(system_name: str | None = None) -> bool:
    """Return whether passive overlay windows should opt out of native shadows."""
    return is_windows_platform(system_name)


def resolve_windows_overlay_ex_style(current_style: int) -> int:
    """Add the Win32 extended styles needed for a passive overlay window."""
    return (
        current_style
        | _WS_EX_LAYERED
        | _WS_EX_TRANSPARENT
        | _WS_EX_TOOLWINDOW
        | _WS_EX_NOACTIVATE
    ) & ~_WS_EX_APPWINDOW


def _dpi_awareness_already_set(error_code: int) -> bool:
    """Return whether Windows refused a DPI call because awareness is locked in."""
    return error_code == _ERROR_ACCESS_DENIED


def _dpi_awareness_hresult_is_ready(result: int) -> bool:
    """Return whether a DPI HRESULT means the process is already configured."""
    return result in {0, _HRESULT_ACCESS_DENIED, _HRESULT_ACCESS_DENIED_UNSIGNED}


def enable_windows_per_monitor_dpi_awareness(
    *,
    ctypes_module: object | None = None,
    system_name: str | None = None,
) -> bool:
    """
    Best-effort opt into per-monitor DPI awareness for Windows Qt runtimes.

    The helper safely falls back across the modern and legacy Win32 APIs so
    packaged builds behave more predictably on mixed-DPI monitor setups.
    """
    if not is_windows_platform(system_name):
        return False

    if ctypes_module is None:
        try:
            import ctypes
        except ImportError:
            return False

        ctypes_module = ctypes

    windll = getattr(ctypes_module, "windll", None)
    if windll is None:
        return False

    user32 = getattr(windll, "user32", None)
    shcore = getattr(windll, "shcore", None)
    get_last_error = getattr(ctypes_module, "get_last_error", None)

    set_awareness_context = getattr(user32, "SetProcessDpiAwarenessContext", None)
    if callable(set_awareness_context):
        if set_awareness_context(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return True
        if callable(get_last_error) and _dpi_awareness_already_set(
            int(get_last_error())
        ):
            return True

    set_process_awareness = getattr(shcore, "SetProcessDpiAwareness", None)
    if callable(set_process_awareness):
        result = int(set_process_awareness(_PROCESS_PER_MONITOR_DPI_AWARE))
        if _dpi_awareness_hresult_is_ready(result):
            return True

    set_dpi_aware = getattr(user32, "SetProcessDPIAware", None)
    if callable(set_dpi_aware):
        return bool(set_dpi_aware())

    return False


def apply_windows_overlay_styles(hwnd: int, *, user32: object | None = None) -> bool:
    """Apply native Win32 flags so the overlay stays click-through and passive."""
    if hwnd <= 0:
        return False

    if user32 is None:
        try:
            import ctypes
        except ImportError:
            return False

        user32 = getattr(getattr(ctypes, "windll", None), "user32", None)

    get_window_long = getattr(user32, "GetWindowLongPtrW", None) or getattr(
        user32,
        "GetWindowLongW",
        None,
    )
    set_window_long = getattr(user32, "SetWindowLongPtrW", None) or getattr(
        user32,
        "SetWindowLongW",
        None,
    )
    set_window_pos = getattr(user32, "SetWindowPos", None)

    if (
        not callable(get_window_long)
        or not callable(set_window_long)
        or not callable(set_window_pos)
    ):
        return False

    current_style = int(get_window_long(hwnd, _GWL_EXSTYLE))
    desired_style = resolve_windows_overlay_ex_style(current_style)
    set_window_long(hwnd, _GWL_EXSTYLE, desired_style)
    set_window_pos(
        hwnd,
        _HWND_TOPMOST,
        0,
        0,
        0,
        0,
        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
    )
    return True
