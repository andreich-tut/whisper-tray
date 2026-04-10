"""Compatibility facade for backend-neutral error presentation."""

from whisper_tray.core.presentation.errors import ErrorPresentation, describe_error

__all__ = [
    "ErrorPresentation",
    "describe_error",
]
