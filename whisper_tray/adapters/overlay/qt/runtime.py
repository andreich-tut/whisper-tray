"""Qt window and runtime implementation for the PySide overlay backend."""

from __future__ import annotations

import html
import queue
from typing import Any

from whisper_tray.core.overlay import (
    OverlayCommand,
    OverlayCommandKind,
    OverlaySettings,
    OverlayStartupCallback,
)
from whisper_tray.core.state import AppState, AppStatePresentation
from whisper_tray.overlay.pyside_presentation import (
    OverlayLayout,
    resolve_overlay_coordinates,
    resolve_overlay_layout,
    resolve_overlay_reposition_screen,
    resolve_overlay_screen,
    resolve_overlay_theme,
    update_last_resolved_screen,
)
from whisper_tray.platform.windows.overlay_styles import (
    apply_windows_overlay_styles,
    enable_windows_per_monitor_dpi_awareness,
    is_windows_platform,
    should_disable_native_window_shadow,
    should_use_card_shadow,
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
        settings: OverlaySettings,
    ) -> None:
        self._commands = commands
        self._settings = settings

    def run(self, startup_callback: OverlayStartupCallback) -> None:
        """Start the Qt event loop and process overlay commands."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        enable_windows_per_monitor_dpi_awareness()
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        window = create_overlay_window(
            position=self._settings.position,
            screen_target=self._settings.screen_target,
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
