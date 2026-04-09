"""
Transcription module.

Handles loading and running the Whisper model via faster-whisper.
CPU-first design: GPU is optional, detected upfront to avoid double-load.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import sys
import time
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from whisper_tray.config import AudioConfig, ModelConfig

logger = logging.getLogger(__name__)


def _cuda_is_available() -> bool:
    """Check if CUDA is actually available before attempting model load."""
    try:
        import ctypes

        # Try to load CUDA runtime libraries — fast check before model load
        if sys.platform == "win32":
            ctypes.CDLL("cublas64_12.dll")
            ctypes.CDLL("cudnn64_8.dll")
        else:
            ctypes.CDLL("libcublas.so.12")
            ctypes.CDLL("libcudnn.so.8")
        return True
    except Exception:
        return False


class Transcriber:
    """Manages the Whisper model and transcription."""

    def __init__(self, config: Optional[ModelConfig] = None) -> None:
        """
        Initialize transcriber.

        Args:
            config: Model configuration. Uses defaults if None.
        """
        self.config = config or ModelConfig()
        self._model: Optional[WhisperModel] = None
        self._model_ready = False
        self._device: str = self.config.device

        # Cache AudioConfig at init time (not re-created on every transcribe call)
        self._audio_config = AudioConfig()

        # Cache VAD ONNX availability check at init/model-load time
        self._vad_onnx_available: Optional[bool] = None

    def ensure_faster_whisper_assets(self) -> None:
        """
        Ensure faster-whisper can find its ONNX model files.

        When bundled with PyInstaller, data files may be extracted to
        different locations. This function verifies the ONNX file exists
        and attempts to locate it if missing.
        """
        try:
            # Find faster-whisper package location
            fw_spec = importlib.util.find_spec("faster_whisper")
            if not fw_spec or not fw_spec.origin:
                logger.warning("Could not find faster_whisper package location")
                return

            fw_dir = os.path.dirname(fw_spec.origin)
            assets_dir = os.path.join(fw_dir, "assets")
            onnx_file = os.path.join(assets_dir, "silero_vad_v6.onnx")

            # Check if ONNX file already exists (common when running as script)
            if os.path.exists(onnx_file):
                logger.info(f"ONNX file found at: {onnx_file}")
                self._vad_onnx_available = True
                return

            # File doesn't exist - only try to copy when bundled with PyInstaller
            if not getattr(sys, "frozen", False):
                logger.warning(
                    f"ONNX file not found at {onnx_file} and not running as bundled app"
                )
                self._vad_onnx_available = False
                return

            logger.info(
                f"ONNX file not found at {onnx_file}, attempting to locate it..."
            )

            # When bundled, PyInstaller extracts to _MEIPASS temp directory
            # Files are placed in faster_whisper/assets/ relative to _MEIPASS
            meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            exe_dir = os.path.dirname(sys.executable)

            # Search in multiple possible locations
            possible_sources = [
                # PyInstaller _MEIPASS location (most common)
                os.path.join(meipass, "faster_whisper", "assets"),
                # _internal folder structure (onedir mode)
                os.path.join(exe_dir, "_internal", "faster_whisper", "assets"),
                os.path.join(exe_dir, "faster_whisper", "assets"),
                # Alternative naming
                os.path.join(meipass, "faster_whisper_assets"),
                os.path.join(exe_dir, "_internal", "faster_whisper_assets"),
            ]

            # Create assets directory if needed
            os.makedirs(assets_dir, exist_ok=True)

            # Try to find and copy ONNX files from possible source locations
            for source_dir in possible_sources:
                source_onnx = os.path.join(source_dir, "silero_vad_v6.onnx")
                if os.path.exists(source_onnx):
                    shutil.copy2(source_onnx, onnx_file)
                    logger.info(f"Copied ONNX file from {source_dir} to {assets_dir}")
                    self._vad_onnx_available = True
                    return

            # Also try to find any .onnx files in source directories
            for source_dir in possible_sources:
                if os.path.exists(source_dir):
                    for f in os.listdir(source_dir):
                        if f.endswith(".onnx"):
                            dest_onnx = os.path.join(assets_dir, f)
                            shutil.copy2(os.path.join(source_dir, f), dest_onnx)
                            logger.info(f"Copied {f} from {source_dir} to {assets_dir}")
                            self._vad_onnx_available = True
                            return

            logger.warning(f"Could not find ONNX files. Checked: {possible_sources}")
            logger.warning(
                "VAD filter may not work. Consider reinstalling faster-whisper."
            )
            self._vad_onnx_available = False

        except Exception as e:
            logger.error(f"Error setting up faster-whisper assets: {e}")
            self._vad_onnx_available = False

    def _check_vad_availability(self) -> bool:
        """Return cached VAD ONNX availability."""
        if self._vad_onnx_available is None:
            # Lazy check if not already determined during model load
            fw_spec = importlib.util.find_spec("faster_whisper")
            if fw_spec and fw_spec.origin:
                fw_dir = os.path.dirname(fw_spec.origin)
                vad_onnx_path = os.path.join(fw_dir, "assets", "silero_vad_v6.onnx")
                self._vad_onnx_available = os.path.exists(vad_onnx_path)
            else:
                self._vad_onnx_available = False
        return self._vad_onnx_available

    def load_model(self) -> None:
        """
        Load the Whisper model.

        CPU-first design: only attempt CUDA when explicitly configured
        and CUDA libraries are actually available. Avoids double-load penalty.

        Includes retry logic with exponential backoff for HuggingFace rate limits (429).
        """
        try:
            logger.info(f"Loading Whisper model ({self.config.model_size})...")

            device = self.config.device
            compute_type = self.config.compute_type

            # If device is cuda, verify CUDA is actually available
            if device == "cuda":
                if not _cuda_is_available():
                    logger.info(
                        "CUDA libraries not found on system. "
                        "Falling back to CPU for model load."
                    )
                    device = "cpu"
                    compute_type = "int8"
                else:
                    logger.info(
                        f"Loading model with CUDA "
                        f"({self.config.device}, {self.config.compute_type})..."
                    )

            # Retry logic for HuggingFace rate limiting (429 Too Many Requests)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self._model = WhisperModel(
                        self.config.model_size,
                        device=device,
                        compute_type=compute_type,
                    )
                    break  # Success
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg and attempt < max_retries - 1:
                        wait_time = 2 ** (attempt + 1) * 5  # 10s, 20s, 40s
                        logger.warning(
                            "HuggingFace rate limited (429). "
                            f"Retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(wait_time)
                    else:
                        raise  # Non-429 error or final attempt

            self._device = device
            logger.info(f"Model loaded successfully ({device}).")

            self._model_ready = True
            logger.info(f"Model ready (device: {self._device})")

            # Ensure VAD assets are available (caches result)
            self.ensure_faster_whisper_assets()

        except Exception as e:
            logger.error(f"Critical error loading model: {e}")
            self._model_ready = False

    @property
    def is_ready(self) -> bool:
        """Check if model is loaded and ready."""
        return self._model_ready and self._model is not None

    @property
    def device(self) -> str:
        """Get the device the model is running on."""
        return self._device

    def transcribe(
        self, audio_data: np.ndarray, language: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio data using faster-whisper.

        Args:
            audio_data: Flat numpy array of audio samples (float32, 16kHz)
            language: Language code (e.g., 'en', 'ru') or None for auto-detect

        Returns:
            Transcribed text or None if failed/too short
        """
        # Use cached AudioConfig (not re-created on every call)
        duration = len(audio_data) / self._audio_config.sample_rate
        if duration < self._audio_config.min_recording_duration:
            logger.info(
                f"Recording too short: {duration:.2f}s < "
                f"{self._audio_config.min_recording_duration}s"
            )
            return None

        if self._model is None:
            logger.error("Model not loaded")
            return None

        # Determine language parameter
        language_param = language if language != "auto" else None
        logger.info(
            f"Transcription language config: {language} -> param: {language_param}"
        )

        try:
            # Use cached VAD availability check (not re-checked on every call)
            vad_available = self._check_vad_availability()

            # Build kwargs for transcribe call
            transcribe_kwargs: dict = {
                "language": language_param,
                "beam_size": self.config.beam_size,
                "condition_on_previous_text": self.config.condition_on_previous_text,
            }

            if vad_available:
                transcribe_kwargs["vad_filter"] = True
                transcribe_kwargs["vad_parameters"] = dict(
                    min_silence_duration_ms=self._audio_config.vad_silence_duration_ms,
                    threshold=self._audio_config.vad_threshold,
                )
            else:
                transcribe_kwargs["vad_filter"] = False

            segments, info = self._model.transcribe(audio_data, **transcribe_kwargs)

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            result_text = " ".join(text_parts).strip()

            if not result_text:
                if vad_available:
                    logger.info("No speech detected (VAD filtered everything)")
                else:
                    logger.info("No speech detected")
                return None

            logger.info(f"Transcription ({info.language}): {result_text}")
            return result_text

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Transcription error: {error_msg}")

            # Detect CUDA DLL missing error
            if "dll is not found" in error_msg or "cublas" in error_msg.lower():
                logger.warning(
                    "CUDA DLL missing! This executable was built without "
                    "CUDA DLLs.\n"
                    "Options:\n"
                    "  1. Rebuild with updated .spec file "
                    "(bundles CUDA DLLs automatically)\n"
                    "  2. Set DEVICE=cpu in environment to force CPU mode\n"
                    "  3. Install CUDA Toolkit and rebuild"
                )
                # Try to reload model with CPU
                if self._device != "cpu":
                    logger.info("Attempting to reload model with CPU...")
                    try:
                        self._model = WhisperModel(
                            self.config.model_size, device="cpu", compute_type="int8"
                        )
                        self._device = "cpu"
                        self._model_ready = True
                        logger.info(
                            "Model reloaded with CPU mode. Retrying transcription..."
                        )
                        # Retry transcription with CPU
                        segments, info = self._model.transcribe(
                            audio_data,
                            language=language_param,
                            vad_filter=False,
                        )
                        text_parts = []
                        for segment in segments:
                            text_parts.append(segment.text)
                        result_text = " ".join(text_parts).strip()
                        if result_text:
                            logger.info(f"Transcription (CPU fallback): {result_text}")
                            return result_text
                    except Exception as retry_error:
                        logger.error(f"CPU fallback also failed: {retry_error}")

            return None
