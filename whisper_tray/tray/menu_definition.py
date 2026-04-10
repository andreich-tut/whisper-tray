"""Shared tray menu definition used by all backends."""

from __future__ import annotations

from whisper_tray.tray.menu_callbacks import TrayMenuCallbacks
from whisper_tray.tray.menu_model import (
    OVERLAY_AUTO_HIDE_OPTIONS,
    OVERLAY_DENSITIES,
    OVERLAY_POSITIONS,
    OVERLAY_SCREENS,
    MenuEntry,
)
from whisper_tray.tray.menu_state import TrayMenuState


def build_menu_entries(
    *,
    callbacks: TrayMenuCallbacks,
    state: TrayMenuState,
) -> tuple[MenuEntry, ...]:
    """Build the shared tray menu structure for all supported backends."""
    return (
        MenuEntry(
            label="Language",
            children=(
                MenuEntry(
                    label="English",
                    action=callbacks.wrap(callbacks.on_set_language_en),
                    checked=lambda: state.language_checked("en"),
                    radio=True,
                ),
                MenuEntry(
                    label="Russian",
                    action=callbacks.wrap(callbacks.on_set_language_ru),
                    checked=lambda: state.language_checked("ru"),
                    radio=True,
                ),
                MenuEntry(
                    label="Auto-Detect",
                    action=callbacks.wrap(callbacks.on_set_language_auto),
                    checked=lambda: state.language_checked("auto"),
                    radio=True,
                ),
            ),
        ),
        MenuEntry(
            label="Toggle Auto-Paste",
            action=callbacks.wrap(callbacks.on_toggle_auto_paste),
            checked=state.get_auto_paste_state,
        ),
        MenuEntry(
            label="Overlay",
            children=(
                MenuEntry(
                    label="Enabled",
                    action=callbacks.wrap(callbacks.on_toggle_overlay),
                    checked=state.get_overlay_enabled_state,
                ),
                MenuEntry(
                    label="Position",
                    children=tuple(
                        MenuEntry(
                            label=label,
                            action=callbacks.wrap_overlay_position(position),
                            checked=state.overlay_position_checked_callback(position),
                            radio=True,
                        )
                        for position, label in OVERLAY_POSITIONS
                    ),
                ),
                MenuEntry(
                    label="Display",
                    children=tuple(
                        MenuEntry(
                            label=label,
                            action=callbacks.wrap_overlay_screen(screen),
                            checked=state.overlay_screen_checked_callback(screen),
                            radio=True,
                        )
                        for screen, label in OVERLAY_SCREENS
                    ),
                ),
                MenuEntry(
                    label="Ready Auto-Hide",
                    children=tuple(
                        MenuEntry(
                            label=label,
                            action=callbacks.wrap_overlay_auto_hide(seconds),
                            checked=state.overlay_auto_hide_checked_callback(seconds),
                            radio=True,
                        )
                        for seconds, label in OVERLAY_AUTO_HIDE_OPTIONS
                    ),
                ),
                MenuEntry(
                    label="View",
                    children=tuple(
                        MenuEntry(
                            label=label,
                            action=callbacks.wrap_overlay_density(density),
                            checked=state.overlay_density_checked_callback(density),
                            radio=True,
                        )
                        for density, label in OVERLAY_DENSITIES
                    ),
                ),
            ),
        ),
        MenuEntry(
            label="Exit",
            action=callbacks.wrap(callbacks.on_exit),
        ),
    )
