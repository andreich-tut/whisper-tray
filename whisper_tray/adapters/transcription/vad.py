"""VAD helper adapter facade."""

from whisper_tray.audio.vad import (
    build_transcribe_kwargs,
    normalize_language,
    vad_onnx_available,
)

__all__ = [
    "build_transcribe_kwargs",
    "normalize_language",
    "vad_onnx_available",
]
