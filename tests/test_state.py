"""Tests for shared app state and presentation mapping."""

from whisper_tray.state import (
    AppState,
    AppStatePresenter,
    AppStatePublisher,
    AppStateSnapshot,
    describe_error,
    format_hotkey,
)


class TestAppStatePresenter:
    """Test mapping app states into UI presentation."""

    def test_ready_state_uses_hotkey_and_cpu_title(self) -> None:
        """Ready presentation should include the hotkey hint."""
        presenter = AppStatePresenter(hotkey_label="Ctrl+Shift+Space")

        presentation = presenter.present(
            AppStateSnapshot(state=AppState.READY, device="cpu")
        )

        assert presentation.tray_title == "WhisperTray (CPU mode) - Ready"
        assert presentation.overlay_badge == "Ready"
        assert presentation.overlay_primary == "Ready"
        assert presentation.overlay_secondary == "Hold Ctrl+Shift+Space to dictate."
        assert (
            presentation.overlay_hint == "Release the hotkey to transcribe and paste."
        )
        assert presentation.overlay_auto_hide_seconds == 1.5
        assert presentation.overlay_density == "detailed"

    def test_ready_state_with_compact_density_hides_secondary(self) -> None:
        """Compact overlay mode should trim non-essential secondary copy."""
        presenter = AppStatePresenter(
            hotkey_label="Ctrl+Shift+Space",
            overlay_density="compact",
        )

        presentation = presenter.present(
            AppStateSnapshot(state=AppState.READY, device="cpu")
        )

        assert presentation.overlay_secondary is None
        assert presentation.overlay_hint is None
        assert presentation.overlay_density == "compact"

    def test_ready_state_can_disable_auto_hide(self) -> None:
        """A zero ready timeout should keep the overlay visible."""
        presenter = AppStatePresenter(ready_auto_hide_seconds=0)

        presentation = presenter.present(
            AppStateSnapshot(state=AppState.READY, device="cpu")
        )

        assert presentation.overlay_auto_hide_seconds is None

    def test_processing_state_requests_flash(self) -> None:
        """Processing should mark the tray icon as flashable."""
        presenter = AppStatePresenter()

        presentation = presenter.present(
            AppStateSnapshot(state=AppState.PROCESSING, device="cpu")
        )

        assert presentation.tray_title == "Processing..."
        assert presentation.overlay_badge == "Processing"
        assert (
            presentation.overlay_hint
            == "Typing stays unblocked while the worker finishes."
        )
        assert presentation.flash_processing is True
        assert presentation.icon_color == "orange"

    def test_error_state_surfaces_message(self) -> None:
        """Error messages should be visible in the presentation."""
        presenter = AppStatePresenter(overlay_density="compact")

        presentation = presenter.present(
            AppStateSnapshot(
                state=AppState.ERROR,
                device="cpu",
                message="Model failed to load.",
            )
        )

        assert presentation.tray_title == "Error: Model failed to load."
        assert presentation.overlay_badge == "Error"
        assert presentation.overlay_primary == "Model unavailable"
        assert presentation.overlay_secondary == "Model failed to load."
        assert presentation.overlay_hint == (
            "Try a smaller model, switch to CPU, or restart WhisperTray."
        )

    def test_describe_error_handles_recording_failures(self) -> None:
        """Recording errors should surface microphone-specific recovery guidance."""
        error = describe_error(
            "Recording failed. Try closing apps or using DEVICE=cpu."
        )

        assert error.primary == "Microphone unavailable"
        assert error.hint == (
            "Close other audio apps, reconnect the mic, or try DEVICE=cpu."
        )


class TestAppStatePublisher:
    """Test publisher fan-out behavior."""

    def test_subscribe_emits_current_and_future_snapshots(self) -> None:
        """Listeners should receive the initial snapshot and later updates."""
        initial = AppStateSnapshot(state=AppState.LOADING_MODEL, device="cpu")
        publisher = AppStatePublisher(initial)
        seen: list[AppStateSnapshot] = []

        publisher.subscribe(seen.append)
        publisher.publish(AppState.READY, device="cpu")

        assert seen == [
            AppStateSnapshot(state=AppState.LOADING_MODEL, device="cpu"),
            AppStateSnapshot(state=AppState.READY, device="cpu"),
        ]


class TestFormatHotkey:
    """Test hotkey label formatting."""

    def test_orders_common_modifiers(self) -> None:
        """Modifier ordering should stay stable for overlay copy."""
        assert format_hotkey({"space", "shift", "ctrl"}) == "Ctrl+Shift+Space"
