"""Tests for transcriber orchestration and helper seams."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

import whisper_tray.adapters.transcription.cuda as cuda_module
import whisper_tray.adapters.transcription.transcriber as transcriber_module
from whisper_tray.audio.transcriber import Transcriber
from whisper_tray.audio.vad import build_transcribe_kwargs
from whisper_tray.config import AudioConfig, ModelConfig


class TestCudaHelpers:
    """Test CUDA backend selection helpers."""

    def test_resolve_model_backend_falls_back_to_cpu_when_cuda_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CUDA requests should degrade to CPU when runtime libraries are missing."""
        monkeypatch.setattr(cuda_module, "cuda_is_available", lambda: False)

        device, compute_type = cuda_module.resolve_model_backend("cuda", "float16")

        assert device == "cpu"
        assert compute_type == "int8"


class TestVadHelpers:
    """Test VAD kwarg construction."""

    def test_build_transcribe_kwargs_enables_vad_parameters(self) -> None:
        """VAD-enabled transcribes should include the configured thresholds."""
        kwargs = build_transcribe_kwargs(
            audio_config=AudioConfig(
                vad_threshold=0.7,
                vad_silence_duration_ms=300,
            ),
            model_config=ModelConfig(
                beam_size=2,
                condition_on_previous_text=True,
            ),
            language="en",
            vad_available=True,
        )

        assert kwargs["language"] == "en"
        assert kwargs["beam_size"] == 2
        assert kwargs["condition_on_previous_text"] is True
        assert kwargs["vad_filter"] is True
        assert kwargs["vad_parameters"] == {
            "min_silence_duration_ms": 300,
            "threshold": 0.7,
        }


class TestTranscriber:
    """Test transcriber behavior without loading a real model."""

    def test_load_model_uses_resolved_backend_and_caches_assets(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Model loading should honor the resolved backend and cache VAD assets."""
        loaded_model = object()
        load_model = MagicMock(return_value=loaded_model)

        monkeypatch.setattr(
            transcriber_module,
            "resolve_model_backend",
            lambda device, compute_type: ("cpu", "int8"),
        )
        monkeypatch.setattr(
            transcriber_module,
            "load_whisper_model_with_retry",
            load_model,
        )
        monkeypatch.setattr(
            transcriber_module,
            "ensure_faster_whisper_assets",
            lambda: True,
        )

        transcriber = Transcriber(
            ModelConfig(model_size="small", device="cuda", compute_type="float16")
        )
        transcriber.load_model()

        load_model.assert_called_once_with("small", "cpu", "int8")
        assert transcriber.device == "cpu"
        assert transcriber.is_ready is True
        assert transcriber._vad_onnx_available is True

    def test_transcribe_returns_none_for_short_audio(self) -> None:
        """Short recordings should be ignored before the model is called."""
        transcriber = Transcriber()
        transcriber._audio_config = AudioConfig(
            sample_rate=16000,
            min_recording_duration=1.0,
        )
        transcriber._model = MagicMock()

        result = transcriber.transcribe(np.ones(1000, dtype=np.float32))

        assert result is None
        transcriber._model.transcribe.assert_not_called()

    def test_transcribe_uses_vad_kwargs_and_collects_segments(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Transcribe should pass VAD kwargs through and join segment text."""
        model = MagicMock()
        model.transcribe.return_value = (
            [
                SimpleNamespace(text="hello"),
                SimpleNamespace(text="world"),
            ],
            SimpleNamespace(language="en"),
        )

        transcriber = Transcriber(ModelConfig(beam_size=2))
        transcriber._audio_config = AudioConfig(
            sample_rate=16000,
            min_recording_duration=0.1,
            vad_threshold=0.7,
            vad_silence_duration_ms=300,
        )
        transcriber._model = model
        monkeypatch.setattr(transcriber, "_check_vad_availability", lambda: True)

        result = transcriber.transcribe(
            np.ones(16000, dtype=np.float32),
            language="en",
        )

        assert result == "hello world"
        kwargs = model.transcribe.call_args.kwargs
        assert kwargs["language"] == "en"
        assert kwargs["beam_size"] == 2
        assert kwargs["vad_filter"] is True
        assert kwargs["vad_parameters"] == {
            "min_silence_duration_ms": 300,
            "threshold": 0.7,
        }

    def test_transcribe_retries_with_cpu_after_cuda_dll_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CUDA DLL failures should trigger the CPU fallback retry path."""
        initial_model = MagicMock()
        initial_model.transcribe.side_effect = RuntimeError("cublas dll is not found")
        fallback_model = MagicMock()
        fallback_model.transcribe.return_value = (
            [SimpleNamespace(text="cpu fallback")],
            SimpleNamespace(language="en"),
        )
        whisper_model = MagicMock(return_value=fallback_model)

        monkeypatch.setattr(transcriber_module, "WhisperModel", whisper_model)

        transcriber = Transcriber(ModelConfig(model_size="small"))
        transcriber._audio_config = AudioConfig(
            sample_rate=16000,
            min_recording_duration=0.1,
        )
        transcriber._model = initial_model
        transcriber._device = "cuda"
        transcriber._model_ready = True
        monkeypatch.setattr(transcriber, "_check_vad_availability", lambda: False)

        result = transcriber.transcribe(
            np.ones(16000, dtype=np.float32),
            language="auto",
        )

        whisper_model.assert_called_once_with(
            "small",
            device="cpu",
            compute_type="int8",
        )
        fallback_model.transcribe.assert_called_once_with(
            pytest.approx(np.ones(16000, dtype=np.float32)),
            language=None,
            vad_filter=False,
        )
        assert transcriber.device == "cpu"
        assert result == "cpu fallback"
