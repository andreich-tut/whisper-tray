"""Compatibility facade for platform-aware default helpers."""

from whisper_tray.platform.defaults import (
    MODEL_PRESETS,
    ModelPreset,
    _apply_preset,
    default_compute_type,
    default_device,
    default_model_size,
    read_bool_env,
)

__all__ = [
    "MODEL_PRESETS",
    "ModelPreset",
    "_apply_preset",
    "default_compute_type",
    "default_device",
    "default_model_size",
    "read_bool_env",
]
