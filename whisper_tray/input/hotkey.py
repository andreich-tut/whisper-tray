"""
Hotkey detection module.

Handles global keyboard event listening using pynput.
"""

from whisper_tray.adapters.hotkey.pynput_listener import HotkeyListener

__all__ = ["HotkeyListener"]
