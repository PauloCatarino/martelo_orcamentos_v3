"""Image preview helpers for UI widgets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap


def load_scaled_pixmap(caminho: str | None, tamanho: QSize) -> QPixmap | None:
    """Load and scale an image, returning None when the path is invalid."""
    if not caminho:
        return None

    try:
        path = Path(caminho)
    except (TypeError, ValueError):
        return None

    if not path.is_file():
        return None

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None

    if not tamanho.isValid() or tamanho.width() <= 0 or tamanho.height() <= 0:
        return pixmap

    return pixmap.scaled(
        tamanho,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
