"""CUDA backend-selection adapter facade."""

from whisper_tray.audio.cuda import cuda_is_available, resolve_model_backend

__all__ = [
    "cuda_is_available",
    "resolve_model_backend",
]
