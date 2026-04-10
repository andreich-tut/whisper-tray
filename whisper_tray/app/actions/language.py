"""Language selection actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whisper_tray.app.lifecycle import WhisperTrayApp


class LanguageActions:
    """Handle language selection menu actions."""

    def __init__(self, app: "WhisperTrayApp") -> None:
        self._app = app

    def on_set_language_en(self, icon: object, item: object | None) -> None:
        """Handle selecting English transcription."""
        del icon, item
        self._app._current_language = "en"
        self._app._notify_user("Language: English")

    def on_set_language_ru(self, icon: object, item: object | None) -> None:
        """Handle selecting Russian transcription."""
        del icon, item
        self._app._current_language = "ru"
        self._app._notify_user("Language: Russian")

    def on_set_language_auto(self, icon: object, item: object | None) -> None:
        """Handle selecting automatic language detection."""
        del icon, item
        self._app._current_language = "auto"
        self._app._notify_user("Language: Auto-detect")
