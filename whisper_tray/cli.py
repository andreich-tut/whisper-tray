"""
CLI entry point for WhisperTray.

Provides the `whisper-tray` command when installed as a package.
"""

from __future__ import annotations

import logging
import sys

from whisper_tray.app import WhisperTrayApp
from whisper_tray.config import AppConfig

# Setup logging to file
logging.basicConfig(
    filename="whisper_tray.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the whisper-tray command."""
    logger.info("WhisperTray starting via CLI entry point")

    try:
        config = AppConfig.from_env()
        app = WhisperTrayApp(config)
        app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
