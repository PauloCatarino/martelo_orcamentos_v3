"""Operations / machines catalog page (read-only)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.def_maquina_repository import DefMaquinaResumo
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.services.def_maquina_service import DefMaquinaService
from app.services.def_operacao_service import DefOperacaoService
from app.utils.formatters import format_currency, format_quantity


class OperacoesMaquinasPage(QWidget):
    """Read-only page listing production operations and machines."""

    OPERACOES_HEADERS = [
        "Código",
        "Nome",
        "Tipo",
        "Unidade cálculo",
        "Máquina",
        "Tempo base",
        "Tempo setup",
        "Custo/hora",
        "Custo mínimo",
        "Ativo",
    ]

    MAQUINAS_HEADERS = [
        "Código",
        "Nome",
        "Tipo",
        "Custo/hora",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        title = QLabel("Operações / Máquinas")
        title.setObjectName("pageTitle")

        info = QLabel(
            "Catálogo de operações e máquinas usado futuramente no custeio de "
            "corte, orlagem, CNC, montagem, mão de obra e outras operações de "
            "produção."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("operacoesMaquinasStatus")

        self.operacoes_table = self._create_table(self.OPERACOES_HEADERS)
        self.maquinas_table = self._create_table(self.MAQUINAS_HEADERS)

        tabs = QTabWidget()
        tabs.addTab(self._wrap_table(self.operacoes_table), "Operações")
        tabs.addTab(self._wrap_table(self.maquinas_table), "Máquinas")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(tabs, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Reload both operations and machines from the database."""
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                operacoes = DefOperacaoService(session).listar_operacoes()
                maquinas = DefMaquinaService(session).listar_maquinas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar operacoes e maquinas.")
            return

        maquina_labels = {maquina.id: f"{maquina.codigo} - {maquina.nome}" for maquina in maquinas}
        self._preencher_operacoes(operacoes, maquina_labels)
        self._preencher_maquinas(maquinas)

    def _preencher_operacoes(
        self,
        operacoes: list[DefOperacaoResumo],
        maquina_labels: dict[int, str],
    ) -> None:
        """Fill the operations table."""
        self.operacoes_table.setRowCount(len(operacoes))

        for row_index, operacao in enumerate(operacoes):
            values = [
                operacao.codigo,
                operacao.nome,
                operacao.tipo_operacao or "",
                operacao.unidade_calculo or "",
                self._format_maquina(operacao.maquina_id, maquina_labels),
                format_quantity(operacao.tempo_base),
                format_quantity(operacao.tempo_setup),
                format_currency(operacao.custo_hora),
                format_currency(operacao.custo_minimo),
                self._format_bool(operacao.ativo),
            ]

            for column_index, value in enumerate(values):
                self.operacoes_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _preencher_maquinas(self, maquinas: list[DefMaquinaResumo]) -> None:
        """Fill the machines table."""
        self.maquinas_table.setRowCount(len(maquinas))

        for row_index, maquina in enumerate(maquinas):
            values = [
                maquina.codigo,
                maquina.nome,
                maquina.tipo or "",
                format_currency(maquina.custo_hora),
                self._format_bool(maquina.ativo),
            ]

            for column_index, value in enumerate(values):
                self.maquinas_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _create_table(self, headers: list[str]) -> QTableWidget:
        """Create a read-only table with the given headers."""
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def _wrap_table(self, table: QTableWidget) -> QWidget:
        """Wrap one table in a tab container widget."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(table, stretch=1)
        tab.setLayout(layout)
        return tab

    def _format_maquina(self, maquina_id: int | None, maquina_labels: dict[int, str]) -> str:
        """Return the display label for one machine reference."""
        if maquina_id is None:
            return ""

        return maquina_labels.get(maquina_id, f"#{maquina_id}")

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
