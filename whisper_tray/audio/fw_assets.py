"""Asset discovery and copy helpers for faster-whisper."""

from whisper_tray.adapters.transcription.fw_assets import (
    ensure_faster_whisper_assets,
    faster_whisper_package_dir,
)

__all__ = [
    "ensure_faster_whisper_assets",
    "faster_whisper_package_dir",
]
