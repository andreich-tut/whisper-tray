"""Tests for clipboard and paste operations."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import whisper_tray.clipboard as clipboard_module
from whisper_tray.clipboard import ClipboardManager, PasteAttemptResult


class TestClipboardManager:
    """Test clipboard manager."""

    @staticmethod
    def _build_keyboard_controller() -> MagicMock:
        """Create a mock keyboard controller with a context-managed modifier."""
        controller = MagicMock()
        pressed_context = MagicMock()
        pressed_context.__enter__.return_value = None
        pressed_context.__exit__.return_value = False
        controller.pressed.return_value = pressed_context
        return controller

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

    def test_copy_and_paste_uses_controller_shortcut_off_windows(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Non-Windows auto-paste should keep using the controller shortcut."""
        controller = self._build_keyboard_controller()
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        send_windows_shortcut = MagicMock(return_value=False)

        monkeypatch.setattr(clipboard_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(clipboard_module, "Key", key)
        monkeypatch.setattr(clipboard_module.sys, "platform", "linux")
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_paste_shortcut",
            send_windows_shortcut,
        )
        monkeypatch.setattr(clipboard_module.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        send_windows_shortcut.assert_not_called()
        controller.pressed.assert_called_once_with(key.ctrl)
        controller.press.assert_called_once_with("v")
        controller.release.assert_called_once_with("v")

    def test_copy_and_paste_uses_native_windows_shortcut_when_available(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Windows should prefer the native Ctrl+V injection path."""
        native_shortcut = MagicMock(return_value=True)

        monkeypatch.setattr(clipboard_module.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_paste_shortcut",
            native_shortcut,
        )
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_shift_insert_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(
            clipboard_module,
            "_send_pyautogui_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(clipboard_module.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            result = mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        native_shortcut.assert_called_once_with()
        assert result == PasteAttemptResult(
            succeeded=True,
            method="native Ctrl+V",
        )

    def test_copy_and_paste_falls_back_when_windows_shortcut_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Windows should fall back to the controller shortcut if needed."""
        controller = self._build_keyboard_controller()
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        native_shortcut = MagicMock(return_value=False)

        monkeypatch.setattr(clipboard_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(clipboard_module, "Key", key)
        monkeypatch.setattr(clipboard_module.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_paste_shortcut",
            native_shortcut,
        )
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_shift_insert_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(
            clipboard_module,
            "_send_pyautogui_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(clipboard_module.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            result = mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        native_shortcut.assert_called_once_with()
        controller.pressed.assert_called_once_with(key.ctrl)
        controller.press.assert_called_once_with("v")
        controller.release.assert_called_once_with("v")
        assert result == PasteAttemptResult(
            succeeded=True,
            method="controller Ctrl+V",
        )

    def test_copy_and_paste_keeps_clipboard_when_auto_paste_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Paste failures should not raise after the text is copied."""
        controller = self._build_keyboard_controller()
        controller.pressed.side_effect = RuntimeError("paste failed")
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        native_shortcut = MagicMock(return_value=False)

        monkeypatch.setattr(clipboard_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(clipboard_module, "Key", key)
        monkeypatch.setattr(clipboard_module.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_paste_shortcut",
            native_shortcut,
        )
        shift_insert_shortcut = MagicMock(return_value=False)
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_shift_insert_shortcut",
            shift_insert_shortcut,
        )
        pyautogui_shortcut = MagicMock(return_value=False)
        monkeypatch.setattr(
            clipboard_module,
            "_send_pyautogui_shortcut",
            pyautogui_shortcut,
        )
        monkeypatch.setattr(clipboard_module.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            result = mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        native_shortcut.assert_called_once_with()
        shift_insert_shortcut.assert_called_once_with()
        assert pyautogui_shortcut.call_count == 2
        assert result == PasteAttemptResult(
            succeeded=False,
            method="PyAutoGUI Shift+Insert",
        )

    def test_copy_and_paste_uses_shift_insert_after_ctrl_v_failures_on_windows(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Windows should try Shift+Insert when Ctrl+V-based fallbacks all fail."""
        controller = self._build_keyboard_controller()
        controller.pressed.side_effect = RuntimeError("paste failed")
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        native_shortcut = MagicMock(return_value=False)
        shift_insert_shortcut = MagicMock(return_value=True)

        monkeypatch.setattr(clipboard_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(clipboard_module, "Key", key)
        monkeypatch.setattr(clipboard_module.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_paste_shortcut",
            native_shortcut,
        )
        monkeypatch.setattr(
            clipboard_module,
            "_send_windows_shift_insert_shortcut",
            shift_insert_shortcut,
        )
        monkeypatch.setattr(
            clipboard_module,
            "_send_pyautogui_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(clipboard_module.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            result = mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        native_shortcut.assert_called_once_with()
        shift_insert_shortcut.assert_called_once_with()
        assert result == PasteAttemptResult(
            succeeded=True,
            method="native Shift+Insert",
        )

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

    @patch("whisper_tray.clipboard.pyperclip")
    def test_owns_clipboard_returns_true_after_copy(
        self,
        mock_pyperclip: MagicMock,
    ) -> None:
        """Clipboard ownership should match the last copied transcript text."""
        mock_pyperclip.paste.return_value = "hello"
        mgr = ClipboardManager(auto_paste=False)

        mgr.copy_and_paste("hello")

        assert mgr.owns_clipboard() is True

    @patch("whisper_tray.clipboard.pyperclip")
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
