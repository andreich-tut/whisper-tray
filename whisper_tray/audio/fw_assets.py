"""Asset discovery and copy helpers for faster-whisper."""

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import sys

logger = logging.getLogger(__name__)

_VAD_ONNX_FILENAME = "silero_vad_v6.onnx"


def faster_whisper_package_dir() -> str | None:
    """Return the installed faster-whisper package directory, if available."""
    fw_spec = importlib.util.find_spec("faster_whisper")
    if not fw_spec or not fw_spec.origin:
        return None
    return os.path.dirname(fw_spec.origin)


def _possible_asset_sources(*, exe_dir: str, meipass: str) -> tuple[str, ...]:
    """Return the bundled locations that may contain faster-whisper assets."""
    return (
        os.path.join(meipass, "faster_whisper", "assets"),
        os.path.join(exe_dir, "_internal", "faster_whisper", "assets"),
        os.path.join(exe_dir, "faster_whisper", "assets"),
        os.path.join(meipass, "faster_whisper_assets"),
        os.path.join(exe_dir, "_internal", "faster_whisper_assets"),
    )


def _copy_named_onnx_asset(source_dirs: tuple[str, ...], destination: str) -> bool:
    """Copy the canonical Silero VAD asset when it exists."""
    for source_dir in source_dirs:
        source_onnx = os.path.join(source_dir, _VAD_ONNX_FILENAME)
        if not os.path.exists(source_onnx):
            continue
        shutil.copy2(source_onnx, destination)
        logger.info(
            "Copied ONNX file from %s to %s", source_dir, os.path.dirname(destination)
        )
        return True
    return False


def _copy_first_onnx_asset(source_dirs: tuple[str, ...], assets_dir: str) -> bool:
    """Copy the first available ONNX asset when the canonical name is absent."""
    for source_dir in source_dirs:
        if not os.path.exists(source_dir):
            continue
        for filename in os.listdir(source_dir):
            if not filename.endswith(".onnx"):
                continue
            destination = os.path.join(assets_dir, filename)
            shutil.copy2(os.path.join(source_dir, filename), destination)
            logger.info("Copied %s from %s to %s", filename, source_dir, assets_dir)
            return True
    return False


def ensure_faster_whisper_assets() -> bool:
    """Ensure faster-whisper can find its bundled VAD assets."""
    try:
        package_dir = faster_whisper_package_dir()
        if package_dir is None:
            logger.warning("Could not find faster_whisper package location")
            return False

        assets_dir = os.path.join(package_dir, "assets")
        onnx_file = os.path.join(assets_dir, _VAD_ONNX_FILENAME)
        if os.path.exists(onnx_file):
            logger.info("ONNX file found at: %s", onnx_file)
            return True

        if not getattr(sys, "frozen", False):
            logger.warning(
                "ONNX file not found at %s and not running as bundled app",
                onnx_file,
            )
            return False

        logger.info("ONNX file not found at %s, attempting to locate it...", onnx_file)
        meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        exe_dir = os.path.dirname(sys.executable)
        source_dirs = _possible_asset_sources(exe_dir=exe_dir, meipass=meipass)
        os.makedirs(assets_dir, exist_ok=True)

        if _copy_named_onnx_asset(source_dirs, onnx_file):
            return True
        if _copy_first_onnx_asset(source_dirs, assets_dir):
            return True

        logger.warning("Could not find ONNX files. Checked: %s", list(source_dirs))
        logger.warning("VAD filter may not work. Consider reinstalling faster-whisper.")
        return False
    except Exception as exc:
        logger.error("Error setting up faster-whisper assets: %s", exc)
        return False
