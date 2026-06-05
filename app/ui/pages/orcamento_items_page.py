"""Budget items tab page."""

from __future__ import annotations

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

from app.db.session import SessionLocal
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.orcamento_item_service import CriarOrcamentoItemSimplesData, OrcamentoItemService
from app.ui.dialogs.novo_item_dialog import NovoItemDialog


class OrcamentoItemsPage(QWidget):
    """Read-only items page for one budget version."""

    TABLE_HEADERS = [
        "Ordem",
        "C\u00f3digo",
        "Item",
        "Descri\u00e7\u00e3o",
        "Altura",
        "Largura",
        "Profundidade",
        "Quantidade",
        "Unidade",
        "Pre\u00e7o Unit\u00e1rio",
        "Pre\u00e7o Total",
    ]

    def __init__(self, orcamento_versao_id: int) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id

        title = QLabel("Items do or\u00e7amento")
        title.setObjectName("orcamentoItemsTitle")

        self.new_button = QPushButton("Novo Item")
        self.new_button.clicked.connect(self.abrir_novo_item)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_items)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemsStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_items()

    def carregar_items(self) -> None:
        """Load budget items into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                items = OrcamentoItemService(session).list_items_by_versao(self.orcamento_versao_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os items.")
            return

        self._preencher_tabela(items)

        if not items:
            self.status_label.setText("Sem items para mostrar.")

    def abrir_novo_item(self) -> None:
        """Open the new item dialog and create the item."""
        dialog = NovoItemDialog(self)

        if not dialog.exec():
            return

        form_data = dialog.get_data()

        try:
            with SessionLocal() as session:
                OrcamentoItemService(session).criar_item_simples(
                    CriarOrcamentoItemSimplesData(
                        orcamento_versao_id=self.orcamento_versao_id,
                        codigo=form_data.codigo,
                        item=form_data.item,
                        descricao=form_data.descricao,
                        altura=form_data.altura,
                        largura=form_data.largura,
                        profundidade=form_data.profundidade,
                        quantidade=form_data.quantidade,
                        unidade=form_data.unidade,
                        preco_unitario=form_data.preco_unitario,
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel criar o item.")
            return

        self.status_label.setText("Item criado.")
        self.carregar_items()

    def _preencher_tabela(self, items: list[OrcamentoItemResumo]) -> None:
        """Fill the items table."""
        self.table.setRowCount(len(items))

        for row_index, item in enumerate(items):
            values = [
                str(item.ordem),
                item.codigo or "",
                item.item,
                item.descricao or "",
                self._format_decimal(item.altura),
                self._format_decimal(item.largura),
                self._format_decimal(item.profundidade),
                self._format_decimal(item.quantidade),
                item.unidade or "",
                self._format_decimal(item.preco_unitario),
                self._format_decimal(item.preco_total),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _format_decimal(self, value: Decimal | None) -> str:
        """Format decimal values for table display."""
        if value is None:
            return ""

        return f"{value:g}"
