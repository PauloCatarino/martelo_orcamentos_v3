"""Dialog for resolving duplicate customer references."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.repositories.orcamento_repository import OrcamentoResumo
from app.ui import tema
from app.utils.formatters import format_version


class RefClienteDuplicadaDialog(QDialog):
    """Ask how to proceed when the customer reference already exists."""

    TABLE_HEADERS = [
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Cliente",
        "Obra",
        "Estado",
        "Data",
    ]
    CENTERED_HEADERS = {"Ano", "N\u00ba Or\u00e7amento", "Vers\u00e3o", "Estado", "Data"}

    def __init__(
        self,
        ref_cliente: str,
        correspondencias: list[OrcamentoResumo],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.resultado: str = "cancelar"
        self.selecionado: OrcamentoResumo | None = None
        self._orcamentos_by_row: dict[int, OrcamentoResumo] = {}

        ref = (ref_cliente or "").strip()
        total = len(correspondencias)

        self.setWindowTitle("Ref. Cliente j\u00e1 existe")
        self.setModal(True)
        self.setMinimumSize(860, 360)

        intro_label = QLabel(
            f"J\u00e1 existe(m) {total} or\u00e7amento(s) com a Ref. Cliente "
            f"\u00ab{ref}\u00bb.\nO que pretende fazer?"
        )
        intro_label.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self.table.itemSelectionChanged.connect(self._atualizar_reabrir)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.reabrir_button = QPushButton("Reabrir selecionado")
        self.reabrir_button.setToolTip("Abrir o or\u00e7amento j\u00e1 existente.")
        self.reabrir_button.clicked.connect(self._reabrir)

        self.novo_button = QPushButton("Criar novo na mesma")
        self.novo_button.setToolTip("Criar mesmo assim um or\u00e7amento novo.")
        self.novo_button.clicked.connect(self._criar_novo)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("N\u00e3o criar nada.")
        self.cancelar_button.clicked.connect(self._cancelar)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.reabrir_button)
        buttons_layout.addWidget(self.novo_button)
        buttons_layout.addWidget(self.cancelar_button)

        layout = QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._preencher_tabela(correspondencias)
        self._atualizar_reabrir()

    def _preencher_tabela(self, correspondencias: list[OrcamentoResumo]) -> None:
        self._orcamentos_by_row = {}
        self.table.setRowCount(len(correspondencias))

        for row_index, orcamento in enumerate(correspondencias):
            self._orcamentos_by_row[row_index] = orcamento
            values = [
                str(orcamento.ano),
                orcamento.num_orcamento,
                format_version(orcamento.numero_versao),
                orcamento.cliente_nome,
                orcamento.obra or "",
                orcamento.estado,
                self._format_date(orcamento.created_at),
            ]

            for column_index, value in enumerate(values):
                header = self.TABLE_HEADERS[column_index]
                item = self._criar_item_tabela(value, header)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                self.table.setItem(row_index, column_index, item)

        self._aplicar_larguras_colunas()
        if correspondencias:
            self.table.selectRow(0)

    def _criar_item_tabela(self, value: str, header: str) -> QTableWidgetItem:
        item = QTableWidgetItem(value)
        if header in self.CENTERED_HEADERS:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        if value:
            item.setToolTip(value)
        return item

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, largura in enumerate((60, 110, 70, 210, 230, 125, 95)):
            self.table.setColumnWidth(column_index, largura)

    def _orcamento_selecionado(self) -> OrcamentoResumo | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._orcamentos_by_row.get(row)

    def _atualizar_reabrir(self) -> None:
        self.reabrir_button.setEnabled(self._orcamento_selecionado() is not None)

    def _reabrir(self) -> None:
        orcamento = self._orcamento_selecionado()
        if orcamento is None:
            return

        self.selecionado = orcamento
        self.resultado = "reabrir"
        self.accept()

    def _criar_novo(self) -> None:
        self.resultado = "novo"
        self.selecionado = None
        self.accept()

    def _cancelar(self) -> None:
        self.resultado = "cancelar"
        self.selecionado = None
        self.reject()

    def _handle_double_click(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self._reabrir()

    @staticmethod
    def _format_date(value: datetime | None) -> str:
        """Format a datetime value for table display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d")
