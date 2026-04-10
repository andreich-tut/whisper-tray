"""
Main application orchestrator.

Coordinates all subsystems: audio, transcription, hotkeys, tray, and clipboard.
CPU-first design with single transcription worker thread (queue-based).
"""

from __future__ import annotations

import logging
import queue
import threading

import numpy as np

from whisper_tray.app_actions import AppSessionActions
from whisper_tray.app_constants import OVERLAY_INSTALL_MESSAGE
from whisper_tray.app_ui import AppUiCoordinator
from whisper_tray.app_workflow import AppWorkflowCoordinator
from whisper_tray.audio.recorder import AudioRecorder
from whisper_tray.audio.transcriber import Transcriber
from whisper_tray.clipboard import ClipboardManager
from whisper_tray.config import AppConfig
from whisper_tray.input.hotkey import HotkeyListener
from whisper_tray.overlay import (
    NullOverlayController,
    OverlayController,
    OverlaySettings,
)
from whisper_tray.state import (
    AppState,
    AppStatePresentation,
    AppStatePresenter,
    AppStatePublisher,
    AppStateSnapshot,
    format_hotkey,
)
from whisper_tray.tray.icon import TrayIcon
from whisper_tray.tray.menu import TrayMenu
from whisper_tray.tray.runtime import (
    PystrayTrayRuntime,
    QtTrayRuntime,
    TrayRuntime,
    should_use_qt_tray,
)
from whisper_tray.types import TrayIcon as PystrayIcon
from whisper_tray.types import TrayMenuItem as PystrayMenuItem

logger = logging.getLogger(__name__)


