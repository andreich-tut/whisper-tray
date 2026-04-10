"""Environment discovery and dotenv loading helpers."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _env_candidate_paths() -> tuple[Path, ...]:
    """Return the supported `.env` lookup locations in priority order."""
    package_dir = Path(__file__).resolve().parents[1]
    project_dir = package_dir.parent
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve(strict=False)
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(path)

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        add(exe_dir / ".env")
        add(exe_dir.parent / ".env")
        add(exe_dir.parent.parent / ".env")
        add(exe_dir.parent.parent / "whisper_tray" / ".env")

    add(Path.cwd() / ".env")
    add(project_dir / ".env")
    add(package_dir / ".env")
    return tuple(candidates)


def _load_env_file() -> None:
    """Load the first matching `.env` file when python-dotenv is available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for candidate in _env_candidate_paths():
        if not candidate.is_file():
            continue
        if load_dotenv(candidate, override=False):
            logger.info("Loaded .env file from %s", candidate)
            return
