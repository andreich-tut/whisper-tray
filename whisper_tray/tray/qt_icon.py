"""Qt icon conversion helpers."""

from __future__ import annotations

from typing import Any


def pil_image_to_qicon(image: Any) -> Any:
    """Convert a PIL image into a QIcon without importing Qt at module load."""
    from PySide6.QtGui import QIcon, QImage, QPixmap

    rgba = image.convert("RGBA")
    buffer = rgba.tobytes("raw", "RGBA")
    image_format = (
        QImage.Format.Format_RGBA8888
        if hasattr(QImage, "Format")
        else getattr(QImage, "Format_RGBA8888")
    )
    qimage = QImage(buffer, rgba.width, rgba.height, image_format).copy()
    return QIcon(QPixmap.fromImage(qimage))