class WhisperTrayApp:
    """Main application class coordinating all subsystems."""

    def __init__(self, config: AppConfig | None = None) -> None:
        """
        Initialize application.

        Args:
            config: Application configuration. Uses defaults if None.
        """
        self.config = config or AppConfig()
        self.config.log_config()

        self._recorder = AudioRecorder(self.config.audio)
        self._transcriber = Transcriber(self.config.model)
        self._clipboard = ClipboardManager(
            paste_delay=self.config.hotkey.paste_delay,
            auto_paste=self.config.hotkey.auto_paste,
        )
        self._tray_icon = TrayIcon()
        self._overlay: OverlayController = NullOverlayController()

        self._current_language: str = self.config.model.language or "auto"
        self._processing_flash_on = False
        self._state_presenter = self._build_state_presenter()
        initial_snapshot = AppStateSnapshot(
            state=AppState.LOADING_MODEL,
            device=self._transcriber.device,
        )
        self._state_publisher = AppStatePublisher(initial_snapshot)
        self._state_snapshot = initial_snapshot
        self._state_presentation: AppStatePresentation = self._state_presenter.present(
            initial_snapshot
        )

        self._model_load_complete = threading.Event()
        self._flash_event = threading.Event()
        self._flash_timer: threading.Thread | None = None
        self._tray_icon_ref: PystrayIcon | None = None
        self._hotkey_listener: HotkeyListener | None = None
        self._tray_update_lock = threading.Lock()
        self._tray_runtime: TrayRuntime | None = None
        self._clipboard_monitor_stop = threading.Event()
        self._clipboard_monitor: threading.Thread | None = None

        self._transcription_queue: queue.Queue = queue.Queue()
        self._transcription_worker: threading.Thread | None = None
        self._worker_stop = threading.Event()

        self._workflow: AppWorkflowCoordinator | None = None
        self._ui: AppUiCoordinator | None = None
        self._actions: AppSessionActions | None = None

        self._state_publisher.subscribe(self._on_state_changed)

    def _workflow_coordinator(self) -> AppWorkflowCoordinator:
        """Create workflow helpers lazily for reuse and init-free tests."""
        if getattr(self, "_workflow", None) is None:
            self._workflow = AppWorkflowCoordinator(self)
        workflow = self._workflow
        assert workflow is not None
        return workflow

    def _ui_coordinator(self) -> AppUiCoordinator:
        """Create UI/runtime helpers lazily for reuse and init-free tests."""
        if getattr(self, "_ui", None) is None:
            self._ui = AppUiCoordinator(self)
        ui = self._ui
        assert ui is not None
        return ui

    def _session_actions(self) -> AppSessionActions:
        """Create session-action helpers lazily for reuse and init-free tests."""
        if getattr(self, "_actions", None) is None:
            self._actions = AppSessionActions(self)
        actions = self._actions
        assert actions is not None
        return actions

    def _transcription_worker_loop(self) -> None:
        """Background worker that processes transcription requests one at a time."""
        self._workflow_coordinator().transcription_worker_loop()

    def _start_worker(self) -> None:
        """Start the single transcription worker thread."""
        self._workflow_coordinator().start_worker()

    def _stop_worker(self) -> None:
        """Stop the transcription worker and drain queue."""
        self._workflow_coordinator().stop_worker()

    def _transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: str,
    ) -> AppStateSnapshot:
        """Transcribe audio and convert the result into a publishable snapshot."""
        return self._workflow_coordinator().transcribe_audio(audio_data, language)

    def _on_state_changed(self, snapshot: AppStateSnapshot) -> None:
        """Cache and fan out the latest app state to UI components."""
        self._ui_coordinator().on_state_changed(snapshot)

    def _build_state_presenter(self) -> AppStatePresenter:
        """Create the shared presenter from the current runtime settings."""
        return self._ui_coordinator().build_state_presenter()

    def _refresh_presentation_model(self) -> None:
        """Rebuild the shared presenter and rerender the current UI state."""
        self._ui_coordinator().refresh_presentation_model()

    def _build_overlay_settings(self) -> OverlaySettings:
        """Build the explicit overlay runtime settings for the current config."""
        return self._ui_coordinator().build_overlay_settings()

    def _build_snapshot(
        self,
        state: AppState,
        *,
        message: str | None = None,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> AppStateSnapshot:
        """Create a typed app-state snapshot for the current runtime."""
        return self._ui_coordinator().build_snapshot(
            state,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )

    def _publish_snapshot(self, snapshot: AppStateSnapshot) -> None:
        """Publish a pre-built shared app state snapshot."""
        self._ui_coordinator().publish_snapshot(snapshot)

    def _publish_state(
        self,
        state: AppState,
        message: str | None = None,
        *,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> None:
        """Publish a new shared app state."""
        self._ui_coordinator().publish_state(
            state,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )

    def _get_idle_state(self) -> AppState:
        """Return the best non-recording state for the current app conditions."""
        return self._workflow_coordinator().get_idle_state()

    def _clipboard_monitor_loop(self) -> None:
        """Revert the transcript state after the clipboard changes elsewhere."""
        self._workflow_coordinator().clipboard_monitor_loop()

    def _start_clipboard_monitor(self) -> None:
        """Start the lightweight clipboard ownership monitor."""
        self._workflow_coordinator().start_clipboard_monitor()

    def _stop_clipboard_monitor(self) -> None:
        """Stop the clipboard ownership monitor."""
        self._workflow_coordinator().stop_clipboard_monitor()

    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press event."""
        self._workflow_coordinator().on_hotkey_pressed()

    def _on_hotkey_released(self) -> None:
        """Handle hotkey release event."""
        self._workflow_coordinator().on_hotkey_released()

    def _process_transcription(self, audio_data: np.ndarray) -> None:
        """
        Legacy method kept for compatibility. Not used in queue-based design.
        Transcription is now handled by _transcription_worker_loop.
        """
        del audio_data

    def _start_flash_timer(self) -> None:
        """Start background thread that flashes the icon during processing."""
        self._workflow_coordinator().start_flash_timer()

    def _stop_flash_timer(self, next_snapshot: AppStateSnapshot | None = None) -> None:
        """Stop the flash timer."""
        self._workflow_coordinator().stop_flash_timer(next_snapshot=next_snapshot)

    def _get_tray_title(self) -> str:
        """Return the current tray hover text for the active app state."""
        return self._ui_coordinator().get_tray_title()

    def _update_tray_icon(self) -> None:
        """Update the tray icon image and hover text for the current state."""
        self._ui_coordinator().update_tray_icon()

    def _refresh_tray_menu(self, icon: PystrayIcon) -> None:
        """Refresh dynamic tray menu checkmarks when pystray supports it."""
        self._ui_coordinator().refresh_tray_menu(icon)

    def _notify_user(self, message: str) -> None:
        """Show a best-effort tray notification without breaking the app flow."""
        self._ui_coordinator().notify_user(message)

    def _apply_overlay_settings(self, *, render_current_state: bool = True) -> bool:
        """Recreate the overlay controller for the current runtime settings."""
        return self._ui_coordinator().apply_overlay_settings(
            render_current_state=render_current_state
        )

    @staticmethod
    def _format_overlay_position(position: str) -> str:
        """Convert an overlay corner into a readable tray label."""
        return AppSessionActions.format_overlay_position(position)

    @staticmethod
    def _format_overlay_auto_hide(seconds: float) -> str:
        """Convert a ready-state timeout into a readable tray label."""
        return AppSessionActions.format_overlay_auto_hide(seconds)

    @staticmethod
    def _format_overlay_density(density: str) -> str:
        """Convert an overlay density into a readable tray label."""
        return AppSessionActions.format_overlay_density(density)

    @staticmethod
    def _format_overlay_screen(screen: str) -> str:
        """Convert an overlay screen target into a readable tray label."""
        return AppSessionActions.format_overlay_screen(screen)

    def _setup_hotkey_listener(self) -> None:
        """Set up the global hotkey listener."""
        self._session_actions().setup_hotkey_listener()

    def _prepare_tray_runtime(self) -> None:
        """Prepare the preferred tray runtime with a safe Qt-to-pystray fallback."""
        self._tray_runtime = self._create_tray_runtime()
        try:
            self._tray_runtime.prepare(self)
        except Exception:
            if not isinstance(self._tray_runtime, QtTrayRuntime):
                raise

            logger.warning(
                "Qt tray runtime failed to start. Falling back to pystray "
                "and preserving overlay settings so the legacy backend can "
                "retry overlay startup.",
                exc_info=True,
            )
            self._tray_runtime = PystrayTrayRuntime()
            self._tray_runtime.prepare(self)

    def _create_tray_runtime(self) -> TrayRuntime:
        """Choose the best tray runtime for the current environment."""
        tray_backend = self.config.ui.tray_backend

        if tray_backend == "pystray":
            return PystrayTrayRuntime()

        if should_use_qt_tray():
            return QtTrayRuntime()

        if tray_backend == "qt":
            logger.warning(
                "TRAY_BACKEND=qt requested, but PySide6 is unavailable. "
                "Falling back to pystray."
            )
        return PystrayTrayRuntime()

    def _setup_tray_menu(self) -> TrayMenu:
        """Set up the tray context menu."""
        return self._ui_coordinator().setup_tray_menu()

    def _on_toggle_auto_paste(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle toggle auto-paste menu action."""
        self._session_actions().on_toggle_auto_paste(icon, item)

    def _on_set_language_en(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle set language to English."""
        self._session_actions().on_set_language_en(icon, item)

    def _on_set_language_ru(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle set language to Russian."""
        self._session_actions().on_set_language_ru(icon, item)

    def _on_set_language_auto(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle set language to auto-detect."""
        self._session_actions().on_set_language_auto(icon, item)

    def _on_toggle_overlay(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle toggling the optional on-screen overlay."""
        self._session_actions().on_toggle_overlay(icon, item)

    def _on_set_overlay_position(
        self,
        position: str,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting a tray-managed overlay corner."""
        self._session_actions().on_set_overlay_position(position, icon, item)

    def _on_set_overlay_auto_hide(
        self,
        seconds: float,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting the ready-state overlay timeout."""
        self._session_actions().on_set_overlay_auto_hide(seconds, icon, item)

    def _on_set_overlay_screen(
        self,
        screen: str,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting the overlay display target."""
        self._session_actions().on_set_overlay_screen(screen, icon, item)

    def _on_set_overlay_density(
        self,
        density: str,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting the overlay presentation density."""
        self._session_actions().on_set_overlay_density(density, icon, item)

    def _on_exit(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle exit menu action."""
        self._session_actions().on_exit(icon, item)

    def _load_model_in_background(self) -> None:
        """Load the Whisper model in background thread."""
        self._workflow_coordinator().load_model_in_background()

    def run(self) -> None:
        """
        Main entry point. Starts the application and blocks until exit.

        The tray icon appears immediately; model loads asynchronously
        in the background so the user sees the app right away.
        """
        logger.info("Starting WhisperTray...")
        logger.info("Hotkey: %s", format_hotkey(self.config.hotkey.hotkey))
        logger.info("Auto-paste: %s", self.config.hotkey.auto_paste)
        self._prepare_tray_runtime()

        overlay_requested = self.config.overlay.enabled
        overlay_active = self._apply_overlay_settings(render_current_state=True)
        if overlay_requested and not overlay_active:
            self._notify_user(OVERLAY_INSTALL_MESSAGE)

        threading.Thread(
            target=self._load_model_in_background,
            daemon=True,
            name="model-loader",
        ).start()

        self._start_worker()
        self._start_clipboard_monitor()

        self._setup_hotkey_listener()
        if self._hotkey_listener:
            self._hotkey_listener.start()

        try:
            if self._tray_runtime is None:
                raise RuntimeError("tray runtime not prepared")
            self._tray_runtime.run()
        finally:
            self._stop_worker()
            self._stop_clipboard_monitor()
            if self._hotkey_listener:
                self._hotkey_listener.stop()
            self._overlay.close()
            logger.info("WhisperTray exited.")
