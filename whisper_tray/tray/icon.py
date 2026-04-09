"""
Tray icon management module.

Handles creating and updating the system tray icon.
"""

from __future__ import annotations

import logging
from typing import Optional

from PIL import Image, ImageDraw

from whisper_tray.state import AppState, AppStatePresentation
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
    def get_icon_image(
        is_recording: bool, model_ready: bool, is_processing: bool = False
    ) -> Image.Image:
        """
        Get current icon image based on state.

        Args:
            is_recording: Whether currently recording audio
            model_ready: Whether the model is loaded and ready
            is_processing: Whether audio is being processed/transcribed

        Returns:
            PIL Image with appropriate icon
        """
        if is_recording:
            return TrayIcon.create_icon_image("tomato")
        elif not model_ready:
            return TrayIcon.create_icon_image("yellow")
        elif is_processing:
            return TrayIcon.create_icon_image("orange")
        else:
            return TrayIcon.create_icon_image("lightgreen")

    @staticmethod
    def get_icon_color_for_state(state: AppState, flash_on: bool = True) -> str:
        """Return the color for a high-level application state."""
        if state is AppState.RECORDING:
            return "tomato"
        if state is AppState.LOADING_MODEL:
            return "yellow"
        if state is AppState.PROCESSING:
            return "orange" if flash_on else "lightgreen"
        if state is AppState.ERROR:
            return "crimson"
        return "lightgreen"

    @classmethod
    def get_icon_image_for_state(
        cls, state: AppState, flash_on: bool = True
    ) -> Image.Image:
        """Build an icon image from the shared app state."""
        return cls.create_icon_image(cls.get_icon_color_for_state(state, flash_on))

    def update_icon(
        self,
        icon: PystrayIcon,
        is_recording: bool,
        model_ready: bool,
        is_processing: bool = False,
    ) -> None:
        """
        Update the tray icon to reflect current state.

        Args:
            icon: The pystray Icon instance
            is_recording: Whether currently recording audio
            model_ready: Whether the model is loaded and ready
            is_processing: Whether audio is being processed/transcribed
        """
        if icon is not None:
            try:
                icon.icon = self.get_icon_image(
                    is_recording, model_ready, is_processing
                )
            except Exception as e:
                logger.info(f"Error updating icon: {e}")

    def update_icon_for_presentation(
        self,
        icon: PystrayIcon,
        presentation: AppStatePresentation,
        flash_on: bool = True,
    ) -> None:
        """Update the tray icon using the shared presentation model."""
        if icon is not None:
            try:
                color = presentation.icon_color
                if (
                    presentation.state is AppState.PROCESSING
                    and presentation.flash_processing
                ):
                    color = presentation.icon_color if flash_on else "lightgreen"
                icon.icon = self.create_icon_image(color)
            except Exception as e:
                logger.info(f"Error updating icon: {e}")

    @staticmethod
    def get_tooltip(
        is_recording: bool, model_ready: bool, device: str, is_processing: bool = False
    ) -> str:
        """
        Get current tooltip text.

        Args:
            is_recording: Whether currently recording audio
            model_ready: Whether the model is loaded and ready
            device: Device the model is running on ('cuda' or 'cpu')
            is_processing: Whether audio is being processed/transcribed

        Returns:
            Tooltip text string
        """
        if not model_ready:
            return "Loading model..."
        elif is_recording:
            return "Recording..."
        elif is_processing:
            return "Processing..."
        elif device == "cpu":
            return "WhisperTray (CPU mode) - Ready"
        else:
            return "WhisperTray (GPU mode) - Ready"
