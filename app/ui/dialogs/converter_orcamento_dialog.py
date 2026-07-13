"""Dialog for selecting an adjudicated budget to convert to production."""

from __future__ import annotations

import re

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
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.producao_service import (
    listar_orcamentos_convertiveis,
    validar_conversao,
)
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_version


class ConverterOrcamentoDialog(QDialog):
    """Modal dialog to pick a budget version for production conversion."""

    TABLE_HEADERS = [
        "Ano",
        "Nº Orç",
        "Versão",
        "Cliente",
        "Nº Enc PHC",
        "Preço",
        "Pronto?",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.selected_orcamento_id: int | None = None
        self.selected_versao_id: int | None = None
        self._todos: list[dict] = []
        self._linhas: list[dict] = []

        self.setWindowTitle("Converter Orçamento")
        self.setModal(True)
        self.setMinimumSize(820, 460)

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar orçamento, cliente ou encomenda PHC..."
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._render)

        self.status_label = QLabel("")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        ligar_persistencia_larguras(self.table, "dialog_converter_orcamento")
        self.table.itemSelectionChanged.connect(self._atualizar_ok)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.ok_button = QPushButton("OK")
        self.ok_button.setToolTip("Converter o orçamento selecionado")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._confirmar)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setToolTip("Fechar sem converter")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.campo_pesquisa)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar()

    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                self._todos = listar_orcamentos_convertiveis(session)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os orcamentos.")
            return

        self._render()
        if not self._todos:
            self.status_label.setText("Sem orçamentos adjudicados para converter.")

    def _render(self, *_args) -> None:
        termos = [
            termo
            for termo in re.split(r"[\s%]+", self.campo_pesquisa.texto().strip().lower())
            if termo
        ]
        linhas = []
        for item in self._todos:
            haystack = " ".join(
                str(item.get(campo) or "").lower()
                for campo in (
                    "ano",
                    "num_orcamento",
                    "numero_versao",
                    "cliente_nome",
                    "enc_phc",
                    "preco_total",
                )
            )
            if all(termo in haystack for termo in termos):
                linhas.append(item)

        self._linhas = linhas
        self.table.setRowCount(len(linhas))
        for row_index, item in enumerate(linhas):
            erros = validar_conversao(
                estado="Adjudicado",
                is_temporary=item["is_temporary"],
                source_system=item["source_system"],
                num_cliente_phc=item["num_cliente_phc"],
                enc_phc=item["enc_phc"],
            )
            values = [
                str(item["ano"]),
                item["num_orcamento"],
                format_version(item["numero_versao"]),
                item["cliente_nome"],
                item["enc_phc"] or "",
                format_currency(item["preco_total"]),
                "✓" if not erros else erros[0],
            ]
            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if value:
                    table_item.setToolTip(value)
                self.table.setItem(row_index, column_index, table_item)

        self._atualizar_ok()

    def _get_selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._linhas):
            return None
        return self._linhas[row]

    def _atualizar_ok(self) -> None:
        self.ok_button.setEnabled(self._get_selected() is not None)

    def _confirmar(self) -> None:
        item = self._get_selected()
        if item is None:
            self.status_label.setText("Selecione um orçamento.")
            return

        self.selected_orcamento_id = item["orcamento_id"]
        self.selected_versao_id = item["versao_id"]
        self.accept()

    def _handle_double_click(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self._confirmar()
