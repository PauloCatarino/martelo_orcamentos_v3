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
from app.services.orcamento_service import CorrespondenciaRefCliente
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_version


class RefClienteDuplicadaDialog(QDialog):
    """Ask how to proceed when the customer reference already exists.

    Mostra tanto as refer\u00eancias iguais como as apenas parecidas (mal
    escritas, com plural, com outra pontua\u00e7\u00e3o), com o grau de semelhan\u00e7a
    na primeira coluna, para o utilizador decidir.
    """

    TABLE_HEADERS = [
        "Semelhan\u00e7a",
        "Ref. Cliente",
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Cliente",
        "Obra",
        "Estado",
        "Data",
    ]
    CENTERED_HEADERS = {
        "Semelhan\u00e7a",
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Estado",
        "Data",
    }

    def __init__(
        self,
        ref_cliente: str,
        correspondencias: list[CorrespondenciaRefCliente],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.resultado: str = "cancelar"
        self.selecionado: OrcamentoResumo | None = None
        self._orcamentos_by_row: dict[int, OrcamentoResumo] = {}

        ref = (ref_cliente or "").strip()

        self.setWindowTitle("Ref. Cliente igual ou parecida")
        self.setModal(True)
        self.setMinimumSize(980, 360)

        intro_label = QLabel(self._texto_intro(ref, correspondencias))
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
        # "_v2": a tabela ganhou colunas, as larguras antigas ficariam trocadas.
        self._larguras_restauradas = ligar_persistencia_larguras(
            self.table, "dialog_ref_cliente_duplicada_v2"
        )
        header.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
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

    @staticmethod
    def _texto_intro(
        ref: str, correspondencias: list[CorrespondenciaRefCliente]
    ) -> str:
        """Frase de abertura, a dizer quantas são iguais e quantas parecidas."""
        iguais = sum(1 for item in correspondencias if item.semelhanca.e_igual)
        parecidas = len(correspondencias) - iguais

        detalhe = []
        if iguais:
            detalhe.append(f"{iguais} igual(ais)")
        if parecidas:
            detalhe.append(f"{parecidas} parecida(s)")

        return (
            f"Já existe(m) {len(correspondencias)} orçamento(s) com a Ref. "
            f"Cliente «{ref}» ou parecida ({' e '.join(detalhe)}).\n"
            "O que pretende fazer?"
        )

    def _preencher_tabela(
        self, correspondencias: list[CorrespondenciaRefCliente]
    ) -> None:
        self._orcamentos_by_row = {}
        self.table.setRowCount(len(correspondencias))

        for row_index, correspondencia in enumerate(correspondencias):
            orcamento = correspondencia.orcamento
            semelhanca = correspondencia.semelhanca
            self._orcamentos_by_row[row_index] = orcamento
            values = [
                semelhanca.etiqueta,
                orcamento.ref_cliente or "",
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
                if column_index == 0:
                    item.setToolTip(semelhanca.explicacao)
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
        if self._larguras_restauradas:
            return

        larguras = (110, 130, 60, 110, 70, 190, 200, 125, 95)
        for column_index, largura in enumerate(larguras):
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
