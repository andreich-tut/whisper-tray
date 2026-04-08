"""
WhisperTray - Global speech-to-text system tray application.

DEPRECATED: This file has been refactored into modules.
Use `python -m whisper_tray` or `whisper-tray` command instead.

This file is kept for backward compatibility only.
"""
# pylint: disable=wrong-import-position
import warnings

warnings.warn(
    "This module is deprecated. Use 'python -m whisper_tray' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from whisper_tray.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
