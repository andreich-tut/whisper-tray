"""Error presentation helpers for user-facing app state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorPresentation:
    """Actionable copy used by the overlay for error states."""

    primary: str
    detail: str
    hint: str


def describe_error(message: str | None) -> ErrorPresentation:
    """Convert a raw runtime error into user-facing recovery copy."""
    detail = (message or "").strip() or "Check whisper_tray.log for details."
    lowered = detail.lower()

    if (
        "model failed" in lowered
        or "load model" in lowered
        or ("model" in lowered and "load" in lowered)
    ):
        return ErrorPresentation(
            primary="Model unavailable",
            detail=detail,
            hint="Try a smaller model, switch to CPU, or restart WhisperTray.",
        )

    if (
        "recording failed" in lowered
        or "microphone" in lowered
        or "host error" in lowered
        or "audio" in lowered
    ):
        return ErrorPresentation(
            primary="Microphone unavailable",
            detail=detail,
            hint="Close other audio apps, reconnect the mic, or try DEVICE=cpu.",
        )

    if "transcription" in lowered:
        return ErrorPresentation(
            primary="Transcription failed",
            detail=detail,
            hint="Try dictating again. If it keeps happening, check whisper_tray.log.",
        )

    return ErrorPresentation(
        primary="Something went wrong",
        detail=detail,
        hint="Try again. If the error persists, check whisper_tray.log.",
    )
