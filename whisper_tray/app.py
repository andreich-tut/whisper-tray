"""
Main application orchestrator.

Coordinates all subsystems: audio, transcription, hotkeys, tray, and clipboard.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np
import pystray

from whisper_tray.audio.recorder import AudioRecorder
from whisper_tray.audio.transcriber import Transcriber
from whisper_tray.clipboard import ClipboardManager
from whisper_tray.config import AppConfig
from whisper_tray.input.hotkey import HotkeyListener
from whisper_tray.tray.icon import TrayIcon
from whisper_tray.tray.menu import TrayMenu

logger = logging.getLogger(__name__)


class WhisperTrayApp:
    """Main application class coordinating all subsystems."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        """
        Initialize application.

        Args:
            config: Application configuration. Uses defaults if None.
        """
        self.config = config or AppConfig()
        self.config.log_config()

        # Initialize subsystems
        self._recorder = AudioRecorder(self.config.audio)
        self._transcriber = Transcriber(self.config.model)
        self._clipboard = ClipboardManager(
            paste_delay=self.config.hotkey.paste_delay,
            auto_paste=self.config.hotkey.auto_paste,
        )
        self._tray_icon = TrayIcon()

        # State
        self._is_recording = False
        self._current_language: str = self.config.model.language or "auto"

        # Threading
        self._model_load_complete = threading.Event()
        self._tray_icon_ref: Optional[pystray.Icon] = None
        self._hotkey_listener: Optional[HotkeyListener] = None

    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press event."""
        if not self._transcriber.is_ready:
            logger.info("Model not ready, ignoring hotkey")
            return

        self._is_recording = True
        self._recorder.start_recording()
        logger.info("Recording started...")
        self._update_tray_icon()

    def _on_hotkey_released(self) -> None:
        """Handle hotkey release event."""
        self._is_recording = False
        audio_data = self._recorder.stop_recording()
        logger.info(f"Recording stopped. Captured {len(audio_data)} samples.")

        # Transcribe in a separate thread to not block hotkey listener
        threading.Thread(
            target=self._process_transcription,
            args=(audio_data,),
            daemon=True,
        ).start()

        # Update tray icon
        self._update_tray_icon()

    def _process_transcription(self, audio_data: np.ndarray) -> None:
        """Process transcription in background thread."""
        text = self._transcriber.transcribe(audio_data, self._current_language)
        if text:
            logger.info(f"Recognized text: {text}")
            self._clipboard.copy_and_paste(text)

    def _update_tray_icon(self) -> None:
        """Update the tray icon to reflect current state."""
        if self._tray_icon_ref:
            self._tray_icon.update_icon(
                self._tray_icon_ref,
                self._is_recording,
                self._transcriber.is_ready,
            )

    def _setup_hotkey_listener(self) -> None:
        """Set up the global hotkey listener."""
        self._hotkey_listener = HotkeyListener(
            hotkey=self.config.hotkey.hotkey,
            on_press=self._on_hotkey_pressed,
            on_release=self._on_hotkey_released,
        )

    def _setup_tray_menu(self) -> TrayMenu:
        """
        Set up the tray context menu.

        Returns:
            Configured TrayMenu instance
        """
        return TrayMenu(
            on_toggle_auto_paste=self._on_toggle_auto_paste,
            on_set_language_en=self._on_set_language_en,
            on_set_language_ru=self._on_set_language_ru,
            on_set_language_auto=self._on_set_language_auto,
            on_exit=self._on_exit,
            get_auto_paste_state=lambda: self._clipboard.auto_paste,
            get_language_state=lambda: self._current_language,
        )

    def _on_toggle_auto_paste(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle toggle auto-paste menu action."""
        new_state = self._clipboard.toggle_auto_paste()
        icon.notify(f"Auto-paste {'enabled' if new_state else 'disabled'}")

    def _on_set_language_en(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle set language to English."""
        self._current_language = "en"
        icon.notify("Language: English")

    def _on_set_language_ru(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle set language to Russian."""
        self._current_language = "ru"
        icon.notify("Language: Russian")

    def _on_set_language_auto(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle set language to auto-detect."""
        self._current_language = "auto"
        icon.notify("Language: Auto-detect")

    def _on_exit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle exit menu action."""
        icon.stop()

    def _load_model_in_background(self) -> None:
        """Load the Whisper model in background thread."""
        self._transcriber.load_model()
        self._model_load_complete.set()

    def run(self) -> None:
        """
        Main entry point. Starts the application and blocks until exit.
        """
        logger.info("Starting WhisperTray...")
        logger.info(f"Hotkey: {'+'.join(sorted(self.config.hotkey.hotkey))}")
        logger.info(f"Auto-paste: {self.config.hotkey.auto_paste}")

        # Start model loading in background thread
        threading.Thread(
            target=self._load_model_in_background,
            daemon=True,
        ).start()

        # Wait for model to be ready
        self._model_load_complete.wait()

        # Create initial icon image
        icon_image = self._tray_icon.get_icon_image(
            is_recording=False,
            model_ready=self._transcriber.is_ready,
        )

        # Determine tooltip
        tooltip = self._tray_icon.get_tooltip(
            is_recording=False,
            model_ready=self._transcriber.is_ready,
            device=self._transcriber.device,
        )

        # Set up tray menu
        menu = self._setup_tray_menu()

        # Create tray icon
        icon = pystray.Icon(
            "WhisperTray",
            icon_image,
            tooltip,
            menu.create_menu(),
        )

        # Store reference for updates
        self._tray_icon_ref = icon

        # Set up hotkey listener
        self._setup_hotkey_listener()
        if self._hotkey_listener:
            self._hotkey_listener.start()

        # Run tray icon (blocks main thread)
        icon.run()

        # Cleanup
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        logger.info("WhisperTray exited.")
