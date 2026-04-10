"""
Main application orchestrator.

Coordinates all subsystems: audio, transcription, hotkeys, tray, and clipboard.
CPU-first design with single transcription worker thread (queue-based).
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

import numpy as np

from whisper_tray.audio.recorder import AudioRecorder
from whisper_tray.audio.transcriber import Transcriber
from whisper_tray.clipboard import ClipboardManager
from whisper_tray.config import AppConfig
from whisper_tray.input.hotkey import HotkeyListener
from whisper_tray.overlay import NullOverlayController, OverlayController
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
OVERLAY_INSTALL_MESSAGE = (
    'Overlay unavailable. Install the UI extras with `pip install -e ".[ui]"`.'
)


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
        self._overlay: OverlayController = NullOverlayController()

        # State
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

        # Threading
        self._model_load_complete = threading.Event()
        self._flash_event = threading.Event()
        self._flash_timer: Optional[threading.Thread] = None
        self._tray_icon_ref: Optional[PystrayIcon] = None
        self._hotkey_listener: Optional[HotkeyListener] = None
        self._tray_update_lock = threading.Lock()
        self._tray_runtime: TrayRuntime | None = None
        self._clipboard_monitor_stop = threading.Event()
        self._clipboard_monitor: Optional[threading.Thread] = None

        # Transcription work queue (single worker thread)
        self._transcription_queue: queue.Queue = queue.Queue()
        self._transcription_worker: Optional[threading.Thread] = None
        self._worker_stop = threading.Event()

        self._state_publisher.subscribe(self._on_state_changed)

    def _transcription_worker_loop(self) -> None:
        """Background worker that processes transcription requests one at a time."""
        while not self._worker_stop.is_set():
            try:
                item = self._transcription_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            audio_data, lang = item
            next_snapshot = self._build_snapshot(AppState.READY)
            try:
                next_snapshot = self._transcribe_audio(audio_data, lang)
            except Exception as e:
                logger.error(f"Transcription worker error: {e}")
                next_snapshot = self._build_snapshot(
                    AppState.ERROR,
                    message=str(e),
                )
            finally:
                self._transcription_queue.task_done()
                self._stop_flash_timer(next_snapshot=next_snapshot)

    def _start_worker(self) -> None:
        """Start the single transcription worker thread."""
        self._worker_stop.clear()
        self._transcription_worker = threading.Thread(
            target=self._transcription_worker_loop,
            daemon=True,
            name="transcription-worker",
        )
        self._transcription_worker.start()

    def _stop_worker(self) -> None:
        """Stop the transcription worker and drain queue."""
        self._worker_stop.set()
        self._flash_event.set()
        if self._flash_timer and self._flash_timer.is_alive():
            self._flash_timer.join(timeout=1.0)
        self._flash_timer = None
        # Drain pending work
        while not self._transcription_queue.empty():
            try:
                self._transcription_queue.get_nowait()
                self._transcription_queue.task_done()
            except queue.Empty:
                break
        if self._transcription_worker:
            self._transcription_worker.join(timeout=2.0)

    def _transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: str,
    ) -> AppStateSnapshot:
        """Transcribe audio and convert the result into a publishable snapshot."""
        text = self._transcriber.transcribe(audio_data, language)
        if not text:
            return self._build_snapshot(AppState.READY)

        logger.info("Recognized text: %s", text)
        paste_result = self._clipboard.copy_and_paste(text)
        if paste_result is not None and not paste_result.succeeded:
            self._notify_user("Auto-paste failed. Text is still in the clipboard.")

        return self._build_snapshot(
            AppState.TRANSCRIBED,
            transcript=text,
            auto_pasted=bool(paste_result and paste_result.succeeded),
        )

    def _on_state_changed(self, snapshot: AppStateSnapshot) -> None:
        """Cache and fan out the latest app state to UI components."""
        self._state_snapshot = snapshot
        self._state_presentation = self._state_presenter.present(snapshot)
        self._overlay.show_state(self._state_presentation)
        self._update_tray_icon()

    def _build_state_presenter(self) -> AppStatePresenter:
        """Create the shared presenter from the current runtime settings."""
        return AppStatePresenter(
            hotkey_label=format_hotkey(self.config.hotkey.hotkey),
            ready_auto_hide_seconds=self.config.overlay.auto_hide_seconds,
            overlay_density=self.config.overlay.density,
        )

    def _refresh_presentation_model(self) -> None:
        """Rebuild the shared presenter and rerender the current UI state."""
        self._state_presenter = self._build_state_presenter()
        self._on_state_changed(self._state_snapshot)

    def _build_snapshot(
        self,
        state: AppState,
        *,
        message: str | None = None,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> AppStateSnapshot:
        """Create a typed app-state snapshot for the current runtime."""
        return AppStateSnapshot(
            state=state,
            device=self._transcriber.device,
            message=message,
            transcript=transcript,
            auto_pasted=auto_pasted,
        )

    def _publish_snapshot(self, snapshot: AppStateSnapshot) -> None:
        """Publish a pre-built shared app state snapshot."""
        self._state_publisher.publish_snapshot(snapshot)

    def _publish_state(
        self,
        state: AppState,
        message: str | None = None,
        *,
        transcript: str | None = None,
        auto_pasted: bool = False,
    ) -> None:
        """Publish a new shared app state."""
        self._publish_snapshot(
            self._build_snapshot(
                state,
                message=message,
                transcript=transcript,
                auto_pasted=auto_pasted,
            )
        )

    def _get_idle_state(self) -> AppState:
        """Return the best non-recording state for the current app conditions."""
        if self._transcription_queue.unfinished_tasks > 0:
            return AppState.PROCESSING
        if self._transcriber.is_ready:
            return AppState.READY
        if self._model_load_complete.is_set():
            return AppState.ERROR
        return AppState.LOADING_MODEL

    def _clipboard_monitor_loop(self) -> None:
        """Revert the transcript state after the clipboard changes elsewhere."""
        while not self._clipboard_monitor_stop.wait(0.25):
            if self._state_snapshot.state is not AppState.TRANSCRIBED:
                continue
            if self._clipboard.owns_clipboard():
                continue
            self._publish_state(AppState.READY)

    def _start_clipboard_monitor(self) -> None:
        """Start the lightweight clipboard ownership monitor."""
        self._clipboard_monitor_stop.clear()
        self._clipboard_monitor = threading.Thread(
            target=self._clipboard_monitor_loop,
            daemon=True,
            name="clipboard-monitor",
        )
        self._clipboard_monitor.start()

    def _stop_clipboard_monitor(self) -> None:
        """Stop the clipboard ownership monitor."""
        self._clipboard_monitor_stop.set()
        if self._clipboard_monitor and self._clipboard_monitor.is_alive():
            self._clipboard_monitor.join(timeout=1.0)
        self._clipboard_monitor = None

    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press event."""
        if not self._transcriber.is_ready:
            logger.info("Model not ready, ignoring hotkey")
            if self._model_load_complete.is_set():
                self._publish_state(AppState.ERROR, message="Model failed to load.")
            return

        try:
            self._recorder.start_recording()
            logger.info("Recording started...")
            self._publish_state(AppState.RECORDING)
        except Exception as e:
            logger.error(f"Failed to start recording on hotkey press: {e}")
            self._publish_state(
                AppState.ERROR,
                message="Recording failed. Try closing apps or using DEVICE=cpu.",
            )
            self._notify_user(
                "Recording failed: insufficient memory. "
                "Try closing apps or using DEVICE=cpu"
            )

    def _on_hotkey_released(self) -> None:
        """Handle hotkey release event."""
        audio_data = self._recorder.stop_recording()
        logger.info(f"Recording stopped. Captured {len(audio_data)} samples.")

        # Don't process very short recordings
        duration = len(audio_data) / self.config.audio.sample_rate
        if duration < self.config.audio.min_recording_duration:
            logger.info(
                f"Ignoring short recording ({duration:.2f}s < "
                f"{self.config.audio.min_recording_duration}s)"
            )
            self._publish_state(self._get_idle_state())
            return

        # Reject if queue already has pending work (avoid backlog)
        if self._transcription_queue.unfinished_tasks >= 1:
            logger.info("Transcription busy, dropping this utterance")
            self._publish_state(self._get_idle_state())
            return

        # Start flash timer before transcription
        self._start_flash_timer()

        # Enqueue transcription request (non-blocking)
        self._transcription_queue.put((audio_data, self._current_language))

    def _process_transcription(self, audio_data: np.ndarray) -> None:
        """
        Legacy method kept for compatibility. Not used in queue-based design.
        Transcription is now handled by _transcription_worker_loop.
        """
        pass  # noqa: E501  — kept for API compatibility

    def _start_flash_timer(self) -> None:
        """Start background thread that flashes the icon during processing."""
        self._processing_flash_on = True
        self._flash_event.clear()
        self._publish_state(AppState.PROCESSING)

        def flash_loop() -> None:
            while not self._flash_event.is_set():
                self._processing_flash_on = not self._processing_flash_on
                self._update_tray_icon()
                self._flash_event.wait(0.5)  # 500ms interval

        self._flash_timer = threading.Thread(
            target=flash_loop,
            daemon=True,
            name="tray-processing-flash",
        )
        self._flash_timer.start()

    def _stop_flash_timer(self, next_snapshot: AppStateSnapshot | None = None) -> None:
        """Stop the flash timer."""
        self._flash_event.set()
        if self._flash_timer and self._flash_timer.is_alive():
            self._flash_timer.join(timeout=1.0)
        self._flash_timer = None
        self._processing_flash_on = False
        self._publish_snapshot(
            next_snapshot or self._build_snapshot(self._get_idle_state())
        )

    def _get_tray_title(self) -> str:
        """Return the current tray hover text for the active app state."""
        return self._state_presentation.tray_title

    def _update_tray_icon(self) -> None:
        """Update the tray icon image and hover text for the current state."""
        if not self._tray_icon_ref:
            return

        with self._tray_update_lock:
            try:
                self._tray_icon.update_icon_for_presentation(
                    self._tray_icon_ref,
                    self._state_presentation,
                    flash_on=self._processing_flash_on,
                )
                # pystray exposes the tray tooltip text via the `title` property.
                self._tray_icon_ref.title = self._get_tray_title()
            except Exception:
                logger.warning("Failed to update tray icon state", exc_info=True)

    def _refresh_tray_menu(self, icon: PystrayIcon) -> None:
        """Refresh dynamic tray menu checkmarks when pystray supports it."""
        update_menu = getattr(icon, "update_menu", None)
        if not callable(update_menu):
            return

        try:
            update_menu()
        except Exception:
            logger.debug("Failed to refresh tray menu", exc_info=True)

    def _notify_user(self, message: str) -> None:
        """Show a best-effort tray notification without breaking the app flow."""
        if not self._tray_icon_ref:
            return

        try:
            self._tray_icon_ref.notify(message)
        except Exception:
            logger.debug("Failed to send tray notification", exc_info=True)

    def _apply_overlay_settings(self, *, render_current_state: bool = True) -> bool:
        """Recreate the overlay controller for the current runtime settings."""
        self._overlay.close()
        runtime = getattr(self, "_tray_runtime", None)
        if runtime is None:
            runtime = PystrayTrayRuntime()
        self._overlay = runtime.create_overlay_controller(
            self.config.overlay.enabled,
            position=self.config.overlay.position,
            screen_target=self.config.overlay.screen,
        )

        if self.config.overlay.enabled and isinstance(
            self._overlay, NullOverlayController
        ):
            self.config.overlay.enabled = False
            return False

        if render_current_state and self.config.overlay.enabled:
            self._overlay.show_state(self._state_presentation)

        return self.config.overlay.enabled

    @staticmethod
    def _format_overlay_position(position: str) -> str:
        """Convert an overlay corner into a readable tray label."""
        return position.replace("-", " ").title()

    @staticmethod
    def _format_overlay_auto_hide(seconds: float) -> str:
        """Convert a ready-state timeout into a readable tray label."""
        if seconds <= 0:
            return "Stay Visible"
        if seconds.is_integer():
            unit = "Second" if seconds == 1 else "Seconds"
            return f"{int(seconds)} {unit}"
        return f"{seconds:g} Seconds"

    @staticmethod
    def _format_overlay_density(density: str) -> str:
        """Convert an overlay density into a readable tray label."""
        return density.title()

    @staticmethod
    def _format_overlay_screen(screen: str) -> str:
        """Convert an overlay screen target into a readable tray label."""
        labels = {
            "primary": "Primary Display",
            "cursor": "Cursor Display",
        }
        return labels.get(screen, screen.replace("-", " ").title())

    def _setup_hotkey_listener(self) -> None:
        """Set up the global hotkey listener."""
        self._hotkey_listener = HotkeyListener(
            hotkey=self.config.hotkey.hotkey,
            on_press=self._on_hotkey_pressed,
            on_release=self._on_hotkey_released,
        )

    def _prepare_tray_runtime(self) -> None:
        """
        Prepare the preferred tray runtime with a safe Qt-to-pystray fallback.

        When the shared Qt tray cannot boot, we keep the requested overlay
        configuration intact so the legacy pystray runtime can still attempt the
        threaded Qt overlay backend during `_apply_overlay_settings()`.
        """
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
            on_toggle_overlay=self._on_toggle_overlay,
            on_set_overlay_position=self._on_set_overlay_position,
            on_set_overlay_screen=self._on_set_overlay_screen,
            on_set_overlay_auto_hide=self._on_set_overlay_auto_hide,
            on_set_overlay_density=self._on_set_overlay_density,
            on_exit=self._on_exit,
            get_auto_paste_state=lambda: self._clipboard.auto_paste,
            get_language_state=lambda: self._current_language,
            get_overlay_enabled_state=lambda: self.config.overlay.enabled,
            get_overlay_position_state=lambda: self.config.overlay.position,
            get_overlay_screen_state=lambda: self.config.overlay.screen,
            get_overlay_auto_hide_state=lambda: self.config.overlay.auto_hide_seconds,
            get_overlay_density_state=lambda: self.config.overlay.density,
        )

    def _on_toggle_auto_paste(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle toggle auto-paste menu action."""
        new_state = self._clipboard.toggle_auto_paste()
        self._notify_user(f"Auto-paste {'enabled' if new_state else 'disabled'}")

    def _on_set_language_en(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle set language to English."""
        self._current_language = "en"
        self._notify_user("Language: English")

    def _on_set_language_ru(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle set language to Russian."""
        self._current_language = "ru"
        self._notify_user("Language: Russian")

    def _on_set_language_auto(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle set language to auto-detect."""
        self._current_language = "auto"
        self._notify_user("Language: Auto-detect")

    def _on_toggle_overlay(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle toggling the optional on-screen overlay."""
        requested_state = not self.config.overlay.enabled
        self.config.overlay.enabled = requested_state
        overlay_active = self._apply_overlay_settings()
        self._refresh_tray_menu(icon)

        if requested_state and overlay_active:
            self._notify_user(
                "Overlay enabled "
                f"({self._format_overlay_position(self.config.overlay.position)})"
            )
            return

        if requested_state:
            self._notify_user(OVERLAY_INSTALL_MESSAGE)
            return

        self._notify_user("Overlay disabled")

    def _on_set_overlay_position(
        self,
        position: str,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting a tray-managed overlay corner."""
        if position == self.config.overlay.position:
            return

        self.config.overlay.position = position
        overlay_was_enabled = self.config.overlay.enabled
        overlay_active = (
            self._apply_overlay_settings() if overlay_was_enabled else False
        )
        self._refresh_tray_menu(icon)

        if overlay_was_enabled and not overlay_active:
            self._notify_user(OVERLAY_INSTALL_MESSAGE)
            return

        self._notify_user(
            f"Overlay position: {self._format_overlay_position(position)}"
        )

    def _on_set_overlay_auto_hide(
        self,
        seconds: float,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting the ready-state overlay timeout."""
        if abs(seconds - self.config.overlay.auto_hide_seconds) < 1e-9:
            return

        self.config.overlay.auto_hide_seconds = seconds
        self._refresh_presentation_model()
        self._refresh_tray_menu(icon)
        self._notify_user(
            f"Overlay ready auto-hide: {self._format_overlay_auto_hide(seconds)}"
        )

    def _on_set_overlay_screen(
        self,
        screen: str,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting the overlay display target."""
        if screen == self.config.overlay.screen:
            return

        self.config.overlay.screen = screen
        overlay_was_enabled = self.config.overlay.enabled
        overlay_active = (
            self._apply_overlay_settings() if overlay_was_enabled else False
        )
        self._refresh_tray_menu(icon)

        if overlay_was_enabled and not overlay_active:
            self._notify_user(OVERLAY_INSTALL_MESSAGE)
            return

        self._notify_user(f"Overlay display: {self._format_overlay_screen(screen)}")

    def _on_set_overlay_density(
        self,
        density: str,
        icon: PystrayIcon,
        item: PystrayMenuItem,
    ) -> None:
        """Handle selecting the overlay presentation density."""
        if density == self.config.overlay.density:
            return

        self.config.overlay.density = density
        self._refresh_presentation_model()
        self._refresh_tray_menu(icon)
        self._notify_user(f"Overlay view: {self._format_overlay_density(density)}")

    def _on_exit(self, icon: PystrayIcon, item: PystrayMenuItem) -> None:
        """Handle exit menu action."""
        icon.stop()

    def _load_model_in_background(self) -> None:
        """Load the Whisper model in background thread."""
        self._transcriber.load_model()
        self._model_load_complete.set()
        if self._transcriber.is_ready:
            self._publish_state(AppState.READY)
        else:
            self._publish_state(AppState.ERROR, message="Model failed to load.")

    def run(self) -> None:
        """
        Main entry point. Starts the application and blocks until exit.

        The tray icon appears immediately; model loads asynchronously
        in the background so the user sees the app right away.
        """
        logger.info("Starting WhisperTray...")
        logger.info(f"Hotkey: {format_hotkey(self.config.hotkey.hotkey)}")
        logger.info(f"Auto-paste: {self.config.hotkey.auto_paste}")
        self._prepare_tray_runtime()

        overlay_requested = self.config.overlay.enabled
        overlay_active = self._apply_overlay_settings(render_current_state=True)
        if overlay_requested and not overlay_active:
            self._notify_user(OVERLAY_INSTALL_MESSAGE)

        # Start model loading in background thread (non-blocking)
        threading.Thread(
            target=self._load_model_in_background,
            daemon=True,
            name="model-loader",
        ).start()

        # Start the transcription worker thread
        self._start_worker()
        self._start_clipboard_monitor()

        # Set up hotkey listener
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
