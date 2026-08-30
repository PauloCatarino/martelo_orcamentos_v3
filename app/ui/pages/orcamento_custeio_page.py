"""Budget costing lines page (read-only listing)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
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
from app.services.orcamento_suplemento_service import (
    OrcamentoSuplementoService,
    SuplementoPlacaResumo,
)
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.ui import tema
from app.ui.dialogs.orcamento_suplementos_dialog import OrcamentoSuplementosDialog
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
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
        self.refresh_button.setToolTip("Recalcular e atualizar o custeio do orçamento")
        self.refresh_button.clicked.connect(lambda: self.carregar(forcar=True))

        self.suplementos_button = QPushButton("Adicionar Suplementos...")
        self.suplementos_button.setToolTip(
            "Gerir suplementos de placas não stock, uma vez por referência e orçamento"
        )
        self.suplementos_button.clicked.connect(self._abrir_suplementos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.suplementos_button)
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

        self.suplementos_label = QLabel("Suplementos de placas não stock")
        self.suplementos_label.setStyleSheet("font-weight: bold;")
        self.suplementos_table = QTableWidget(0, 10)
        self.suplementos_table.setHorizontalHeaderLabels(
            [
                "Ref. placa",
                "Descrição",
                "Esp.",
                "Fonte",
                "Valor base",
                "Valor local",
                "Qt",
                "Editado localmente",
                "Notas para o cliente",
                "Itens",
            ]
        )
        self.suplementos_table.verticalHeader().setVisible(False)
        self.suplementos_table.setAlternatingRowColors(True)
        self.suplementos_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.suplementos_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        larguras_suplementos = (90, 310, 55, 75, 90, 90, 55, 130, 360, 55)
        for coluna, largura in enumerate(larguras_suplementos):
            self.suplementos_table.setColumnWidth(coluna, largura)
        ligar_persistencia_larguras(
            self.suplementos_table,
            "orcamento_custeio_suplementos",
            guardar_ordem=True,
        )
        self.suplementos_table.setMaximumHeight(190)
        self.suplementos_total_label = QLabel("")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        ligar_persistencia_larguras(self.table, "orcamento_custeio")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.banner)
        layout.addWidget(self.status_label)
        layout.addWidget(self.suplementos_label)
        layout.addWidget(self.suplementos_table)
        layout.addWidget(self.suplementos_total_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Auto-refresh whenever this tab becomes visible (phase 8W.1.2)."""
        super().showEvent(event)
        self.carregar()

    def carregar(self, forcar: bool = False) -> None:
        """Load the costing lines, recomputing only when the costing changed.

        A listagem lê os custos gravados nas linhas. Recalcular a pipeline
        completa a cada visita a este separador custava ~27 s no orçamento
        260868, quase sempre para reescrever exatamente os mesmos números: agora
        só recalcula quando o retrato do custeio mudou desde a última passagem
        (ou quando o botão "Atualizar" o pede à mão).
        """
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                relatorio = RelatorioConsumosService(session)
                if forcar:
                    relatorio.recalcular_versao(self.orcamento_versao_id)
                else:
                    relatorio.recalcular_versao_se_necessario(
                        self.orcamento_versao_id
                    )
                items = OrcamentoItemService(session).list_items_by_versao(
                    self.orcamento_versao_id
                )
                linhas = OrcamentoItemCusteioLinhaService(session).listar_linhas_da_versao(
                    self.orcamento_versao_id
                )
                suplementos = OrcamentoSuplementoService(session).listar(
                    self.orcamento_versao_id
                )
                item_service = OrcamentoItemService(session)
                custo_suplementos = item_service.get_custo_suplementos_versao(
                    self.orcamento_versao_id
                )
                preco_suplementos = item_service.get_preco_suplementos_versao(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as linhas de custeio.")
            return

        item_labels = {item.id: self._item_label(item) for item in items}
        self._preencher_suplementos(
            suplementos, custo_suplementos, preco_suplementos
        )
        self._preencher(linhas, item_labels)
        self.banner.setText(
            f"Atualizado às {datetime.now().strftime('%H:%M:%S')}"
        )

    def _abrir_suplementos(self) -> None:
        """Open the budget-level editor and persist all selected references."""
        try:
            with SessionLocal() as session:
                suplementos = OrcamentoSuplementoService(session).listar(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError:
            QMessageBox.critical(
                self,
                "Suplementos",
                "Não foi possível carregar as referências de placas.",
            )
            return

        dialog = OrcamentoSuplementosDialog(suplementos, self)
        if not dialog.exec():
            return
        try:
            with SessionLocal() as session:
                ativos = OrcamentoSuplementoService(session).guardar(
                    self.orcamento_versao_id, dialog.dados()
                )
        except (SQLAlchemyError, ValueError) as erro:
            QMessageBox.critical(
                self,
                "Suplementos",
                f"Não foi possível guardar os suplementos:\n{erro}",
            )
            return
        self.carregar()
        self.status_label.setText(
            f"Suplementos guardados: {ativos} referência(s) ativa(s)."
        )

    def _preencher_suplementos(
        self,
        suplementos: list[SuplementoPlacaResumo],
        custo_total,
        preco_total,
    ) -> None:
        ativos = [row for row in suplementos if row.ativo]
        self.suplementos_table.setRowCount(len(ativos))
        for row_index, suplemento in enumerate(ativos):
            values = [
                suplemento.ref_le,
                suplemento.descricao,
                format_quantity(suplemento.esp),
                suplemento.suplemento_ref_le,
                format_currency(suplemento.valor_base),
                format_currency(suplemento.valor_local),
                format_quantity(suplemento.quantidade),
                self._format_bool(suplemento.editado_localmente),
                suplemento.nota_cliente,
                str(suplemento.numero_itens),
            ]
            for column_index, value in enumerate(values):
                self.suplementos_table.setItem(
                    row_index, column_index, QTableWidgetItem(value)
                )
        self.suplementos_table.setVisible(bool(ativos))
        if ativos:
            self.suplementos_total_label.setText(
                f"Valor global fixo dos suplementos: {format_currency(preco_total)}"
                "    |    Sem margens adicionais"
            )
        else:
            self.suplementos_total_label.setText(
                "Sem suplementos aplicados a esta versão do orçamento."
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
