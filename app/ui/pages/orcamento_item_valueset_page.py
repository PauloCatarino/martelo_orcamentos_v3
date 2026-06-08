"""Budget item ValueSet page (create from budget + list lines)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaResumo,
)
from app.services.orcamento_item_valueset_linha_service import (
    OrcamentoItemValuesetLinhaService,
)
from app.utils.formatters import format_currency, format_quantity


class OrcamentoItemValuesetPage(QWidget):
    """Page listing the ValueSet lines of a budget item."""

    TABLE_HEADERS = [
        "Chave",
        "Opção",
        "Nome opção",
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Padrão",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
    ]

    def __init__(self, orcamento_item_id: int) -> None:
        super().__init__()

        self.orcamento_item_id = orcamento_item_id
        self._linhas_by_row: dict[int, OrcamentoItemValuesetLinhaResumo] = {}

        title = QLabel("ValueSet do Item")
        title.setObjectName("pageTitle")

        info = QLabel(
            "Materiais, ferragens, acabamentos, orlas, sistemas e acessórios "
            "definidos por defeito para este item."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.create_button = QPushButton("Criar a partir do Orçamento")
        self.create_button.clicked.connect(self.criar_do_orcamento)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.create_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemValuesetStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Load the ValueSet lines of the budget item."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = OrcamentoItemValuesetLinhaService(session).listar_linhas_do_item(
                    self.orcamento_item_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar o ValueSet do item.")
            return

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText(
                "Sem ValueSet. Use 'Criar a partir do Orçamento' para preencher este item."
            )

    def _preencher(self, linhas: list[OrcamentoItemValuesetLinhaResumo]) -> None:
        """Fill the table with ValueSet lines."""
        self._linhas_by_row = {}
        self.table.setRowCount(len(linhas))

        for row_index, linha in enumerate(linhas):
            self._linhas_by_row[row_index] = linha
            values = [
                linha.chave,
                linha.codigo_opcao or "",
                linha.nome_opcao or "",
                linha.ref_le or "",
                linha.descricao_no_orcamento or "",
                linha.unidade or "",
                format_currency(linha.preco_tabela),
                formatar_percentagem(linha.margem_percentagem),
                formatar_percentagem(linha.desconto_percentagem),
                format_currency(linha.preco_liquido),
                formatar_percentagem(linha.desperdicio_percentagem),
                linha.tipo_materia_prima or "",
                linha.familia_materia_prima or "",
                linha.coresp_orla_0_4 or "",
                linha.coresp_orla_1_0 or "",
                format_quantity(linha.comp_mp),
                format_quantity(linha.larg_mp),
                format_quantity(linha.esp_mp),
                self._format_bool(linha.padrao),
                str(linha.ordem),
                linha.origem_dados or "",
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def criar_do_orcamento(self) -> None:
        """Create the item ValueSet from the budget version ValueSet."""
        try:
            with SessionLocal() as session:
                result = OrcamentoItemValuesetLinhaService(
                    session
                ).criar_a_partir_do_orcamento(self.orcamento_item_id)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText(
                "Não foi possível criar o ValueSet a partir do orçamento."
            )
            return

        self.carregar()
        self.status_label.setText(
            f"ValueSet do item criado a partir do orçamento: "
            f"{result.criadas} criadas, {result.atualizadas} atualizadas, "
            f"{result.ignoradas} ignoradas (de {result.total_origem} linhas)."
        )

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
