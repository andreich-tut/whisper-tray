"""Whisper model loading helpers."""

from __future__ import annotations

import logging
import time

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def load_whisper_model_with_retry(
    model_size: str,
    device: str,
    compute_type: str,
) -> WhisperModel:
    """Load a Whisper model with bounded retries for remote rate limits."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
        except Exception as exc:
            error_msg = str(exc)
            if "429" not in error_msg or attempt >= max_retries - 1:
                raise
            wait_time = 2 ** (attempt + 1) * 5
            logger.warning(
                "HuggingFace rate limited (429). Retrying in %ss (attempt %s/%s)...",
                wait_time,
                attempt + 1,
                max_retries,
            )
            time.sleep(wait_time)

    raise RuntimeError("Whisper model load exhausted retries unexpectedly")
