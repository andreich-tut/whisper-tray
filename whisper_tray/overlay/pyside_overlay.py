"""PySide6-backed overlay runtime."""

from __future__ import annotations

import html
import platform
import queue
from dataclasses import dataclass, replace
from typing import Any, Sequence

from whisper_tray.overlay.controller import (
    OverlayCommand,
    OverlayCommandKind,
    OverlayStartupCallback,
)
from whisper_tray.state import AppState, AppStatePresentation

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
try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QWidget

    _PYSIDE6_AVAILABLE = True
except ImportError:
    Qt = QColor = None
    QWidget = object
    _PYSIDE6_AVAILABLE = False


@dataclass(frozen=True)
class OverlayTheme:
    """Simple theme tokens used by the overlay card."""

    accent: str
    accent_soft: str
    border: str
    background: str
    badge_border: str
    body: str = "rgba(255, 255, 255, 0.88)"
    hint: str = "rgba(255, 255, 255, 0.62)"


@dataclass(frozen=True)
class OverlayLayout:
    """Layout tokens used to keep overlay sizing consistent."""

    min_width: int
    max_width: int
    radius: int
    accent_width: int
    padding_horizontal: int
    padding_vertical: int
    spacing: int
    badge_radius: int
    badge_padding_horizontal: int
    badge_padding_vertical: int
    badge_spacing: int
    primary_size: int
    secondary_size: int
    hint_size: int


DETAILED_LAYOUT = OverlayLayout(
    min_width=320,
    max_width=400,
    radius=18,
    accent_width=0,
    padding_horizontal=18,
    padding_vertical=16,
    spacing=6,
    badge_radius=12,
    badge_padding_horizontal=10,
    badge_padding_vertical=6,
    badge_spacing=7,
    primary_size=14,
    secondary_size=11,
    hint_size=10,
)

COMPACT_LAYOUT = OverlayLayout(
    min_width=240,
    max_width=300,
    radius=16,
    accent_width=0,
    padding_horizontal=14,
    padding_vertical=12,
    spacing=5,
    badge_radius=10,
    badge_padding_horizontal=9,
    badge_padding_vertical=5,
    badge_spacing=6,
    primary_size=12,
    secondary_size=10,
    hint_size=9,
)


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


def resolve_overlay_screen(
    *,
    screen_target: str,
    primary_screen: Any | None,
    cursor_screen: Any | None,
    screens: Sequence[Any],
) -> Any | None:
    """Choose the screen the overlay should render on."""
    if screen_target == "cursor":
        return cursor_screen
    return primary_screen


def resolve_overlay_coordinates(
    *,
    position: str,
    geometry: Any,
    width: int,
    height: int,
    margin: int,
) -> tuple[int, int]:
    """Translate a corner preference into concrete on-screen coordinates."""
    if position == "top-left":
        return geometry.x() + margin, geometry.y() + margin
    if position == "top-right":
        return geometry.x() + geometry.width() - width - margin, geometry.y() + margin
    if position == "bottom-left":
        return geometry.x() + margin, geometry.y() + geometry.height() - height - margin
    return (
        geometry.x() + geometry.width() - width - margin,
        geometry.y() + geometry.height() - height - margin,
    )


def resolve_overlay_layout(presentation: AppStatePresentation) -> OverlayLayout:
    """Choose the overlay sizing tokens for the active presentation."""
    layout = (
        COMPACT_LAYOUT if presentation.overlay_density == "compact" else DETAILED_LAYOUT
    )
    if presentation.state is AppState.ERROR:
        return replace(
            layout,
            min_width=layout.min_width + 24,
            max_width=layout.max_width + 40,
        )
    return layout


def _geometry_bounds(geometry: Any) -> tuple[float, float, float, float]:
    """Extract a rect-like geometry into numeric bounds."""
    return (
        float(geometry.x()),
        float(geometry.y()),
        float(geometry.width()),
        float(geometry.height()),
    )


def geometry_contains_geometry(outer_geometry: Any, inner_geometry: Any) -> bool:
    """Return whether the inner geometry's center sits inside the outer geometry."""
    outer_x, outer_y, outer_width, outer_height = _geometry_bounds(outer_geometry)
    inner_x, inner_y, inner_width, inner_height = _geometry_bounds(inner_geometry)
    center_x = inner_x + (inner_width / 2)
    center_y = inner_y + (inner_height / 2)
    return (
        outer_x <= center_x <= outer_x + outer_width
        and outer_y <= center_y <= outer_y + outer_height
    )


