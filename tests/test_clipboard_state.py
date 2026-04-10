"""Tests for clipboard ownership and local state."""

from unittest.mock import MagicMock, patch

from whisper_tray.clipboard import ClipboardManager


class TestClipboardState:
    """Test clipboard manager state tracking."""

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

    @patch("whisper_tray.adapters.clipboard.core.pyperclip")
    def test_owns_clipboard_returns_true_after_copy(
        self,
        mock_pyperclip: MagicMock,
    ) -> None:
        """Clipboard ownership should match the last copied transcript text."""
        mock_pyperclip.paste.return_value = "hello"
        mgr = ClipboardManager(auto_paste=False)

        mgr.copy_and_paste("hello")

        assert mgr.owns_clipboard() is True

    @patch("whisper_tray.adapters.clipboard.core.pyperclip")
    def test_owns_clipboard_returns_false_after_external_change(
        self,
        mock_pyperclip: MagicMock,
    ) -> None:
        """Clipboard ownership should clear when another app replaces the text."""
        mock_pyperclip.paste.return_value = "someone else"
        mgr = ClipboardManager(auto_paste=False)

        mgr.copy_and_paste("hello")

        assert mgr.owns_clipboard() is False

    def test_owns_clipboard_returns_false_before_copy(self) -> None:
        """Clipboard ownership should be false until WhisperTray copies text."""
        mgr = ClipboardManager(auto_paste=False)

        assert mgr.owns_clipboard() is False
