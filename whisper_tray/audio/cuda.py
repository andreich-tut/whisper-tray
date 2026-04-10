"""CUDA probing and runtime backend selection."""

from whisper_tray.adapters.transcription.cuda import (
    cuda_is_available,
    resolve_model_backend,
)

__all__ = ["cuda_is_available", "resolve_model_backend"]
