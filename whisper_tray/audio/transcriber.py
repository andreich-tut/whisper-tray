"""
Transcription module.

Handles loading and running the Whisper model via faster-whisper.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import sys
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from whisper_tray.config import ModelConfig

logger = logging.getLogger(__name__)


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
                return

            # File doesn't exist - only try to copy when bundled with PyInstaller
            if not getattr(sys, "frozen", False):
                logger.warning(
                    f"ONNX file not found at {onnx_file} and not running as bundled app"
                )
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
                    return

            # Also try to find any .onnx files in source directories
            for source_dir in possible_sources:
                if os.path.exists(source_dir):
                    for f in os.listdir(source_dir):
                        if f.endswith(".onnx"):
                            dest_onnx = os.path.join(assets_dir, f)
                            shutil.copy2(os.path.join(source_dir, f), dest_onnx)
                            logger.info(f"Copied {f} from {source_dir} to {assets_dir}")
                            return

            logger.warning(f"Could not find ONNX files. Checked: {possible_sources}")
            logger.warning(
                "VAD filter may not work. Consider reinstalling faster-whisper."
            )

        except Exception as e:
            logger.error(f"Error setting up faster-whisper assets: {e}")

    def load_model(self) -> None:
        """Load the Whisper model. Tries CUDA first, falls back to CPU."""
        try:
            logger.info(f"Loading Whisper model ({self.config.model_size})...")

            # Try CUDA first
            try:
                logger.info(
                    f"Loading model with CUDA ({self.config.device}, "
                    f"{self.config.compute_type})..."
                )
                self._model = WhisperModel(
                    self.config.model_size,
                    device=self.config.device,
                    compute_type=self.config.compute_type,
                )
                self._device = self.config.device
                logger.info("Model loaded successfully with CUDA.")
            except Exception as e:
                logger.info(f"CUDA failed: {e}, falling back to CPU...")
                self._model = WhisperModel(
                    self.config.model_size, device="cpu", compute_type="int8"
                )
                self._device = "cpu"
                logger.info("Model loaded successfully with CPU.")

            self._model_ready = True
            logger.info(f"Model ready (device: {self._device})")

            # Ensure VAD assets are available
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
        from whisper_tray.config import AudioConfig

        audio_config = AudioConfig()

        # Check duration
        duration = len(audio_data) / audio_config.sample_rate
        if duration < audio_config.min_recording_duration:
            logger.info(
                f"Recording too short: {duration:.2f}s < "
                f"{audio_config.min_recording_duration}s"
            )
            return None

        if self._model is None:
            logger.error("Model not loaded")
            return None

        # Determine language parameter
        language_param = language if language != "auto" else None

        try:
            # Check if VAD ONNX file exists
            fw_spec = importlib.util.find_spec("faster_whisper")
            vad_onnx_exists = False
            if fw_spec and fw_spec.origin:
                fw_dir = os.path.dirname(fw_spec.origin)
                vad_onnx_path = os.path.join(fw_dir, "assets", "silero_vad_v6.onnx")
                vad_onnx_exists = os.path.exists(vad_onnx_path)

            # Use VAD if available, otherwise fall back to no VAD
            if vad_onnx_exists:
                # Transcribe with VAD filter
                segments, info = self._model.transcribe(
                    audio_data,
                    language=language_param,
                    vad_filter=True,
                    vad_parameters=dict(
                        min_silence_duration_ms=audio_config.vad_silence_duration_ms,
                        threshold=audio_config.vad_threshold,
                    ),
                )
            else:
                # Fallback: transcribe without VAD
                logger.warning(
                    "VAD ONNX file not found, transcribing without VAD filter"
                )
                segments, info = self._model.transcribe(
                    audio_data,
                    language=language_param,
                    vad_filter=False,
                )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            result_text = " ".join(text_parts).strip()

            if not result_text:
                if vad_onnx_exists:
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
