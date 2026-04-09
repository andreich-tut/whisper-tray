"""Tests for clipboard and paste operations."""

import sys
from unittest.mock import MagicMock, patch

from whisper_tray.clipboard import ClipboardManager


class TestClipboardManager:
    """Test clipboard manager."""

    def test_init_defaults(self) -> None:
        """Test initialization with default values."""
        mgr = ClipboardManager()
        assert mgr.paste_delay == 0.1
        assert mgr.auto_paste is True

    def test_init_custom(self) -> None:
        """Test initialization with custom values."""
        mgr = ClipboardManager(paste_delay=0.2, auto_paste=False)
        assert mgr.paste_delay == 0.2
        assert mgr.auto_paste is False

    def test_paste_modifier_platform_aware(self) -> None:
        """Test that paste modifier is correct for the platform."""
        mgr = ClipboardManager()
        if sys.platform == "darwin":
            assert mgr._paste_modifier.name == "cmd"
        else:
            assert mgr._paste_modifier.name == "ctrl"

    @patch("whisper_tray.clipboard.pyperclip")
    def test_copy_text(self, mock_pyperclip: MagicMock) -> None:
        """Test copying text to clipboard."""
        mgr = ClipboardManager(auto_paste=False)
        mgr.copy_and_paste("hello")
        mock_pyperclip.copy.assert_called_once_with("hello")

    def test_toggle_auto_paste(self) -> None:
        """Test toggling auto-paste."""
        mgr = ClipboardManager(auto_paste=True)
        assert mgr.auto_paste is True

        new_state = mgr.toggle_auto_paste()
        assert new_state is False
        assert mgr.auto_paste is False

        new_state = mgr.toggle_auto_paste()
        assert new_state is True
        assert mgr.auto_paste is True
