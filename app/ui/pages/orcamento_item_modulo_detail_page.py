"""Budget item module detail page."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from app.repositories.orcamento_item_modulo_repository import OrcamentoItemModuloResumo
from app.ui.widgets.breadcrumb import Breadcrumb
from app.utils.formatters import format_mm, format_quantity


class OrcamentoItemModuloDetailPage(QWidget):
    """Read-only detail page for one budget item module."""

    def __init__(
        self,
        modulo: OrcamentoItemModuloResumo,
        on_back: Callable[[], None] | None = None,
        orcamento_codigo: str | None = None,
        item_label: str | None = None,
    ) -> None:
        super().__init__()

        self.modulo = modulo
        self.on_back = on_back
        self.orcamento_codigo = orcamento_codigo
        self.item_label = item_label
        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())

        title = QLabel(f"M\u00f3dulo: {modulo.nome}")
        title.setObjectName("orcamentoItemModuloDetailTitle")

        back_button = QPushButton("Voltar aos M\u00f3dulos")
        back_button.clicked.connect(self._handle_back)

        header_layout = QHBoxLayout()
        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignRight)

        tabs = QTabWidget()
        tabs.addTab(self._create_dados_gerais_tab(), "Dados Gerais")
        tabs.addTab(self._create_placeholder_tab("Pe\u00e7as do m\u00f3dulo ser\u00e3o geridas aqui."), "Pe\u00e7as")
        tabs.addTab(self._create_placeholder_tab("Custeio do m\u00f3dulo ser\u00e1 desenvolvido numa fase posterior."), "Custeio")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.breadcrumb)
        layout.addLayout(header_layout)
        layout.addWidget(tabs, stretch=1)

        self.setLayout(layout)

    def _handle_back(self) -> None:
        """Call the optional back callback."""
        if self.on_back is not None:
            self.on_back()

    def _build_breadcrumb_items(self) -> list[str]:
        """Return breadcrumb items for the module detail page."""
        items: list[str] = []
        if self.orcamento_codigo:
            items.append(f"Or\u00e7amento {self.orcamento_codigo}")
        if self.item_label:
            items.append(f"Item: {self.item_label}")

        items.append(f"M\u00f3dulo: {self.modulo.nome}")
        return items

    def _create_dados_gerais_tab(self) -> QWidget:
        """Create the general data tab."""
        tab = QWidget()
        form_layout = QFormLayout()
        form_layout.addRow("Ordem", QLabel(str(self.modulo.ordem)))
        form_layout.addRow("Nome", QLabel(self.modulo.nome))
        form_layout.addRow("Descri\u00e7\u00e3o", QLabel(self.modulo.descricao or ""))
        form_layout.addRow("Altura", QLabel(format_mm(self.modulo.altura)))
        form_layout.addRow("Largura", QLabel(format_mm(self.modulo.largura)))
        form_layout.addRow("Profundidade", QLabel(format_mm(self.modulo.profundidade)))
        form_layout.addRow("Quantidade", QLabel(format_quantity(self.modulo.quantidade)))
        form_layout.addRow("Criado em", QLabel(self._format_datetime(self.modulo.created_at)))
        form_layout.addRow("Atualizado em", QLabel(self._format_datetime(self.modulo.updated_at)))

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addStretch()
        tab.setLayout(layout)

        return tab

    def _create_placeholder_tab(self, text: str) -> QWidget:
        """Create a simple placeholder tab."""
        tab = QWidget()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(label)
        tab.setLayout(layout)

        return tab

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        """Format a datetime value for display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")
