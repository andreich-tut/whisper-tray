"""Windows overlay-style helper facade."""

from whisper_tray.overlay.pyside_platform import (
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
)

__all__ = [
    "_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2",
    "_GWL_EXSTYLE",
    "_HWND_TOPMOST",
    "_PROCESS_PER_MONITOR_DPI_AWARE",
    "_SWP_FRAMECHANGED",
    "_SWP_NOACTIVATE",
    "_SWP_NOMOVE",
    "_SWP_NOSIZE",
    "_WS_EX_APPWINDOW",
    "_WS_EX_LAYERED",
    "_WS_EX_NOACTIVATE",
    "_WS_EX_TOOLWINDOW",
    "_WS_EX_TRANSPARENT",
    "apply_windows_overlay_styles",
    "enable_windows_per_monitor_dpi_awareness",
    "resolve_windows_overlay_ex_style",
]
