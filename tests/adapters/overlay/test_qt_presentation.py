"""Tests for overlay geometry, screen resolution, and presentation layout."""

from __future__ import annotations

from whisper_tray.adapters.overlay.qt.presentation import (
    geometry_contains_geometry,
    resolve_overlay_coordinates,
    resolve_overlay_layout,
    resolve_overlay_reposition_screen,
    resolve_overlay_screen,
    resolve_overlay_theme,
    update_last_resolved_screen,
)
from whisper_tray.state import AppState, AppStatePresenter, AppStateSnapshot


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