def resolve_screen_from_geometry(
    geometry: Any | None,
    screens: Sequence[Any],
) -> Any | None:
    """Find the screen that currently contains the overlay geometry."""
    if geometry is None:
        return None

    for screen in screens:
        screen_geometry_getter = getattr(screen, "geometry", None)
        if callable(screen_geometry_getter):
            screen_geometry = screen_geometry_getter()
        else:
            available_geometry_getter = getattr(screen, "availableGeometry", None)
            if not callable(available_geometry_getter):
                continue
            screen_geometry = available_geometry_getter()
        if geometry_contains_geometry(screen_geometry, geometry):
            return screen
    return None


def update_last_resolved_screen(
    *,
    last_resolved_screen: Any | None,
    new_screen: Any | None,
    last_anchor: object | None,
) -> tuple[Any | None, object | None]:
    """Track the last cursor/primary lookup result and invalidate stale anchors."""
    if new_screen is None:
        return last_resolved_screen, last_anchor
    if new_screen is last_resolved_screen:
        return new_screen, last_anchor
    return new_screen, None


def resolve_overlay_reposition_screen(
    *,
    screen_target: str,
    primary_screen: Any | None,
    cursor_screen: Any | None,
    screens: Sequence[Any],
    last_resolved_screen: Any | None,
    current_geometry: Any | None,
) -> Any | None:
    """Resolve the best screen for the current overlay reposition request."""
    screen = resolve_overlay_screen(
        screen_target=screen_target,
        primary_screen=primary_screen,
        cursor_screen=cursor_screen,
        screens=screens,
    )
    if screen is not None:
        return screen
    if last_resolved_screen is not None:
        return last_resolved_screen

    geometry_screen = resolve_screen_from_geometry(current_geometry, screens)
    if geometry_screen is not None:
        return geometry_screen
    if primary_screen is not None:
        return primary_screen
    if screens:
        return screens[0]
    return None


def resolve_overlay_theme(color: str) -> OverlayTheme:
    """Translate tray colors into a readable overlay theme."""
    themes = {
        "crimson": OverlayTheme(
            accent="#ff9ab2",
            accent_soft="rgba(255, 154, 178, 0.16)",
            border="rgba(255, 145, 176, 0.55)",
            background="rgba(86, 20, 34, 0.94)",
            badge_border="rgba(255, 145, 176, 0.35)",
        ),
        "lightgreen": OverlayTheme(
            accent="#9ae4b4",
            accent_soft="rgba(154, 228, 180, 0.14)",
            border="rgba(148, 235, 175, 0.28)",
            background="rgba(27, 126, 63, 0.30)",
            badge_border="rgba(154, 228, 180, 0.35)",
        ),
        "orange": OverlayTheme(
            accent="#ffcc73",
            accent_soft="rgba(255, 204, 115, 0.14)",
            border="rgba(255, 205, 108, 0.32)",
            background="rgba(166, 111, 20, 0.30)",
            badge_border="rgba(255, 205, 108, 0.36)",
        ),
        "tomato": OverlayTheme(
            accent="#ffab92",
            accent_soft="rgba(255, 171, 146, 0.14)",
            border="rgba(255, 163, 139, 0.30)",
            background="rgba(156, 53, 31, 0.30)",
            badge_border="rgba(255, 163, 139, 0.36)",
        ),
        "yellow": OverlayTheme(
            accent="#f5d360",
            accent_soft="rgba(245, 211, 96, 0.14)",
            border="rgba(255, 218, 96, 0.32)",
            background="rgba(149, 122, 19, 0.30)",
            badge_border="rgba(255, 218, 96, 0.34)",
        ),
    }
    return themes.get(
        color,
        OverlayTheme(
            accent="#e8eef6",
            accent_soft="rgba(232, 238, 246, 0.12)",
            border="rgba(232, 238, 246, 0.28)",
            background="rgba(25, 31, 42, 0.92)",
            badge_border="rgba(232, 238, 246, 0.30)",
        ),
    )


