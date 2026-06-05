"""Orcamentos page."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt
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

from app.core.session import app_session
from app.db.session import SessionLocal
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import CriarOrcamentoSimplesData, OrcamentoService
from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog
from app.utils.formatters import format_currency, format_version


class OrcamentosPage(QWidget):
    """Structural budgets page without data access yet."""

    TABLE_HEADERS = [
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Cliente",
        "Obra",
        "Estado",
        "Pre\u00e7o Total",
        "Criado em",
    ]

    def __init__(self, on_open_orcamento: Callable[[OrcamentoResumo], None] | None = None) -> None:
        super().__init__()

        self.on_open_orcamento = on_open_orcamento
        self._orcamentos_by_row: dict[int, OrcamentoResumo] = {}

        title = QLabel("Or\u00e7amentos")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Gest\u00e3o de or\u00e7amentos do Martelo V3")
        subtitle.setObjectName("pageSubtitle")

        self.new_button = QPushButton("Novo Or\u00e7amento")
        self.new_button.clicked.connect(self.abrir_novo_orcamento)

        self.open_button = QPushButton("Abrir Or\u00e7amento")
        self.open_button.clicked.connect(self.abrir_orcamento_selecionado)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_orcamentos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentosStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)

    def carregar_orcamentos(self) -> None:
        """Load budget versions into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                orcamentos = OrcamentoService(session).list_orcamentos()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os orcamentos.")
            return

        self._preencher_tabela(orcamentos)

        if not orcamentos:
            self.status_label.setText("Sem orcamentos para mostrar.")

    def abrir_novo_orcamento(self) -> None:
        """Open the simple new budget dialog."""
        dialog = NovoOrcamentoDialog(self)

        if not dialog.exec():
            return

        form_data = dialog.get_data()
        current_user = app_session.current_user
        created_by_id = current_user.id if current_user is not None else None

        try:
            with SessionLocal() as session:
                service = OrcamentoService(session)
                result = service.criar_orcamento_simples(
                    CriarOrcamentoSimplesData(
                        nome_cliente=form_data.nome_cliente,
                        email_cliente=form_data.email_cliente,
                        telefone_cliente=form_data.telefone_cliente,
                        obra=form_data.obra,
                        descricao=form_data.descricao,
                        localizacao=form_data.localizacao,
                        ref_cliente=form_data.ref_cliente,
                        created_by_id=created_by_id,
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel criar o orcamento.")
            return

        self.status_label.setText(f"Orcamento {result.codigo_versao} criado.")
        self.carregar_orcamentos()

    def _preencher_tabela(self, orcamentos: list[OrcamentoResumo]) -> None:
        """Fill the table with budget read models."""
        self._orcamentos_by_row = {}
        self.table.setRowCount(len(orcamentos))

        for row_index, orcamento in enumerate(orcamentos):
            self._orcamentos_by_row[row_index] = orcamento
            values = [
                str(orcamento.ano),
                orcamento.num_orcamento,
                format_version(orcamento.numero_versao),
                orcamento.cliente_nome,
                orcamento.obra or "",
                orcamento.estado,
                format_currency(orcamento.preco_total),
                self._format_datetime(orcamento.created_at),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        {
                            "orcamento_id": orcamento.orcamento_id,
                            "orcamento_versao_id": orcamento.orcamento_versao_id,
                        },
                    )
                self.table.setItem(row_index, column_index, item)

    def abrir_orcamento_selecionado(self) -> None:
        """Open the currently selected budget through the callback."""
        row = self.table.currentRow()
        orcamento = self._orcamentos_by_row.get(row)

        if row < 0 or orcamento is None:
            self.status_label.setText("Selecione um orcamento para abrir.")
            return

        if self.on_open_orcamento is not None:
            self.on_open_orcamento(orcamento)

    def _handle_row_double_click(self, row: int, _column: int) -> None:
        """Open a budget when the user double-clicks its table row."""
        self.table.selectRow(row)
        self.abrir_orcamento_selecionado()

    def _format_datetime(self, value: datetime | None) -> str:
        """Format a datetime value for table display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")
