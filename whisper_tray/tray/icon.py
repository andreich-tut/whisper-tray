"""
Tray icon management module.

Handles creating and updating the system tray icon.
"""

from __future__ import annotations

import logging
from typing import Optional

from PIL import Image, ImageDraw

from whisper_tray.types import TrayIcon as PystrayIcon

logger = logging.getLogger(__name__)


class TrayIcon:
    """Manages the system tray icon appearance."""

    def __init__(self) -> None:
        """Initialize tray icon manager."""
        self._icon: Optional[PystrayIcon] = None

    @staticmethod
    def create_icon_image(color: str, size: int = 64) -> Image.Image:
        """
        Create a circular icon with specified color.

        Args:
            color: Color name (e.g., "gray", "red")
            size: Icon size in pixels

        Returns:
            PIL Image with circular icon
        """
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw circle
        margin = 4
        draw.ellipse([margin, margin, size - margin, size - margin], fill=color)

        # Add border
        draw.ellipse(
            [margin, margin, size - margin, size - margin], outline="white", width=2
        )

        return image

    @staticmethod
    def get_icon_image(is_recording: bool, model_ready: bool) -> Image.Image:
        """
        Get current icon image based on state.

        Args:
            is_recording: Whether currently recording audio
            model_ready: Whether the model is loaded and ready

        Returns:
            PIL Image with appropriate icon
        """
        if is_recording:
            return TrayIcon.create_icon_image("tomato")
        elif not model_ready:
            return TrayIcon.create_icon_image("yellow")
        else:
            return TrayIcon.create_icon_image("lightgreen")

    def update_icon(
        self, icon: PystrayIcon, is_recording: bool, model_ready: bool
    ) -> None:
        """
        Update the tray icon to reflect current state.

        Args:
            icon: The pystray Icon instance
            is_recording: Whether currently recording audio
            model_ready: Whether the model is loaded and ready
        """
        if icon is not None:
            try:
                icon.icon = self.get_icon_image(is_recording, model_ready)
            except Exception as e:
                logger.info(f"Error updating icon: {e}")

    @staticmethod
    def get_tooltip(is_recording: bool, model_ready: bool, device: str) -> str:
        """
        Get current tooltip text.

        Args:
            is_recording: Whether currently recording audio
            model_ready: Whether the model is loaded and ready
            device: Device the model is running on ('cuda' or 'cpu')

        Returns:
            Tooltip text string
        """
        if not model_ready:
            return "Loading model..."
        elif is_recording:
            return "Recording..."
        elif device == "cpu":
            return "WhisperTray (CPU mode) - Ready"
        else:
            return "WhisperTray (GPU mode) - Ready"
