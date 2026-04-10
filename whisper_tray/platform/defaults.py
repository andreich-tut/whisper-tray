"""Platform-aware defaults and shared configuration helpers."""

from __future__ import annotations

import os
import platform
from typing import Literal

ModelPreset = Literal["fast", "balanced", "accurate"]

MODEL_PRESETS: dict[ModelPreset, dict[str, str]] = {
    "fast": {
        "model_size": "base",
        "device": "cpu",
        "compute_type": "int8",
    },
    "balanced": {
        "model_size": "small",
        "device": "cpu",
        "compute_type": "int8",
    },
    "accurate": {
        "model_size": "medium",
        "device": "cpu",
        "compute_type": "int8",
    },
}

_TRUE_ENV_VALUES = {"true", "1", "yes", "on"}


def read_bool_env(name: str, *, default: bool = False) -> bool:
    """Parse a boolean environment variable with repo-standard truthy values."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in _TRUE_ENV_VALUES


def default_device() -> str:
    """Return the default inference device for the current platform."""
    if platform.system() == "Darwin":
        return "cpu"
    return os.getenv("DEVICE", "cpu")


def default_compute_type() -> str:
    """Return the default compute type for the selected device."""
    if default_device() == "cuda":
        return "float16"
    return "int8"


def default_model_size() -> str:
    """Return the default model size for CPU-first usage."""
    return os.getenv("MODEL_SIZE", "small")


def _apply_preset(preset_name: str) -> dict[str, str]:
    """Return preset values, or an empty mapping for unknown presets."""
    if preset_name in ("fast", "balanced", "accurate"):
        return MODEL_PRESETS[preset_name]  # type: ignore[index]
    return {}
