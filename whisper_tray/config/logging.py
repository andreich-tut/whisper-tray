"""Compatibility facade for backend-neutral config logging helpers."""

from whisper_tray.core.config.logging import apply_cpu_thread_limits, log_config

__all__ = [
    "apply_cpu_thread_limits",
    "log_config",
]
