"""PySide6-backed overlay runtime."""

from __future__ import annotations

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


@dataclass(frozen=True)
class OverlayTheme:
    """Simple theme tokens used by the overlay card."""

    accent: str
    accent_soft: str
    border: str
    background: str
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
    primary_size: int
    secondary_size: int
    hint_size: int


DETAILED_LAYOUT = OverlayLayout(
    min_width=308,
    max_width=420,
    radius=22,
    accent_width=6,
    padding_horizontal=20,
    padding_vertical=18,
    spacing=8,
    badge_radius=10,
    primary_size=14,
    secondary_size=10,
    hint_size=9,
)

COMPACT_LAYOUT = OverlayLayout(
    min_width=244,
    max_width=300,
    radius=18,
    accent_width=5,
    padding_horizontal=16,
    padding_vertical=14,
    spacing=6,
    badge_radius=9,
    primary_size=13,
    secondary_size=10,
    hint_size=9,
)


def is_windows_platform(system_name: str | None = None) -> bool:
    """Return whether the current runtime should use Win32 overlay polish."""
    return (system_name or platform.system()) == "Windows"


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
    if screen_target == "cursor" and cursor_screen is not None:
        return cursor_screen
    if primary_screen is not None:
        return primary_screen
    if cursor_screen is not None:
        return cursor_screen
    if screens:
        return screens[0]
    return None


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


def resolve_overlay_theme(color: str) -> OverlayTheme:
    """Translate tray colors into a readable overlay theme."""
    themes = {
        "crimson": OverlayTheme(
            accent="#ff9ab2",
            accent_soft="rgba(255, 154, 178, 0.16)",
            border="rgba(255, 145, 176, 0.55)",
            background="rgba(86, 20, 34, 0.94)",
        ),
        "lightgreen": OverlayTheme(
            accent="#a9efb9",
            accent_soft="rgba(169, 239, 185, 0.16)",
            border="rgba(172, 237, 191, 0.48)",
            background="rgba(20, 54, 33, 0.93)",
        ),
        "orange": OverlayTheme(
            accent="#ffc86b",
            accent_soft="rgba(255, 200, 107, 0.18)",
            border="rgba(255, 201, 107, 0.5)",
            background="rgba(79, 46, 12, 0.94)",
        ),
        "tomato": OverlayTheme(
            accent="#ff9d84",
            accent_soft="rgba(255, 157, 132, 0.16)",
            border="rgba(255, 157, 132, 0.52)",
            background="rgba(85, 29, 23, 0.94)",
        ),
        "yellow": OverlayTheme(
            accent="#ffe27a",
            accent_soft="rgba(255, 226, 122, 0.18)",
            border="rgba(255, 226, 122, 0.5)",
            background="rgba(78, 66, 18, 0.94)",
        ),
    }
    return themes.get(
        color,
        OverlayTheme(
            accent="#e8eef6",
            accent_soft="rgba(232, 238, 246, 0.12)",
            border="rgba(232, 238, 246, 0.28)",
            background="rgba(25, 31, 42, 0.93)",
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
            QSizePolicy,
            QVBoxLayout,
            QWidget,
        )

        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
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
        self._last_anchor: tuple[int, int] | None = None

        root_layout = QVBoxLayout(self._widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame(self._widget)
        self._card.setObjectName("overlayCard")
        self._card_shell = QHBoxLayout(self._card)
        self._card_shell.setContentsMargins(0, 0, 0, 0)
        self._card_shell.setSpacing(0)

        self._accent = QFrame(self._card)
        self._accent.setObjectName("overlayAccent")

        self._content = QWidget(self._card)
        self._content_layout = QVBoxLayout(self._content)

        self._badge = QLabel(self._content)
        self._badge.setObjectName("overlayBadge")
        self._badge.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        self._badge.setFont(QFont("Segoe UI Semibold", 9))

        self._primary = QLabel(self._content)
        self._primary.setObjectName("overlayPrimary")
        self._primary.setWordWrap(True)
        self._primary.setFont(QFont("Segoe UI Semibold", 12))

        self._secondary = QLabel(self._content)
        self._secondary.setObjectName("overlaySecondary")
        self._secondary.setWordWrap(True)
        self._secondary.setFont(QFont("Segoe UI", 10))

        self._hint = QLabel(self._content)
        self._hint.setObjectName("overlayHint")
        self._hint.setWordWrap(True)
        self._hint.setFont(QFont("Segoe UI", 9))

        self._content_layout.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignLeft)
        self._content_layout.addWidget(self._primary)
        self._content_layout.addWidget(self._secondary)
        self._content_layout.addWidget(self._hint)
        self._card_shell.addWidget(self._accent)
        self._card_shell.addWidget(self._content)
        root_layout.addWidget(self._card)

        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 70))
        self._card.setGraphicsEffect(shadow)

        self._opacity = QGraphicsOpacityEffect(self._widget)
        self._opacity.setOpacity(0.0)
        self._widget.setGraphicsEffect(self._opacity)

        from PySide6.QtCore import QEasingCurve, QPropertyAnimation

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
        self._primary.setText(presentation.overlay_primary)

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
            QFrame#overlayAccent {
                background-color: %(accent)s;
                border-top-left-radius: %(radius)spx;
                border-bottom-left-radius: %(radius)spx;
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
            QLabel#overlayBadge {
                color: %(accent)s;
                background-color: %(accent_soft)s;
                border: 1px solid %(border)s;
                border-radius: %(badge_radius)spx;
                padding: 3px 8px;
            }
            """
            % {
                "background": theme.background,
                "accent": theme.accent,
                "accent_soft": theme.accent_soft,
                "border": theme.border,
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
        self._widget.close()

    def hide_now(self) -> None:
        """Hide the overlay immediately without waiting for the fade timer."""
        self._hide_timer.stop()
        self._position_timer.stop()
        self._fade.stop()
        self._fade_visible = False
        self._last_anchor = None
        self._opacity.setOpacity(0.0)
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
        start = self._opacity.opacity()
        self._fade.setStartValue(start)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def _fade_out(self) -> None:
        """Animate the overlay out of view."""
        if not self._widget.isVisible():
            return
        self._fade.stop()
        self._fade_visible = False
        start = self._opacity.opacity()
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
        from PySide6.QtGui import QCursor, QGuiApplication

        cursor_screen = None
        if hasattr(QGuiApplication, "screenAt"):
            cursor_screen = QGuiApplication.screenAt(QCursor.pos())

        screen = resolve_overlay_screen(
            screen_target=self._screen_target,
            primary_screen=QGuiApplication.primaryScreen(),
            cursor_screen=cursor_screen,
            screens=QGuiApplication.screens(),
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
        self._accent.setFixedWidth(layout.accent_width)
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

        self._badge.setFont(QFont("Segoe UI Semibold", max(layout.hint_size, 9)))
        self._primary.setFont(QFont("Segoe UI Semibold", layout.primary_size))
        self._secondary.setFont(QFont("Segoe UI", layout.secondary_size))
        self._hint.setFont(QFont("Segoe UI", layout.hint_size))

    def _apply_platform_window_behaviors(self) -> None:
        """Apply native focus and input behavior when the platform supports it."""
        if not is_windows_platform():
            return

        try:
            apply_windows_overlay_styles(int(self._widget.winId()))
        except Exception:
            # Native overlay polish should never take down the Qt runtime.
            return


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
        window = OverlayWindow(
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

    def _drain_commands(self, window: OverlayWindow, app: Any) -> None:
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
