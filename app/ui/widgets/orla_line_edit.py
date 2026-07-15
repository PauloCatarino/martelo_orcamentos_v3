"""Line edit that exposes a double-click signal for selecting an edge band."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit


class OrlaLineEdit(QLineEdit):
    """Editable orla reference field; double-click opens the orla picker."""

    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt API name
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)