class OverlayWindow:
    """Compact, always-on-top status window."""

    _MARGIN = 24
    _POSITION_POLL_INTERVAL_MS = 250

    def __init__(self, position: str, screen_target: str) -> None:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QColor, QFont
        from PySide6.QtWidgets import (
            QFrame,
            QGraphicsDropShadowEffect,
            QGraphicsOpacityEffect,
            QHBoxLayout,
            QLabel,
            QVBoxLayout,
            QWidget,
        )

        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        if (
            hasattr(Qt.WindowType, "NoDropShadowWindowHint")
            and should_disable_native_window_shadow()
        ):
            flags |= Qt.WindowType.NoDropShadowWindowHint
        if hasattr(Qt.WindowType, "WindowDoesNotAcceptFocus"):
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        if hasattr(Qt.WindowType, "WindowTransparentForInput"):
            flags |= Qt.WindowType.WindowTransparentForInput

        self._widget = QWidget(None, flags)
        self._widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._position = position
        self._screen_target = screen_target
        self._fade_visible = False
        self._use_window_opacity_fade = False
        self._last_anchor: tuple[int, int] | None = None
        self._last_resolved_screen: Any | None = None

        root_layout = QVBoxLayout(self._widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame(self._widget)
        self._card.setObjectName("overlayCard")
        self._content = QWidget(self._card)
        self._content_layout = QVBoxLayout(self._content)

        self._badge_shell = QFrame(self._content)
        self._badge_shell.setObjectName("overlayBadgeShell")
        self._badge_layout = QHBoxLayout(self._badge_shell)
        self._badge_layout.setContentsMargins(10, 6, 10, 6)
        self._badge_layout.setSpacing(7)

        self._badge_dot = QLabel(self._badge_shell)
        self._badge_dot.setObjectName("overlayBadgeDot")
        self._badge_dot.setText("●")
        self._badge_dot.setFont(QFont("Segoe UI Symbol", 10))

        self._badge = QLabel(self._badge_shell)
        self._badge.setObjectName("overlayBadge")
        self._badge.setFont(QFont("Segoe UI Semibold", 9))
        self._badge_layout.addWidget(self._badge_dot)
        self._badge_layout.addWidget(self._badge)

        self._primary = QLabel(self._content)
        self._primary.setObjectName("overlayPrimary")
        self._primary.setWordWrap(True)
        self._primary.setTextFormat(Qt.TextFormat.RichText)
        self._primary.setFont(QFont("Segoe UI Semibold", 12))

        self._secondary = QLabel(self._content)
        self._secondary.setObjectName("overlaySecondary")
        self._secondary.setWordWrap(True)
        self._secondary.setFont(QFont("Segoe UI", 10))

        self._hint = QLabel(self._content)
        self._hint.setObjectName("overlayHint")
        self._hint.setWordWrap(True)
        self._hint.setFont(QFont("Segoe UI", 9))

        self._content_layout.addWidget(self._badge_shell, 0, Qt.AlignmentFlag.AlignLeft)
        self._content_layout.addWidget(self._primary)
        self._content_layout.addWidget(self._secondary)
        self._content_layout.addWidget(self._hint)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addWidget(self._content)
        root_layout.addWidget(self._card)

        from PySide6.QtCore import QEasingCurve, QPropertyAnimation

        if should_use_card_shadow():
            shadow = QGraphicsDropShadowEffect(self._card)
            shadow.setBlurRadius(38)
            shadow.setOffset(0, 18)
            shadow.setColor(QColor(0, 0, 0, 46))
            self._card.setGraphicsEffect(shadow)

        self._opacity: Any | None = None
        if self._use_window_opacity_fade:
            self._widget.setWindowOpacity(0.0)
            self._fade = QPropertyAnimation(
                self._widget, b"windowOpacity", self._widget
            )
        else:
            self._opacity = QGraphicsOpacityEffect(self._widget)
            self._opacity.setOpacity(0.0)
            self._widget.setGraphicsEffect(self._opacity)
            self._fade = QPropertyAnimation(self._opacity, b"opacity", self._widget)
        self._fade.setDuration(180)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._on_fade_finished)

        self._hide_timer = QTimer(self._widget)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self._position_timer = QTimer(self._widget)
        self._position_timer.setInterval(self._POSITION_POLL_INTERVAL_MS)
        self._position_timer.timeout.connect(self._reposition)
        self._apply_platform_window_behaviors()

    def show_presentation(self, presentation: AppStatePresentation) -> None:
        """Render a new presentation and show the window."""
        theme = resolve_overlay_theme(presentation.icon_color)
        layout = resolve_overlay_layout(presentation)
        self._apply_layout(layout)
        self._apply_fonts(layout)

        self._badge.setText(presentation.overlay_badge.upper())
        self._primary.setText(self._format_primary_markup(presentation))

        secondary = presentation.overlay_secondary or ""
        self._secondary.setText(secondary)
        self._secondary.setVisible(bool(secondary))

        hint = presentation.overlay_hint or ""
        self._hint.setText(hint)
        self._hint.setVisible(bool(hint))

        self._card.setStyleSheet(
            """
            QFrame#overlayCard {
                background-color: %(background)s;
                border: 1px solid %(border)s;
                border-radius: %(radius)spx;
            }
            QFrame#overlayBadgeShell {
                background-color: %(accent_soft)s;
                border: 1px solid %(badge_border)s;
                border-radius: %(badge_radius)spx;
            }
            QLabel#overlayPrimary {
                color: rgba(255, 255, 255, 0.96);
                background: transparent;
            }
            QLabel#overlaySecondary {
                color: %(body)s;
                background: transparent;
            }
            QLabel#overlayHint {
                color: %(hint)s;
                background: transparent;
            }
            QLabel#overlayBadgeDot {
                color: %(accent)s;
                background: transparent;
            }
            QLabel#overlayBadge {
                color: %(accent)s;
                background: transparent;
            }
            """
            % {
                "background": theme.background,
                "accent": theme.accent,
                "accent_soft": theme.accent_soft,
                "border": theme.border,
                "badge_border": theme.badge_border,
                "body": theme.body,
                "hint": theme.hint,
                "radius": layout.radius,
                "badge_radius": layout.badge_radius,
            }
        )

        self._hide_timer.stop()
        self._widget.adjustSize()
        self._reposition()
        self._widget.show()
        self._sync_position_tracking()
        self._apply_platform_window_behaviors()
        self._widget.raise_()
        self._fade_in()

        if presentation.overlay_auto_hide_seconds is not None:
            duration_ms = max(0, int(presentation.overlay_auto_hide_seconds * 1000))
            self._hide_timer.start(duration_ms)

    def close(self) -> None:
        """Close the backing widget."""
        self._hide_timer.stop()
        self._position_timer.stop()
        self._last_anchor = None
        self._last_resolved_screen = None
        self._widget.close()

    def hide_now(self) -> None:
        """Hide the overlay immediately without waiting for the fade timer."""
        self._hide_timer.stop()
        self._position_timer.stop()
        self._fade.stop()
        self._fade_visible = False
        self._last_anchor = None
        self._last_resolved_screen = None
        self._set_opacity(0.0)
        self._widget.hide()

    def update_anchor(self, position: str, screen_target: str) -> None:
        """Update the overlay corner/display target and reposition if visible."""
        self._position = position
        self._screen_target = screen_target
        if self._widget.isVisible():
            self._reposition()

    def _fade_in(self) -> None:
        """Animate the overlay into view."""
        self._fade.stop()
        self._fade_visible = True
        start = self._current_opacity()
        self._fade.setStartValue(start)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def _fade_out(self) -> None:
        """Animate the overlay out of view."""
        if not self._widget.isVisible():
            return
        self._fade.stop()
        self._fade_visible = False
        start = self._current_opacity()
        self._fade.setStartValue(start)
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self) -> None:
        """Hide the widget after fade-out completes."""
        if not self._fade_visible:
            self._position_timer.stop()
            self._last_anchor = None
            self._widget.hide()

    def _reposition(self) -> None:
        """Place the overlay in the configured corner of the selected screen."""
        from PySide6.QtGui import QCursor, QGuiApplication, QScreen

        screens = QGuiApplication.screens()
        cursor_screen: QScreen | None = None
        if hasattr(QGuiApplication, "screenAt"):
            raw_screen = QGuiApplication.screenAt(QCursor.pos())
            if isinstance(raw_screen, QScreen):
                cursor_screen = raw_screen

        lookup_screen = resolve_overlay_screen(
            screen_target=self._screen_target,
            primary_screen=QGuiApplication.primaryScreen(),
            cursor_screen=cursor_screen,
            screens=screens,
        )
        resolved_screen, resolved_anchor = update_last_resolved_screen(
            last_resolved_screen=self._last_resolved_screen,
            new_screen=lookup_screen,
            last_anchor=self._last_anchor,
        )
        self._last_resolved_screen = resolved_screen
        self._last_anchor = resolved_anchor  # type: ignore[assignment]

        screen = resolve_overlay_reposition_screen(
            screen_target=self._screen_target,
            primary_screen=QGuiApplication.primaryScreen(),
            cursor_screen=cursor_screen,
            screens=screens,
            last_resolved_screen=self._last_resolved_screen,
            current_geometry=self._widget.geometry(),
        )
        if screen is None:
            self._last_anchor = None
            return

        geometry = screen.availableGeometry()
        anchor = resolve_overlay_coordinates(
            position=self._position,
            geometry=geometry,
            width=self._widget.width(),
            height=self._widget.height(),
            margin=self._MARGIN,
        )
        if anchor == self._last_anchor:
            return

        self._last_anchor = anchor
        self._widget.move(*anchor)

    def _sync_position_tracking(self) -> None:
        """Keep visible overlays aligned as cursor display or geometry changes."""
        if self._widget.isVisible():
            self._position_timer.start()
            return
        self._position_timer.stop()
        self._last_anchor = None

    def _apply_layout(self, layout: OverlayLayout) -> None:
        """Apply layout tokens before sizing and rendering the card."""
        self._card.setMinimumWidth(layout.min_width)
        self._card.setMaximumWidth(layout.max_width)
        self._content_layout.setContentsMargins(
            layout.padding_horizontal,
            layout.padding_vertical,
            layout.padding_horizontal,
            layout.padding_vertical,
        )
        self._content_layout.setSpacing(layout.spacing)

    def _apply_fonts(self, layout: OverlayLayout) -> None:
        """Refresh font sizing when the density or state changes."""
        from PySide6.QtGui import QFont

        self._badge.setFont(
            QFont("Segoe UI Semibold", max(layout.secondary_size - 1, 9))
        )
        self._badge_dot.setFont(
            QFont("Segoe UI Symbol", max(layout.secondary_size, 10))
        )
        self._primary.setFont(QFont("Segoe UI Semibold", layout.primary_size))
        self._secondary.setFont(QFont("Segoe UI", layout.secondary_size))
        self._hint.setFont(QFont("Segoe UI", layout.hint_size))

    def _current_opacity(self) -> float:
        """Return the active fade opacity for the top-level widget."""
        if self._use_window_opacity_fade:
            return float(self._widget.windowOpacity())
        if self._opacity is None:
            return 1.0
        return float(self._opacity.opacity())

    def _set_opacity(self, value: float) -> None:
        """Set overlay opacity without assuming a specific fade backend."""
        if self._use_window_opacity_fade:
            self._widget.setWindowOpacity(value)
            return
        if self._opacity is not None:
            self._opacity.setOpacity(value)

    @staticmethod
    def _format_keycap(token: str) -> str:
        """Render a keyboard token with the artifact-style keycap treatment."""
        return (
            '<span style="display:inline-block; '
            "font-family:Consolas, 'Cascadia Mono', monospace; "
            "padding:3px 6px; background:#1f1f1f; border-radius:3px; "
            "color:#ffffff; line-height:1; vertical-align:baseline; "
            'box-shadow:0 0 0 1px rgba(255, 255, 255, 0.06);">'
            f"{html.escape(token)}"
            "</span>"
        )

    def _format_primary_markup(self, presentation: AppStatePresentation) -> str:
        """Render primary copy with rich text when the state calls for keycaps."""
        primary_text = presentation.overlay_primary
        if presentation.state is not AppState.READY:
            return html.escape(primary_text)

        prefix = "Hold "
        suffix = " to dictate."
        if not primary_text.startswith(prefix) or not primary_text.endswith(suffix):
            return html.escape(primary_text)

        hotkey = primary_text[len(prefix) : -len(suffix)]
        keycaps = "+".join(self._format_keycap(part) for part in hotkey.split("+"))
        return f"{html.escape(prefix)}{keycaps}{html.escape(suffix)}"

    def _apply_platform_window_behaviors(self) -> None:
        """Apply native focus and input behavior when the platform supports it."""
        if not is_windows_platform():
            return

        try:
            apply_windows_overlay_styles(int(self._widget.winId()))
        except Exception:
            # Native overlay polish should never take down the Qt runtime.
            return


