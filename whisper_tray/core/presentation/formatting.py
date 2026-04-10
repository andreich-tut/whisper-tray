"""Formatting helpers for state presentation copy."""

from __future__ import annotations

import textwrap
from typing import Sequence


def format_hotkey(hotkey: Sequence[str] | set[str]) -> str:
    """Convert a hotkey set into a stable, user-facing label."""
    display_names = {
        "alt": "Alt",
        "cmd": "Cmd",
        "command": "Cmd",
        "ctrl": "Ctrl",
        "shift": "Shift",
        "space": "Space",
        "super": "Super",
        "win": "Win",
    }
    priority = {
        "ctrl": 0,
        "shift": 1,
        "alt": 2,
        "cmd": 3,
        "command": 3,
        "super": 4,
        "win": 4,
        "space": 5,
    }

    ordered = sorted(
        hotkey,
        key=lambda key: (priority.get(key, 100), display_names.get(key, key.title())),
    )
    return "+".join(display_names.get(key, key.title()) for key in ordered)


def truncate_line(text: str, max_chars: int) -> str:
    """Clamp a single line of overlay copy to a stable maximum width."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def format_transcript(transcript: str | None, *, density: str) -> str:
    """Format recognized text for the selected overlay density."""
    normalized = " ".join((transcript or "").split())
    if not normalized:
        return "Transcript ready"

    if density == "compact":
        return truncate_line(normalized, max_chars=56)

    wrapped = textwrap.wrap(normalized, width=42, break_long_words=False)
    if len(wrapped) <= 3:
        return "\n".join(wrapped)

    visible_lines = wrapped[:3]
    visible_lines[-1] = truncate_line(visible_lines[-1], max_chars=39)
    if not visible_lines[-1].endswith("..."):
        visible_lines[-1] = visible_lines[-1].rstrip() + "..."
    return "\n".join(visible_lines)
