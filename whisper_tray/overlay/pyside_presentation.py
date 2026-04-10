"""Presentation, theme, and geometry helpers for the PySide overlay."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

from whisper_tray.state import AppState, AppStatePresentation


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


def resolve_overlay_screen(
    *,
    screen_target: str,
    primary_screen: Any | None,
    cursor_screen: Any | None,
    screens: Sequence[Any],
) -> Any | None:
    """Choose the screen the overlay should render on."""
    del screens
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
