"""Simple budget detail page."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.repositories.orcamento_repository import OrcamentoResumo


class OrcamentoDetailPage(QWidget):
    """Read-only detail page for a selected budget version."""

    def __init__(self, orcamento: OrcamentoResumo, on_back=None) -> None:
        super().__init__()

        self.orcamento = orcamento
        self.on_back = on_back

        title = QLabel(f"Or\u00e7amento {orcamento.codigo_versao}")
        title.setObjectName("orcamentoDetailTitle")

        form_layout = QFormLayout()
        form_layout.addRow("C\u00f3digo da vers\u00e3o", QLabel(orcamento.codigo_versao))
        form_layout.addRow("Ano", QLabel(str(orcamento.ano)))
        form_layout.addRow("N\u00ba Or\u00e7amento", QLabel(orcamento.num_orcamento))
        form_layout.addRow("Vers\u00e3o", QLabel(self._format_numero_versao(orcamento.numero_versao)))
        form_layout.addRow("Cliente", QLabel(orcamento.cliente_nome))
        form_layout.addRow("Obra", QLabel(orcamento.obra or ""))
        form_layout.addRow("Descri\u00e7\u00e3o", QLabel(orcamento.descricao or ""))
        form_layout.addRow("Localiza\u00e7\u00e3o", QLabel(orcamento.localizacao or ""))
        form_layout.addRow("Refer\u00eancia cliente", QLabel(orcamento.ref_cliente or ""))
        form_layout.addRow("Estado", QLabel(orcamento.estado))
        form_layout.addRow("Pre\u00e7o total", QLabel(self._format_decimal(orcamento.preco_total)))
        form_layout.addRow("Criado em", QLabel(self._format_datetime(orcamento.created_at)))

        back_button = QPushButton("Voltar \u00e0 lista")
        back_button.clicked.connect(self._handle_back)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addStretch()
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.setLayout(layout)

    def _handle_back(self) -> None:
        """Call the optional back callback."""
        if self.on_back is not None:
            self.on_back()

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
