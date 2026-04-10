"""Audio-related configuration values."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    """Configuration for audio recording."""

    sample_rate: int = field(
        default_factory=lambda: int(os.getenv("SAMPLE_RATE", "16000"))
    )
    min_recording_duration: float = field(
        default_factory=lambda: float(os.getenv("MIN_RECORDING_DURATION", "0.3"))
    )
    vad_threshold: float = field(
        default_factory=lambda: float(os.getenv("VAD_THRESHOLD", "0.5"))
    )
    vad_silence_duration_ms: int = field(
        default_factory=lambda: int(os.getenv("VAD_SILENCE_DURATION_MS", "500"))
    )
