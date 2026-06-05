"""Modules tab that follows the selected budget item."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.pages.orcamento_item_modulos_page import OrcamentoItemModulosPage


class OrcamentoModulosTab(QWidget):
    """Detail tab that shows the modules of the currently selected item."""

    PLACEHOLDER_TEXT = "Selecione um item na tab Items para ver os seus módulos."

    def __init__(self) -> None:
        super().__init__()

        self._current_item_id: int | None = None
        self._content_widget: QWidget | None = None

        self.header_label = QLabel("Módulos")
        self.header_label.setObjectName("orcamentoModulosTabHeader")

        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header_label)
        layout.addLayout(self._content_layout, stretch=1)

        self.setLayout(layout)

        self.set_item(None)

    def set_item(self, item_id: int | None, item_label: str = "") -> None:
        """Show the modules of the given item, or a placeholder when None."""
        self._current_item_id = item_id
        self._clear_content()

        if item_id is None:
            self.header_label.setText("Módulos")
            placeholder = QLabel(self.PLACEHOLDER_TEXT)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_content(placeholder)
            return

        label = item_label.strip()
        self.header_label.setText(f"Módulos do item {label}" if label else "Módulos do item")
        self._set_content(OrcamentoItemModulosPage(item_id))

    def _clear_content(self) -> None:
        """Remove the current content widget, if any."""
        if self._content_widget is not None:
            self._content_layout.removeWidget(self._content_widget)
            self._content_widget.deleteLater()
            self._content_widget = None

    def _set_content(self, widget: QWidget) -> None:
        """Place a new content widget in the tab."""
        self._content_widget = widget
        self._content_layout.addWidget(widget, stretch=1)
