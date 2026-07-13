"""Editable detail of the effective operations inside one costing line."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain.custeio_linha_types import FERRAGEM
from app.domain.regra_operacao_types import get_regra_operacao_label
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.services.orcamento_item_custeio_linha_service import (
    OperacaoEfetivaLinhaResumo,
)
from app.ui.dialogs.def_peca_operacao_dialog import UNIDADE_TEMPO_LABELS
from app.utils.formatters import format_currency, format_quantity


RecarregarOperacoes = Callable[
    [],
    tuple[
        OrcamentoItemCusteioLinhaResumo,
        list[OperacaoEfetivaLinhaResumo],
        bool,
    ],
]
AcaoSimples = Callable[[], bool]
AcaoOperacao = Callable[[OperacaoEfetivaLinhaResumo], bool]


class CusteioLinhaOperacoesDialog(QDialog):
    HEADERS = (
        "Ordem",
        "Operação",
        "Tipo",
        "Máquina",
        "Origem",
        "Ação",
        "Regra",
        "Quantidade base",
        "Rasgo",
        "Setup (min)",
        "Tempo/unidade",
        "Unidade tempo",
        "Obrigatória",
    )

    def __init__(
        self,
        linha: OrcamentoItemCusteioLinhaResumo,
        operacoes: list[OperacaoEfetivaLinhaResumo],
        parent: QWidget | None = None,
        *,
        on_recarregar: RecarregarOperacoes | None = None,
        on_adicionar: AcaoSimples | None = None,
        on_editar: AcaoOperacao | None = None,
        on_remover: AcaoOperacao | None = None,
        on_repor: AcaoSimples | None = None,
        tem_edicao_local: bool = False,
    ) -> None:
        super().__init__(parent)
        self._on_recarregar = on_recarregar
        self._on_adicionar = on_adicionar
        self._on_editar = on_editar
        self._on_remover = on_remover
        self._on_repor = on_repor
        self._operacoes_by_row: dict[int, OperacaoEfetivaLinhaResumo] = {}
        self._tem_edicao_local = tem_edicao_local

        self.setWindowTitle("Operações da peça no custeio")
        self.resize(1240, 620)

        self.titulo_label = QLabel()
        self.titulo_label.setObjectName("custeioLinhaOperacoesTitulo")
        self.titulo_label.setWordWrap(True)
        nota = QLabel(
            "As operações pertencem apenas a esta linha e não criam linhas "
            "adicionais no custeio. Ao guardar uma alteração, o custo da linha "
            "e do item é recalculado imediatamente. O catálogo da peça não é alterado."
        )
        nota.setWordWrap(True)

        self.alerta_label = QLabel()
        self.alerta_label.setWordWrap(True)
        self.alerta_label.setObjectName("custeioLinhaOperacoesAlerta")

        resumo = QFormLayout()
        self.operacoes_label = QLabel()
        self.maquinas_label = QLabel()
        self.tipo_producao_label = QLabel()
        self.custo_corte_label = QLabel()
        self.custo_orlagem_label = QLabel()
        self.custo_cnc_label = QLabel()
        self.custo_manual_label = QLabel()
        self.custo_producao_label = QLabel()
        resumo.addRow("Operações efetivas", self.operacoes_label)
        resumo.addRow("Máquinas", self.maquinas_label)
        resumo.addRow("Tipo de produção", self.tipo_producao_label)
        resumo.addRow("Custo corte", self.custo_corte_label)
        resumo.addRow("Custo orlagem", self.custo_orlagem_label)
        resumo.addRow("Custo CNC", self.custo_cnc_label)
        resumo.addRow("Custo montagem/manual", self.custo_manual_label)
        resumo.addRow("Custo produção total", self.custo_producao_label)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.itemSelectionChanged.connect(self._atualizar_botoes)
        self.table.itemDoubleClicked.connect(lambda _item: self._editar())

        self.status_label = QLabel()
        self.adicionar_button = QPushButton("Nova operação")
        self.editar_button = QPushButton("Editar operação")
        self.remover_button = QPushButton("Remover operação")
        self.repor_button = QPushButton("Repor operações da origem")
        fechar_button = QPushButton("Fechar")
        self.adicionar_button.clicked.connect(self._adicionar)
        self.editar_button.clicked.connect(self._editar)
        self.remover_button.clicked.connect(self._remover)
        self.repor_button.clicked.connect(self._repor)
        fechar_button.clicked.connect(self.accept)

        acoes = QHBoxLayout()
        acoes.addWidget(self.adicionar_button)
        acoes.addWidget(self.editar_button)
        acoes.addWidget(self.remover_button)
        acoes.addWidget(self.repor_button)
        acoes.addStretch(1)
        acoes.addWidget(fechar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.titulo_label)
        layout.addWidget(nota)
        layout.addWidget(self.alerta_label)
        layout.addLayout(resumo)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.status_label)
        layout.addLayout(acoes)
        self._aplicar_dados(linha, operacoes, tem_edicao_local)

    def _operacao_selecionada(self) -> OperacaoEfetivaLinhaResumo | None:
        rows = self.table.selectionModel().selectedRows()
        return self._operacoes_by_row.get(rows[0].row()) if rows else None

    def _atualizar_botoes(self) -> None:
        selecionada = self._operacao_selecionada() is not None
        self.editar_button.setEnabled(selecionada and self._on_editar is not None)
        self.remover_button.setEnabled(selecionada and self._on_remover is not None)
        self.adicionar_button.setEnabled(self._on_adicionar is not None)
        self.repor_button.setEnabled(
            self._on_repor is not None and self._tem_edicao_local
        )

    def _executar_e_recarregar(self, acao: Callable[[], bool] | None) -> None:
        if acao is None or not acao():
            return
        if self._on_recarregar is not None:
            linha, operacoes, tem_edicao_local = self._on_recarregar()
            self._aplicar_dados(linha, operacoes, tem_edicao_local)

    def _adicionar(self) -> None:
        self._executar_e_recarregar(self._on_adicionar)

    def _editar(self) -> None:
        operacao = self._operacao_selecionada()
        if operacao is not None and self._on_editar is not None:
            self._executar_e_recarregar(lambda: self._on_editar(operacao))

    def _remover(self) -> None:
        operacao = self._operacao_selecionada()
        if operacao is not None and self._on_remover is not None:
            self._executar_e_recarregar(lambda: self._on_remover(operacao))

    def _repor(self) -> None:
        self._executar_e_recarregar(self._on_repor)

    def _aplicar_dados(
        self,
        linha: OrcamentoItemCusteioLinhaResumo,
        operacoes: list[OperacaoEfetivaLinhaResumo],
        tem_edicao_local: bool,
    ) -> None:
        self._tem_edicao_local = tem_edicao_local
        self.titulo_label.setText(
            f"{linha.codigo or linha.def_peca_codigo or 'Linha'} — {linha.descricao}"
        )
        self.operacoes_label.setText(str(len(operacoes)))
        self.maquinas_label.setText(linha.maquina or "—")
        self.tipo_producao_label.setText(linha.tipo_producao or "—")
        self.custo_corte_label.setText(format_currency(linha.custo_corte))
        self.custo_orlagem_label.setText(format_currency(linha.custo_orlagem))
        self.custo_cnc_label.setText(format_currency(linha.custo_cnc))
        self.custo_manual_label.setText(format_currency(linha.custo_montagem_manual))
        self.custo_producao_label.setText(format_currency(linha.custo_producao))
        local = tem_edicao_local or any(
            item.origem == "Edição local" for item in operacoes
        )
        if not operacoes and linha.tipo_linha == FERRAGEM:
            self.alerta_label.setText(
                "⚠ Ferragem sem operações efetivas. Confirme se falta, por exemplo, "
                "uma operação de CNC/furação ou de montagem; o custo de produção pode "
                "estar incompleto."
            )
        elif local:
            self.alerta_label.setText(
                "Edição local ativa: estas operações aplicam-se somente a esta linha."
            )
        else:
            self.alerta_label.setText("")
        self.alerta_label.setVisible(bool(self.alerta_label.text()))
        self.status_label.setText(
            "Sem operações efetivas nesta linha."
            if not operacoes
            else f"{len(operacoes)} operação(ões) efetiva(s)."
        )
        self._preencher(operacoes)
        self._atualizar_botoes()

    def _preencher(self, operacoes: list[OperacaoEfetivaLinhaResumo]) -> None:
        self._operacoes_by_row.clear()
        self.table.setRowCount(len(operacoes))
        for row, operacao in enumerate(operacoes):
            self._operacoes_by_row[row] = operacao
            rasgo = ""
            if operacao.rasgo_qt_comp or operacao.rasgo_qt_larg:
                rasgo = (
                    f"{operacao.rasgo_qt_comp} × COMP + "
                    f"{operacao.rasgo_qt_larg} × LARG"
                )
            valores = (
                str(operacao.ordem),
                " — ".join(filter(None, (operacao.codigo, operacao.nome))),
                operacao.tipo_operacao or "",
                operacao.maquina,
                operacao.origem,
                operacao.acao or "Base",
                get_regra_operacao_label(operacao.regra_calculo),
                format_quantity(operacao.quantidade_base),
                rasgo,
                format_quantity(operacao.tempo_setup_minutos),
                format_quantity(operacao.tempo_por_unidade_minutos),
                UNIDADE_TEMPO_LABELS.get(
                    operacao.unidade_tempo, operacao.unidade_tempo or ""
                ),
                "Sim" if operacao.obrigatorio else "Não",
            )
            for column, value in enumerate(valores):
                self.table.setItem(row, column, QTableWidgetItem(value))
