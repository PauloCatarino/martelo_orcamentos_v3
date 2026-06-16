"""Budget costing lines page (read-only listing)."""

from __future__ import annotations

from datetime import datetime

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
from app.domain.custeio_linha_types import get_custeio_linha_type_label
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_service import OrcamentoItemService
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.ui import tema
from app.utils.formatters import format_currency, format_quantity


class OrcamentoCusteioPage(QWidget):
    """Read-only page listing the costing lines of a budget version."""

    TABLE_HEADERS = [
        "Item",
        "Tipo",
        "Código",
        "Descrição",
        "Matéria-prima",
        "Unidade",
        "Quantidade",
        "Comp",
        "Larg",
        "Esp",
        "Área m²",
        "ML orla fina",
        "ML orla grossa",
        "Custo unitário",
        "Custo total",
        "Preço unitário",
        "Preço total",
        "Editado localmente",
        "Ativo",
    ]

    def __init__(self, orcamento_versao_id: int) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id

        info = QLabel("Linhas de custeio dos items deste orçamento.")
        info.setObjectName("orcamentoCusteioInfo")
        info.setWordWrap(True)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        # Highlighted "updated at HH:MM:SS" banner above the table (Lança Encanto).
        self.banner = QLabel("")
        self.banner.setObjectName("orcamentoCusteioBanner")
        self.banner.setStyleSheet(
            f"QLabel#orcamentoCusteioBanner {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; border: 1px solid {tema.CINZA_CASTANHO}; "
            f"border-radius: 4px; padding: 4px 8px; font-weight: bold; }}"
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoCusteioStatus")

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
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.banner)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Auto-refresh whenever this tab becomes visible (phase 8W.1.2)."""
        super().showEvent(event)
        self.carregar()

    def carregar(self) -> None:
        """Recompute the costing of every item, then load the costing lines.

        The listing reads the costs stored on the lines, so it first recomputes
        the full costing pipeline of ALL items (the SAME logic as the reports)
        and applies the version prices, to always reflect the current state.
        """
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                RelatorioConsumosService(session).recalcular_versao(
                    self.orcamento_versao_id
                )
                items = OrcamentoItemService(session).list_items_by_versao(
                    self.orcamento_versao_id
                )
                linhas = OrcamentoItemCusteioLinhaService(session).listar_linhas_da_versao(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as linhas de custeio.")
            return

        item_labels = {item.id: self._item_label(item) for item in items}
        self._preencher(linhas, item_labels)
        self.banner.setText(
            f"Atualizado às {datetime.now().strftime('%H:%M:%S')}"
        )

    def _preencher(
        self,
        linhas: list[OrcamentoItemCusteioLinhaResumo],
        item_labels: dict[int, str],
    ) -> None:
        """Fill the costing lines table."""
        self.table.setRowCount(len(linhas))

        for row_index, linha in enumerate(linhas):
            values = [
                item_labels.get(linha.orcamento_item_id, f"#{linha.orcamento_item_id}"),
                get_custeio_linha_type_label(linha.tipo_linha),
                linha.codigo or "",
                linha.descricao,
                linha.ref_materia_prima or linha.descricao_materia_prima or "",
                linha.unidade or "",
                format_quantity(linha.quantidade),
                format_quantity(linha.comp),
                format_quantity(linha.larg),
                format_quantity(linha.esp),
                format_quantity(linha.area_m2),
                format_quantity(linha.ml_orla_fina),
                format_quantity(linha.ml_orla_grossa),
                format_currency(linha.custo_unitario),
                format_currency(linha.custo_total),
                format_currency(linha.preco_unitario),
                format_currency(linha.preco_total),
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

        if not linhas:
            self.status_label.setText("Sem linhas de custeio para mostrar.")

    def _item_label(self, item: OrcamentoItemResumo) -> str:
        """Return a display label for one budget item."""
        if item.codigo:
            return f"{item.codigo} - {item.item}"

        return item.item

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
