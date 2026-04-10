"""Tests for shared app-state presentation mapping."""

from whisper_tray.state import (
    AppState,
    AppStatePresenter,
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
        assert presentation.overlay_primary == "Hold Ctrl+Shift+Space to dictate."
        assert presentation.overlay_secondary is None
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

    def test_transcribed_state_shows_pasted_badge_and_transcript(self) -> None:
        """Successful auto-paste should surface the transcript as a persistent state."""
        presenter = AppStatePresenter()

        presentation = presenter.present(
            AppStateSnapshot(
                state=AppState.TRANSCRIBED,
                device="cpu",
                transcript=(
                    "This is a fairly long transcript that should wrap across "
                    "multiple overlay lines so we can verify truncation."
                ),
                auto_pasted=True,
            )
        )

        assert presentation.overlay_badge == "PASTED"
        assert (
            "\n" in presentation.overlay_primary
            or presentation.overlay_primary.endswith("...")
        )
        assert presentation.overlay_secondary == (
            "Pasted and still available in the clipboard."
        )
        assert presentation.overlay_hint == "Shown until clipboard changes"
        assert presentation.overlay_auto_hide_seconds is None
        assert presentation.icon_color == "lightgreen"

    def test_transcribed_state_uses_single_line_compact_copy(self) -> None:
        """Compact overlays should collapse transcript display to one line."""
        presenter = AppStatePresenter(overlay_density="compact")

        presentation = presenter.present(
            AppStateSnapshot(
                state=AppState.TRANSCRIBED,
                device="cpu",
                transcript=(
                    "This transcript should be compact enough to collapse into "
                    "a single line even when it needs truncation."
                ),
            )
        )

        assert presentation.overlay_badge == "COPIED"
        assert "\n" not in presentation.overlay_primary
        assert presentation.overlay_secondary is None
        assert presentation.overlay_hint is None

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


class TestFormatHotkey:
    """Test hotkey label formatting."""

    def test_orders_common_modifiers(self) -> None:
        """Modifier ordering should stay stable for overlay copy."""
        assert format_hotkey({"space", "shift", "ctrl"}) == "Ctrl+Shift+Space"
