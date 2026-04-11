"""Tests for overlay-related config values."""

import os
from typing import Generator

import pytest

from whisper_tray.config import OverlayConfig


@pytest.fixture(autouse=True)
def _clear_env() -> Generator[None, None, None]:
    """Clear environment variables that could affect config tests."""
    env_vars = [
        "OVERLAY_ENABLED",
        "OVERLAY_AUTO_HIDE_SECONDS",
        "OVERLAY_POSITION",
        "OVERLAY_SCREEN",
        "OVERLAY_DENSITY",
    ]
    saved: dict[str, str | None] = {}
    for var in env_vars:
        saved[var] = os.environ.pop(var, None)
    yield
    for var, value in saved.items():
        if value is not None:
            os.environ[var] = value


class TestOverlayConfig:
    """Test overlay configuration."""

    def test_defaults(self) -> None:
        """Overlay should stay disabled until a UI backend is installed."""
        config = OverlayConfig()
        assert config.enabled is False
        assert config.auto_hide_seconds == 1.5
        assert config.position == "bottom-right"
        assert config.screen == "primary"
        assert config.density == "detailed"

    def test_env_var_bindings(self) -> None:
        """Overlay config should read environment variables."""
        os.environ["OVERLAY_ENABLED"] = "true"
        os.environ["OVERLAY_AUTO_HIDE_SECONDS"] = "0"
        os.environ["OVERLAY_POSITION"] = "top-left"
        os.environ["OVERLAY_SCREEN"] = "cursor"
        os.environ["OVERLAY_DENSITY"] = "compact"

        config = OverlayConfig()
        assert config.enabled is True
        assert config.auto_hide_seconds == 0
        assert config.position == "top-left"
        assert config.screen == "cursor"
        assert config.density == "compact"

    def test_invalid_position_falls_back_to_bottom_right(self) -> None:
        """Unknown positions should degrade to the default corner."""
        config = OverlayConfig(position="center")
        assert config.position == "bottom-right"

    def test_invalid_density_falls_back_to_detailed(self) -> None:
        """Unknown densities should degrade to the default presentation."""
        config = OverlayConfig(density="wide")
        assert config.density == "detailed"

    def test_invalid_screen_falls_back_to_primary(self) -> None:
        """Unknown screen targets should degrade to the primary display."""
        config = OverlayConfig(screen="secondary")
        assert config.screen == "primary"
