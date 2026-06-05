"""Orcamentos page."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

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

    def __init__(self) -> None:
        super().__init__()

        title = QLabel("Or\u00e7amentos")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Gest\u00e3o de or\u00e7amentos do Martelo V3")
        subtitle.setObjectName("pageSubtitle")

        self.new_button = QPushButton("Novo Or\u00e7amento")
        self.new_button.clicked.connect(self.abrir_novo_orcamento)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_orcamentos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
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
        self.table.setRowCount(len(orcamentos))

        for row_index, orcamento in enumerate(orcamentos):
            values = [
                str(orcamento.ano),
                orcamento.num_orcamento,
                self._format_numero_versao(orcamento.numero_versao),
                orcamento.cliente_nome,
                orcamento.obra or "",
                orcamento.estado,
                self._format_decimal(orcamento.preco_total),
                self._format_datetime(orcamento.created_at),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _format_decimal(self, value: Decimal | None) -> str:
        """Format a decimal value for table display."""
        if value is None:
            return ""

        return f"{value:.2f}"

    def _format_datetime(self, value: datetime | None) -> str:
        """Format a datetime value for table display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _format_numero_versao(value: int) -> str:
        """Format a version number for table display."""
        return f"{value:02d}"
