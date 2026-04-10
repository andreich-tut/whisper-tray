"""Optional PyAutoGUI-based paste fallback."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send_pyautogui_shortcut(*keys: str) -> bool:
    """Fallback to PyAutoGUI when lower-level keyboard backends fail."""
    try:
        import pyautogui
    except Exception:
        return False

    try:
        pyautogui.hotkey(*keys)
    except Exception:
        logger.warning(
            "PyAutoGUI auto-paste via %s failed.",
            "+".join(keys),
            exc_info=True,
        )
        return False

    return True