def create_overlay_window(
    *,
    position: str,
    screen_target: str,
) -> OverlayWindow:
    """Create the overlay window implementation."""
    return OverlayWindow(position=position, screen_target=screen_target)


class PySide6OverlayRuntime:
    """Qt runtime that drains state updates and renders the overlay window."""

    def __init__(
        self,
        commands: queue.Queue[OverlayCommand],
        position: str,
        screen_target: str,
    ) -> None:
        self._commands = commands
        self._position = position
        self._screen_target = screen_target

    def run(self, startup_callback: OverlayStartupCallback) -> None:
        """Start the Qt event loop and process overlay commands."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        enable_windows_per_monitor_dpi_awareness()
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        window = create_overlay_window(
            position=self._position,
            screen_target=self._screen_target,
        )
        startup_callback(True)

        poller = QTimer()
        poller.setInterval(33)
        poller.timeout.connect(lambda: self._drain_commands(window, app))
        poller.start()

        try:
            app.exec()
        finally:
            poller.stop()
            window.close()

    def _drain_commands(self, window: Any, app: Any) -> None:
        """Apply the latest queued overlay command."""
        latest_presentation: AppStatePresentation | None = None

        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                break

            if command.kind is OverlayCommandKind.CLOSE:
                window.close()
                app.quit()
                return

            latest_presentation = command.presentation

        if latest_presentation is not None:
            window.show_presentation(latest_presentation)
