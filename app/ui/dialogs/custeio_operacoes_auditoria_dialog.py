"""Read-only operation coverage audit for one budget item."""

from __future__ import annotations

from collections.abc import Callable

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
    QWidget,
)

from app.domain.custeio_linha_types import get_custeio_linha_type_label
from app.services.orcamento_item_custeio_linha_service import (
    AuditoriaOperacaoLinhaResumo,
)
from app.utils.formatters import format_currency


class CusteioOperacoesAuditoriaDialog(QDialog):
    HEADERS = (
        "Estado",
        "Tipo",
        "Linha",
        "Descrição",
        "Operações",
        "Origens",
        "Máquinas",
        "Custo produção",
        "Diagnóstico",
    )

    def __init__(
        self,
        linhas: list[AuditoriaOperacaoLinhaResumo],
        parent: QWidget | None = None,
        *,
        on_abrir_linha: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._linhas_by_row: dict[int, AuditoriaOperacaoLinhaResumo] = {}
        self._on_abrir_linha = on_abrir_linha
        self.setWindowTitle("Auditoria de operações do item")
        self.resize(1280, 650)

        titulo = QLabel("Cobertura de operações das peças e ferragens do item")
        titulo.setObjectName("custeioOperacoesAuditoriaTitulo")
        nota = QLabel(
            "Análise apenas de leitura. As linhas com atenção aparecem primeiro. "
            "Abra uma linha para consultar ou corrigir as operações localmente."
        )
        nota.setWordWrap(True)
        atencoes = sum(linha.estado != "OK" for linha in linhas)
        sem_operacoes = sum(linha.operacoes_efetivas == 0 for linha in linhas)
        resumo = QLabel(
            f"Linhas analisadas: {len(linhas)}  |  A verificar: {atencoes}  |  "
            f"Sem operações: {sem_operacoes}"
        )
        resumo.setStyleSheet("font-weight: bold; padding: 5px 0;")

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.itemSelectionChanged.connect(self._atualizar_botao)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._abrir())
        self._preencher(linhas)

        self.abrir_button = QPushButton("Abrir operações da linha")
        self.abrir_button.clicked.connect(self._abrir)
        self.abrir_button.setEnabled(False)
        fechar_button = QPushButton("Fechar")
        fechar_button.clicked.connect(self.reject)
        botoes = QHBoxLayout()
        botoes.addWidget(self.abrir_button)
        botoes.addStretch(1)
        botoes.addWidget(fechar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(nota)
        layout.addWidget(resumo)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(botoes)

    def _linha_selecionada(self) -> AuditoriaOperacaoLinhaResumo | None:
        rows = self.table.selectionModel().selectedRows()
        return self._linhas_by_row.get(rows[0].row()) if rows else None

    def _atualizar_botao(self) -> None:
        self.abrir_button.setEnabled(
            self._linha_selecionada() is not None and self._on_abrir_linha is not None
        )

    def _abrir(self) -> None:
        linha = self._linha_selecionada()
        if linha is None or self._on_abrir_linha is None:
            return
        self._on_abrir_linha(linha.linha_id)
        self.accept()

    def _preencher(self, linhas: list[AuditoriaOperacaoLinhaResumo]) -> None:
        self._linhas_by_row.clear()
        self.table.setRowCount(len(linhas))
        cores = {
            "ATENÇÃO": QColor("#F8D7DA"),
            "VERIFICAR": QColor("#FFF3CD"),
            "OK": QColor("#D4EDDA"),
        }
        for row, linha in enumerate(linhas):
            self._linhas_by_row[row] = linha
            valores = (
                linha.estado,
                get_custeio_linha_type_label(linha.tipo_linha),
                linha.codigo,
                linha.descricao,
                str(linha.operacoes_efetivas),
                linha.origens,
                linha.maquinas,
                format_currency(linha.custo_producao),
                linha.diagnostico,
            )
            for column, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setToolTip(valor)
                if column == 0:
                    item.setBackground(cores.get(linha.estado, QColor("white")))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()
