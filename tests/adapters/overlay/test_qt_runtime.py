"""Tests for the Qt overlay window factory."""

from __future__ import annotations

import pytest

from whisper_tray.adapters.overlay.qt.runtime import create_overlay_window


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
        "whisper_tray.adapters.overlay.qt.runtime.OverlayWindow",
        FakeCardWindow,
    )

    window = create_overlay_window(
        position="top-left",
        screen_target="cursor",
    )

    assert isinstance(window, FakeCardWindow)
    assert created == [("top-left", "cursor")]
