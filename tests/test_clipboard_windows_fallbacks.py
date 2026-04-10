"""Tests for Windows-specific clipboard fallback order."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import whisper_tray.clipboard.controller as controller_module
import whisper_tray.clipboard.core as clipboard_core
from whisper_tray.clipboard import ClipboardManager, PasteAttemptResult


def _build_keyboard_controller() -> MagicMock:
    """Create a mock keyboard controller with a context-managed modifier."""
    controller = MagicMock()
    pressed_context = MagicMock()
    pressed_context.__enter__.return_value = None
    pressed_context.__exit__.return_value = False
    controller.pressed.return_value = pressed_context
    return controller


class TestClipboardWindowsFallbacks:
    """Test Windows-only fallback behavior."""

    def test_copy_and_paste_keeps_clipboard_when_auto_paste_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Paste failures should not raise after the text is copied."""
        controller = _build_keyboard_controller()
        controller.pressed.side_effect = RuntimeError("paste failed")
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        native_shortcut = MagicMock(return_value=False)
        shift_insert_shortcut = MagicMock(return_value=False)
        pyautogui_shortcut = MagicMock(return_value=False)

        monkeypatch.setattr(controller_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(controller_module, "Key", key)
        monkeypatch.setattr(clipboard_core.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_paste_shortcut",
            native_shortcut,
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_shift_insert_shortcut",
            shift_insert_shortcut,
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_pyautogui_shortcut",
            pyautogui_shortcut,
        )
        monkeypatch.setattr(clipboard_core.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.core.pyperclip") as mock_pyperclip:
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
        controller = _build_keyboard_controller()
        controller.pressed.side_effect = RuntimeError("paste failed")
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        native_shortcut = MagicMock(return_value=False)
        shift_insert_shortcut = MagicMock(return_value=True)

        monkeypatch.setattr(controller_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(controller_module, "Key", key)
        monkeypatch.setattr(clipboard_core.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_paste_shortcut",
            native_shortcut,
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_shift_insert_shortcut",
            shift_insert_shortcut,
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_pyautogui_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(clipboard_core.time, "sleep", lambda _: None)

        with patch("whisper_tray.clipboard.core.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            result = mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        native_shortcut.assert_called_once_with()
        shift_insert_shortcut.assert_called_once_with()
        assert result == PasteAttemptResult(
            succeeded=True,
            method="native Shift+Insert",
        )
