"""VAD availability and transcribe-kwargs helpers."""

from __future__ import annotations

import os

from whisper_tray.adapters.transcription.fw_assets import faster_whisper_package_dir
from whisper_tray.config import AudioConfig, ModelConfig


def vad_onnx_available() -> bool:
    """Return whether the faster-whisper VAD ONNX asset is available."""
    package_dir = faster_whisper_package_dir()
    if package_dir is None:
        return False
    return os.path.exists(os.path.join(package_dir, "assets", "silero_vad_v6.onnx"))


def normalize_language(language: str | None) -> str | None:
    """Normalize auto-detect language selection for faster-whisper."""
    if language == "auto":
        return None
    return language


def build_transcribe_kwargs(
    *,
    audio_config: AudioConfig,
    model_config: ModelConfig,
    language: str | None,
    vad_available: bool,
) -> dict[str, object]:
    """Build stable kwargs for `WhisperModel.transcribe()`."""
    kwargs: dict[str, object] = {
        "language": normalize_language(language),
        "beam_size": model_config.beam_size,
        "condition_on_previous_text": model_config.condition_on_previous_text,
    }

    if vad_available:
        kwargs["vad_filter"] = True
        kwargs["vad_parameters"] = {
            "min_silence_duration_ms": audio_config.vad_silence_duration_ms,
            "threshold": audio_config.vad_threshold,
        }
        return kwargs

    kwargs["vad_filter"] = False
    return kwargs
