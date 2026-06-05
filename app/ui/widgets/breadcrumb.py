"""Simple breadcrumb widget."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


def format_breadcrumb(items: Sequence[str]) -> str:
    """Format breadcrumb items as a single text line."""
    normalized_items = [str(item).strip() for item in items if str(item).strip()]
    return " > ".join(normalized_items)


class Breadcrumb(QWidget):
    """Simple text breadcrumb."""

    def __init__(self, items: Sequence[str] | None = None, parent=None) -> None:
        super().__init__(parent)

        self.setObjectName("breadcrumb")
        self.label = QLabel("")
        self.label.setObjectName("breadcrumbLabel")
        self.label.setWordWrap(True)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.set_items(items or [])

    def set_items(self, items: Sequence[str]) -> None:
        """Update the breadcrumb items."""
        self.label.setText(format_breadcrumb(items))

    def text(self) -> str:
        """Return the current breadcrumb text."""
        return self.label.text()
