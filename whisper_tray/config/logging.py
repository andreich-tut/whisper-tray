"""Configuration-side logging helpers."""

from __future__ import annotations

import logging
import os

from whisper_tray.config.audio import AudioConfig
from whisper_tray.config.hotkey import HotkeyConfig
from whisper_tray.config.model import ModelConfig
from whisper_tray.config.overlay import OverlayConfig
from whisper_tray.config.ui import UiConfig

logger = logging.getLogger(__name__)


def apply_cpu_thread_limits() -> None:
    """Apply optional CPU thread limits before ONNX Runtime initializes."""
    cpu_threads = os.getenv("CPU_THREADS")
    if cpu_threads is None:
        return
    os.environ["OMP_NUM_THREADS"] = cpu_threads
    os.environ["ONNX_NUM_THREADS"] = cpu_threads


def log_config(
    *,
    model: ModelConfig,
    hotkey: HotkeyConfig,
    audio: AudioConfig,
    overlay: OverlayConfig,
    ui: UiConfig,
) -> None:
    """Log the current configuration in a stable, user-debuggable form."""
    logger.info(
        "Model config: size=%s, device=%s, compute=%s, language=%s",
        model.model_size,
        model.device,
        model.compute_type,
        model.language,
    )
    logger.info("Hotkey: %s", "+".join(sorted(hotkey.hotkey)))
    logger.info(
        "Auto-paste: %s, delay: %ss",
        hotkey.auto_paste,
        hotkey.paste_delay,
    )
    logger.info(
        "Audio: %sHz, min duration: %ss",
        audio.sample_rate,
        audio.min_recording_duration,
    )
    logger.info(
        "Overlay: enabled=%s, position=%s, screen=%s, auto-hide=%ss, density=%s",
        overlay.enabled,
        overlay.position,
        overlay.screen,
        overlay.auto_hide_seconds,
        overlay.density,
    )
    logger.info("UI: tray-backend=%s", ui.tray_backend)
