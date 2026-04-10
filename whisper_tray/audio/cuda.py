"""CUDA probing and runtime backend selection."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def cuda_is_available() -> bool:
    """Check whether CUDA runtime libraries are available."""
    try:
        import ctypes

        if sys.platform == "win32":
            ctypes.CDLL("cublas64_12.dll")
            ctypes.CDLL("cudnn64_8.dll")
        else:
            ctypes.CDLL("libcublas.so.12")
            ctypes.CDLL("libcudnn.so.8")
        return True
    except Exception:
        return False


def resolve_model_backend(device: str, compute_type: str) -> tuple[str, str]:
    """Return the safe runtime backend for model loading."""
    if device != "cuda":
        return device, compute_type

    if cuda_is_available():
        return device, compute_type

    logger.info(
        "CUDA libraries not found on system. Falling back to CPU for model load."
    )
    return "cpu", "int8"
