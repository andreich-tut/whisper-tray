"""Tests for hotkey detection module."""

from unittest.mock import MagicMock, patch

from whisper_tray.input.hotkey import HotkeyListener


class TestHotkeyListener:
    """Test hotkey listener."""

    def test_init(self) -> None:
        """Test initialization."""
        listener = HotkeyListener(hotkey={"ctrl", "space"})
        assert listener.hotkey == {"ctrl", "space"}

    def test_get_key_name_char(self) -> None:
        """Test getting key name from character key."""
        mock_key = MagicMock()
        mock_key.char = "a"
        mock_key.name = None
        assert HotkeyListener._get_key_name(mock_key) == "a"

    def test_get_key_name_ctrl(self) -> None:
        """Test getting key name from ctrl key."""
        mock_key = MagicMock()
        mock_key.char = None
        mock_key.name = "ctrl_l"
        assert HotkeyListener._get_key_name(mock_key) == "ctrl"

    def test_get_key_name_space(self) -> None:
        """Test getting key name from space key."""
        mock_key = MagicMock()
        mock_key.char = None
        mock_key.name = "space"
        assert HotkeyListener._get_key_name(mock_key) == "space"

    @patch("whisper_tray.adapters.hotkey.pynput_listener.keyboard.Listener")
    def test_start(self, mock_listener_class: MagicMock) -> None:
        """Test starting listener."""
        mock_listener_instance = MagicMock()
        mock_listener_class.return_value = mock_listener_instance

        listener = HotkeyListener(hotkey={"ctrl", "space"})
        listener.start()

        mock_listener_class.assert_called_once()
        mock_listener_instance.start.assert_called_once()

    @patch("whisper_tray.adapters.hotkey.pynput_listener.keyboard.Listener")
    def test_stop(self, mock_listener_class: MagicMock) -> None:
        """Test stopping listener."""
        mock_listener_instance = MagicMock()
        mock_listener_class.return_value = mock_listener_instance

        listener = HotkeyListener(hotkey={"ctrl", "space"})
        listener.start()
        listener.stop()

        mock_listener_instance.stop.assert_called_once()
