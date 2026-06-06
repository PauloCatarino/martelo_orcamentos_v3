"""Budget costing lines page (read-only listing)."""

from __future__ import annotations

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
    CriarLinhaCusteioData,
    EditarLinhaCusteioData,
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_service import OrcamentoItemService
from app.ui.dialogs.custeio_linha_manual_dialog import CusteioLinhaManualDialog
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
        self._linhas_by_row: dict[int, OrcamentoItemCusteioLinhaResumo] = {}

        info = QLabel("Linhas de custeio dos items deste orçamento.")
        info.setObjectName("orcamentoCusteioInfo")
        info.setWordWrap(True)

        self.nova_linha_button = QPushButton("Nova Linha Manual")
        self.nova_linha_button.clicked.connect(self.abrir_nova_linha)
        self.editar_linha_button = QPushButton("Editar Linha")
        self.editar_linha_button.clicked.connect(self.abrir_editar_linha)
        self.toggle_linha_button = QPushButton("Ativar/Desativar")
        self.toggle_linha_button.clicked.connect(self.alternar_linha_ativa)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.nova_linha_button)
        actions_layout.addWidget(self.editar_linha_button)
        actions_layout.addWidget(self.toggle_linha_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoCusteioStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Load the costing lines of the budget version."""
        self.status_label.clear()

        try:
            with SessionLocal() as session:
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

    def _preencher(
        self,
        linhas: list[OrcamentoItemCusteioLinhaResumo],
        item_labels: dict[int, str],
    ) -> None:
        """Fill the costing lines table."""
        self._linhas_by_row = {}
        self.table.setRowCount(len(linhas))

        for row_index, linha in enumerate(linhas):
            self._linhas_by_row[row_index] = linha
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

    def _get_selected_linha(self) -> OrcamentoItemCusteioLinhaResumo | None:
        """Return the selected cost line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a cost line when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_editar_linha()

    def _carregar_items_disponiveis(self) -> list[OrcamentoItemResumo] | None:
        """Load the items of the budget version for the dialog."""
        try:
            with SessionLocal() as session:
                return OrcamentoItemService(session).list_items_by_versao(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os items.")
            return None

    def abrir_nova_linha(self) -> None:
        """Open the dialog to create a new manual cost line."""
        items = self._carregar_items_disponiveis()
        if items is None:
            return

        if not items:
            self.status_label.setText(
                "Não existem items neste orçamento. "
                "Crie um item antes de adicionar linhas de custeio."
            )
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    OrcamentoItemCusteioLinhaService(session).criar_linha_manual(
                        CriarLinhaCusteioData(
                            orcamento_item_id=form_data.orcamento_item_id,
                            descricao=form_data.descricao,
                            tipo_linha=form_data.tipo_linha,
                            codigo=form_data.codigo,
                            unidade=form_data.unidade,
                            quantidade=form_data.quantidade,
                            comp=form_data.comp,
                            larg=form_data.larg,
                            esp=form_data.esp,
                            custo_unitario=form_data.custo_unitario,
                            margem_percentagem=form_data.margem_percentagem,
                            preco_unitario=form_data.preco_unitario,
                            observacoes=form_data.observacoes,
                            override_manual=True,
                            editado_localmente=True,
                            ativo=form_data.ativo,
                        )
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível guardar a linha de custeio.")
                return False

            saved = True
            return True

        dialog = CusteioLinhaManualDialog(items, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha de custeio criada.")

    def abrir_editar_linha(self) -> None:
        """Open the dialog to edit the selected cost line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        items = self._carregar_items_disponiveis()
        if items is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    OrcamentoItemCusteioLinhaService(session).editar_linha(
                        linha.id,
                        EditarLinhaCusteioData(
                            orcamento_item_id=linha.orcamento_item_id,
                            descricao=form_data.descricao,
                            tipo_linha=form_data.tipo_linha,
                            codigo=form_data.codigo,
                            unidade=form_data.unidade,
                            quantidade=form_data.quantidade,
                            comp=form_data.comp,
                            larg=form_data.larg,
                            esp=form_data.esp,
                            custo_unitario=form_data.custo_unitario,
                            margem_percentagem=form_data.margem_percentagem,
                            preco_unitario=form_data.preco_unitario,
                            observacoes=form_data.observacoes,
                            override_manual=linha.override_manual,
                            editado_localmente=True,
                            ativo=form_data.ativo,
                        ),
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível guardar a linha de custeio.")
                return False

            saved = True
            return True

        dialog = CusteioLinhaManualDialog(items, linha=linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha de custeio atualizada.")

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected cost line after confirmation."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para ativar/desativar.")
            return

        acao = "desativar" if linha.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta linha de custeio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoItemCusteioLinhaService(session)
                if linha.ativo:
                    service.desativar_linha(linha.id)
                else:
                    service.ativar_linha(linha.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado da linha.")
            return

        estado = "desativada" if linha.ativo else "reativada"
        self.carregar()
        self.status_label.setText(f"Linha {estado}.")

    def _item_label(self, item: OrcamentoItemResumo) -> str:
        """Return a display label for one budget item."""
        if item.codigo:
            return f"{item.codigo} - {item.item}"

        return item.item

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
