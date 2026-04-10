"""Compatibility facade for the PySide overlay backend."""

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
    is_windows_platform,
    resolve_windows_overlay_ex_style,
    should_disable_native_window_shadow,
    should_use_card_shadow,
    should_use_window_opacity_fade,
)
from whisper_tray.overlay.pyside_presentation import (
    COMPACT_LAYOUT,
    DETAILED_LAYOUT,
    OverlayLayout,
    OverlayTheme,
    geometry_contains_geometry,
    resolve_overlay_coordinates,
    resolve_overlay_layout,
    resolve_overlay_reposition_screen,
    resolve_overlay_screen,
    resolve_overlay_theme,
    resolve_screen_from_geometry,
    update_last_resolved_screen,
)
from whisper_tray.overlay.pyside_runtime import (
    OverlayWindow,
    PySide6OverlayRuntime,
)


def create_overlay_window(
    *,
    position: str,
    screen_target: str,
) -> OverlayWindow:
    """Create the overlay window implementation."""
    return OverlayWindow(position=position, screen_target=screen_target)


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
    "COMPACT_LAYOUT",
    "DETAILED_LAYOUT",
    "OverlayLayout",
    "OverlayTheme",
    "OverlayWindow",
    "PySide6OverlayRuntime",
    "apply_windows_overlay_styles",
    "create_overlay_window",
    "enable_windows_per_monitor_dpi_awareness",
    "geometry_contains_geometry",
    "is_windows_platform",
    "resolve_overlay_coordinates",
    "resolve_overlay_layout",
    "resolve_overlay_reposition_screen",
    "resolve_overlay_screen",
    "resolve_overlay_theme",
    "resolve_screen_from_geometry",
    "resolve_windows_overlay_ex_style",
    "should_disable_native_window_shadow",
    "should_use_card_shadow",
    "should_use_window_opacity_fade",
    "update_last_resolved_screen",
]
