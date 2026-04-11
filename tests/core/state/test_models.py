"""Tests for state publisher fan-out behavior."""

from whisper_tray.state import AppState, AppStatePublisher, AppStateSnapshot


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

    def test_publish_snapshot_forwards_prebuilt_snapshot(self) -> None:
        """Prebuilt snapshots should be published without losing transcript fields."""
        initial = AppStateSnapshot(state=AppState.LOADING_MODEL, device="cpu")
        publisher = AppStatePublisher(initial)
        seen: list[AppStateSnapshot] = []

        publisher.subscribe(seen.append)
        publisher.publish_snapshot(
            AppStateSnapshot(
                state=AppState.TRANSCRIBED,
                device="cpu",
                transcript="hello world",
                auto_pasted=True,
            )
        )

        assert seen[-1] == AppStateSnapshot(
            state=AppState.TRANSCRIBED,
            device="cpu",
            transcript="hello world",
            auto_pasted=True,
        )
