"""Transcriber orchestration for faster-whisper."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

import numpy as np
from faster_whisper import WhisperModel

from whisper_tray.adapters.transcription.cuda import resolve_model_backend
from whisper_tray.adapters.transcription.fw_assets import ensure_faster_whisper_assets
from whisper_tray.adapters.transcription.model_load import load_whisper_model_with_retry
from whisper_tray.adapters.transcription.vad import (
    build_transcribe_kwargs,
    normalize_language,
    vad_onnx_available,
)
from whisper_tray.config import AudioConfig, ModelConfig

logger = logging.getLogger(__name__)


class _SegmentLike(Protocol):
    """Minimal transcribed-segment interface used by the result joiner."""

    text: str


def _join_segment_text(segments: Iterable[_SegmentLike]) -> str:
    """Join all transcribed segment text into a single normalized string."""
    return " ".join(segment.text for segment in segments).strip()


class Transcriber:
    """Manages the Whisper model and transcription."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        """Initialize the transcriber and cache runtime config."""
        self.config = config or ModelConfig()
        self._model: WhisperModel | None = None
        self._model_ready = False
        self._device = self.config.device
        self._audio_config = AudioConfig()
        self._vad_onnx_available: bool | None = None

    def ensure_faster_whisper_assets(self) -> None:
        """Ensure faster-whisper can find its ONNX model files."""
        self._vad_onnx_available = ensure_faster_whisper_assets()

    def _check_vad_availability(self) -> bool:
        """Return cached VAD ONNX availability."""
        if self._vad_onnx_available is None:
            self._vad_onnx_available = vad_onnx_available()
        return self._vad_onnx_available

    def load_model(self) -> None:
        """Load the Whisper model with CPU-first fallback behavior."""
        try:
            logger.info("Loading Whisper model (%s)...", self.config.model_size)
            device, compute_type = resolve_model_backend(
                self.config.device,
                self.config.compute_type,
            )
            if device == "cuda":
                logger.info(
                    "Loading model with CUDA (%s, %s)...",
                    self.config.device,
                    self.config.compute_type,
                )

            self._model = load_whisper_model_with_retry(
                self.config.model_size,
                device,
                compute_type,
            )
            self._device = device
            self._model_ready = True
            logger.info("Model loaded successfully (%s).", device)
            logger.info("Model ready (device: %s)", self._device)
            self.ensure_faster_whisper_assets()
        except Exception as exc:
            logger.error("Critical error loading model: %s", exc)
            self._model_ready = False

    @property
    def is_ready(self) -> bool:
        """Check if model is loaded and ready."""
        return self._model_ready and self._model is not None

    @property
    def device(self) -> str:
        """Get the device the model is running on."""
        return self._device

    def _transcription_too_short(self, audio_data: np.ndarray) -> bool:
        """Return whether the captured audio is shorter than the minimum duration."""
        duration = len(audio_data) / self._audio_config.sample_rate
        if duration >= self._audio_config.min_recording_duration:
            return False
        logger.info(
            "Recording too short: %.2fs < %ss",
            duration,
            self._audio_config.min_recording_duration,
        )
        return True

    def _cpu_fallback_transcribe(
        self,
        audio_data: np.ndarray,
        language: str | None,
    ) -> str | None:
        """Retry transcription on CPU after a CUDA runtime failure."""
        logger.info("Attempting to reload model with CPU...")
        try:
            self._model = WhisperModel(
                self.config.model_size,
                device="cpu",
                compute_type="int8",
            )
            self._device = "cpu"
            self._model_ready = True
            logger.info("Model reloaded with CPU mode. Retrying transcription...")
            segments, info = self._model.transcribe(
                audio_data,
                language=normalize_language(language),
                vad_filter=False,
            )
            result_text = _join_segment_text(segments)
            if result_text:
                logger.info("Transcription (CPU fallback): %s", result_text)
                return result_text
            logger.info("No speech detected")
            return None
        except Exception as retry_error:
            logger.error("CPU fallback also failed: %s", retry_error)
            return None

    def transcribe(
        self,
        audio_data: np.ndarray,
        language: str | None = None,
    ) -> str | None:
        """Transcribe audio data using faster-whisper."""
        if self._transcription_too_short(audio_data):
            return None
        if self._model is None:
            logger.error("Model not loaded")
            return None

        language_param = normalize_language(language)
        logger.info(
            "Transcription language config: %s -> param: %s",
            language,
            language_param,
        )

        try:
            vad_available = self._check_vad_availability()
            transcribe_kwargs = build_transcribe_kwargs(
                audio_config=self._audio_config,
                model_config=self.config,
                language=language,
                vad_available=vad_available,
            )
            segments, info = self._model.transcribe(audio_data, **transcribe_kwargs)
            result_text = _join_segment_text(segments)

            if not result_text:
                if vad_available:
                    logger.info("No speech detected (VAD filtered everything)")
                else:
                    logger.info("No speech detected")
                return None

            logger.info("Transcription (%s): %s", info.language, result_text)
            return result_text
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Transcription error: %s", error_msg)
            if (
                "dll is not found" in error_msg or "cublas" in error_msg.lower()
            ) and self._device != "cpu":
                logger.warning(
                    "CUDA DLL missing! This executable was built without CUDA DLLs.\n"
                    "Options:\n"
                    "  1. Rebuild with updated .spec file "
                    "(bundles CUDA DLLs automatically)\n"
                    "  2. Set DEVICE=cpu in environment to force CPU mode\n"
                    "  3. Install CUDA Toolkit and rebuild"
                )
                return self._cpu_fallback_transcribe(audio_data, language)
            return None
