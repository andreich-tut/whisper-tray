"""Bundled faster-whisper asset adapter facade."""

from whisper_tray.audio.fw_assets import (
    ensure_faster_whisper_assets,
    faster_whisper_package_dir,
)

__all__ = [
    "ensure_faster_whisper_assets",
    "faster_whisper_package_dir",
]
