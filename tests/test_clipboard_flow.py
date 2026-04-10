"""Tests for clipboard manager copy and controller flows."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import whisper_tray.adapters.clipboard.controller as controller_module
import whisper_tray.adapters.clipboard.core as clipboard_core
from whisper_tray.adapters.clipboard.core import ClipboardManager, PasteAttemptResult


def _build_keyboard_controller() -> MagicMock:
    """Create a mock keyboard controller with a context-managed modifier."""
    controller = MagicMock()
    pressed_context = MagicMock()
    pressed_context.__enter__.return_value = None
    pressed_context.__exit__.return_value = False
    controller.pressed.return_value = pressed_context
    return controller


class TestClipboardFlow:
    """Test clipboard manager copy behavior and controller injection."""

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

    @patch("whisper_tray.adapters.clipboard.core.pyperclip")
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
        controller = _build_keyboard_controller()
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))

        monkeypatch.setattr(controller_module, "KeyboardController", lambda: controller)
        monkeypatch.setattr(controller_module, "Key", key)
        monkeypatch.setattr(clipboard_core.sys, "platform", "linux")
        monkeypatch.setattr(clipboard_core.time, "sleep", lambda _: None)
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_paste_shortcut",
            MagicMock(return_value=False),
        )

        with patch("whisper_tray.adapters.clipboard.core.pyperclip") as mock_pyperclip:
            mgr = ClipboardManager(auto_paste=True)
            mgr.copy_and_paste("hello")

        mock_pyperclip.copy.assert_called_once_with("hello")
        controller.pressed.assert_called_once_with(key.ctrl)
        controller.press.assert_called_once_with("v")
        controller.release.assert_called_once_with("v")

    def test_copy_and_paste_uses_native_windows_shortcut_when_available(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Windows should prefer the native Ctrl+V injection path."""
        native_shortcut = MagicMock(return_value=True)

        monkeypatch.setattr(clipboard_core.sys, "platform", "win32")
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_paste_shortcut",
            native_shortcut,
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_windows_shift_insert_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_pyautogui_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(clipboard_core.time, "sleep", lambda _: None)

        with patch("whisper_tray.adapters.clipboard.core.pyperclip") as mock_pyperclip:
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
        controller = _build_keyboard_controller()
        key = SimpleNamespace(ctrl=SimpleNamespace(name="ctrl"))
        native_shortcut = MagicMock(return_value=False)

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
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(
            clipboard_core,
            "send_pyautogui_shortcut",
            MagicMock(return_value=False),
        )
        monkeypatch.setattr(clipboard_core.time, "sleep", lambda _: None)

        with patch("whisper_tray.adapters.clipboard.core.pyperclip") as mock_pyperclip:
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
