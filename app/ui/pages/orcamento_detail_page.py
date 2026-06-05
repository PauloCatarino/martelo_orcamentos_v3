"""Simple budget detail page."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from app.repositories.orcamento_repository import OrcamentoResumo


class OrcamentoDetailPage(QWidget):
    """Read-only detail page for a selected budget version."""

    def __init__(self, orcamento: OrcamentoResumo, on_back=None) -> None:
        super().__init__()

        self.orcamento = orcamento
        self.on_back = on_back

        title = QLabel(f"Or\u00e7amento {orcamento.codigo_versao}")
        title.setObjectName("orcamentoDetailTitle")

        back_button = QPushButton("Voltar \u00e0 lista")
        back_button.clicked.connect(self._handle_back)

        header_layout = QHBoxLayout()
        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignRight)

        tabs = QTabWidget()
        tabs.addTab(self._create_dados_gerais_tab(), "Dados Gerais")
        tabs.addTab(self._create_placeholder_tab("Items do or\u00e7amento ser\u00e3o geridos aqui."), "Items")
        tabs.addTab(self._create_placeholder_tab("Custeio ser\u00e1 desenvolvido numa fase posterior."), "Custeio")
        tabs.addTab(self._create_placeholder_tab("Resumo do or\u00e7amento ser\u00e1 apresentado aqui."), "Resumo")
        tabs.addTab(self._create_placeholder_tab("Hist\u00f3rico de altera\u00e7\u00f5es ser\u00e1 apresentado aqui."), "Hist\u00f3rico")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header_layout)
        layout.addWidget(tabs, stretch=1)

        self.setLayout(layout)

    def _handle_back(self) -> None:
        """Call the optional back callback."""
        if self.on_back is not None:
            self.on_back()

    def _create_dados_gerais_tab(self) -> QWidget:
        """Create the general data tab."""
        tab = QWidget()
        form_layout = QFormLayout()
        form_layout.addRow("C\u00f3digo da vers\u00e3o", QLabel(self.orcamento.codigo_versao))
        form_layout.addRow("Ano", QLabel(str(self.orcamento.ano)))
        form_layout.addRow("N\u00ba Or\u00e7amento", QLabel(self.orcamento.num_orcamento))
        form_layout.addRow("Vers\u00e3o", QLabel(self._format_numero_versao(self.orcamento.numero_versao)))
        form_layout.addRow("Cliente", QLabel(self.orcamento.cliente_nome))
        form_layout.addRow("Obra", QLabel(self.orcamento.obra or ""))
        form_layout.addRow("Descri\u00e7\u00e3o", QLabel(self.orcamento.descricao or ""))
        form_layout.addRow("Localiza\u00e7\u00e3o", QLabel(self.orcamento.localizacao or ""))
        form_layout.addRow("Refer\u00eancia cliente", QLabel(self.orcamento.ref_cliente or ""))
        form_layout.addRow("Estado", QLabel(self.orcamento.estado))
        form_layout.addRow("Pre\u00e7o total", QLabel(self._format_decimal(self.orcamento.preco_total)))
        form_layout.addRow("Criado em", QLabel(self._format_datetime(self.orcamento.created_at)))

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
    def _format_numero_versao(value: int) -> str:
        """Format version number for display."""
        return f"{value:02d}"

    @staticmethod
    def _format_decimal(value: Decimal | None) -> str:
        """Format a decimal value for display."""
        if value is None:
            return ""

        return f"{value:.2f}"

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        """Format a datetime value for display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")
