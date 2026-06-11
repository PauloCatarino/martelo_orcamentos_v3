"""Budget items tab page."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.item_types import get_item_type_label
from app.domain.producao_types import (
    TIPO_PRODUCAO_SERIE,
    TIPO_PRODUCAO_STD,
    tipo_producao_efetivo,
)
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_service import (
    CriarOrcamentoItemSimplesData,
    EditarOrcamentoItemSimplesData,
    OrcamentoItemService,
)
from app.services.orcamento_item_modulo_service import OrcamentoItemModuloService
from app.ui.dialogs.novo_item_dialog import NovoItemDialog, NovoItemDialogData
from app.ui.pages.orcamento_item_modulos_page import OrcamentoItemModulosPage
from app.ui.widgets.breadcrumb import Breadcrumb
from app.utils.formatters import format_currency, format_mm, format_quantity


class OrcamentoItemsPage(QWidget):
    """Read-only items page for one budget version."""

    TABLE_HEADERS = [
        "Ordem",
        "C\u00f3digo",
        "Tipo",
        "M\u00f3dulos",
        "Item",
        "Descri\u00e7\u00e3o",
        "Altura",
        "Largura",
        "Profundidade",
        "Quantidade",
        "Unidade",
        "Produ\u00e7\u00e3o",
        "Pre\u00e7o Unit\u00e1rio",
        "Pre\u00e7o Total",
    ]

    PRODUCAO_DEFAULT_TOOLTIP = (
        "Padr\u00e3o de produ\u00e7\u00e3o da vers\u00e3o (STD ou SERIE): aplica-se a todos os items "
        "sem exce\u00e7\u00e3o pr\u00f3pria. Mudar recalcula os custos de produ\u00e7\u00e3o de todos os "
        "items do or\u00e7amento."
    )
    PRODUCAO_ITEM_TOOLTIP = (
        "Produ\u00e7\u00e3o deste item: Padr\u00e3o segue o padr\u00e3o da vers\u00e3o; STD/SERIE define "
        "uma exce\u00e7\u00e3o s\u00f3 para este item. Mudar recalcula s\u00f3 este item."
    )

    def __init__(
        self,
        orcamento_versao_id: int,
        orcamento_codigo: str | None = None,
        on_items_changed: Callable[[], None] | None = None,
        on_open_item_custeio: Callable[[OrcamentoItemResumo], None] | None = None,
    ) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id
        self.orcamento_codigo = orcamento_codigo
        self.on_items_changed = on_items_changed
        self.on_open_item_custeio = on_open_item_custeio
        self._items_by_row: dict[int, OrcamentoItemResumo] = {}
        self._modulos_page: OrcamentoItemModulosPage | None = None
        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())

        title = QLabel("Items do or\u00e7amento")
        title.setObjectName("orcamentoItemsTitle")

        self.new_button = QPushButton("Novo Item")
        self.new_button.clicked.connect(self.abrir_novo_item)

        self.edit_button = QPushButton("Editar Item")
        self.edit_button.clicked.connect(self.editar_item_selecionado)

        self.modules_button = QPushButton("M\u00f3dulos")
        self.modules_button.clicked.connect(self.abrir_modulos_item_selecionado)

        self.item_custeio_button = QPushButton("Custeio do Item")
        self.item_custeio_button.clicked.connect(self.abrir_custeio_item_selecionado)

        self.remove_button = QPushButton("Remover Item")
        self.remove_button.clicked.connect(self.remover_item_selecionado)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_items)

        self._tipo_producao_default = TIPO_PRODUCAO_STD
        self._carregando_producao = False

        self.producao_title_label = QLabel("Produção:")
        self.producao_title_label.setToolTip(self.PRODUCAO_DEFAULT_TOOLTIP)

        self.producao_std_button = QPushButton(TIPO_PRODUCAO_STD)
        self.producao_serie_button = QPushButton(TIPO_PRODUCAO_SERIE)
        for botao in (self.producao_std_button, self.producao_serie_button):
            botao.setCheckable(True)
            botao.setToolTip(self.PRODUCAO_DEFAULT_TOOLTIP)

        self.producao_group = QButtonGroup(self)
        self.producao_group.setExclusive(True)
        self.producao_group.addButton(self.producao_std_button)
        self.producao_group.addButton(self.producao_serie_button)
        self.producao_std_button.setChecked(True)
        self.producao_std_button.clicked.connect(
            lambda: self._on_producao_default_clicked(TIPO_PRODUCAO_STD)
        )
        self.producao_serie_button.clicked.connect(
            lambda: self._on_producao_default_clicked(TIPO_PRODUCAO_SERIE)
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.modules_button)
        actions_layout.addWidget(self.item_custeio_button)
        actions_layout.addWidget(self.remove_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addSpacing(16)
        actions_layout.addWidget(self.producao_title_label)
        actions_layout.addWidget(self.producao_std_button)
        actions_layout.addWidget(self.producao_serie_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemsStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        header_producao = self.table.horizontalHeaderItem(
            self.TABLE_HEADERS.index("Produção")
        )
        if header_producao is not None:
            header_producao.setToolTip(self.PRODUCAO_ITEM_TOOLTIP)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)

        self.items_list_widget = QWidget()
        items_layout = QVBoxLayout()
        items_layout.setContentsMargins(12, 12, 12, 12)
        items_layout.setSpacing(10)
        items_layout.addWidget(self.breadcrumb)
        items_layout.addWidget(title)
        items_layout.addLayout(actions_layout)
        items_layout.addWidget(self.status_label)
        items_layout.addWidget(self.table, stretch=1)
        self.items_list_widget.setLayout(items_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.items_list_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.setLayout(layout)
        self.carregar_items()

    def carregar_items(self) -> None:
        """Load budget items into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                items = item_service.list_items_by_versao(self.orcamento_versao_id)
                tipo_default = item_service.get_tipo_producao_default(
                    self.orcamento_versao_id
                )
                module_counts = OrcamentoItemModuloService(session).get_counts_by_item_ids(
                    [item.id for item in items]
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os items.")
            return

        self._tipo_producao_default = tipo_default
        self._atualizar_seletor_producao()
        self._preencher_tabela(items, module_counts)

        if not items:
            self.status_label.setText("Sem items para mostrar.")

    def _atualizar_seletor_producao(self) -> None:
        """Reflect the version's production default on the STD/SERIE toggle."""
        self._carregando_producao = True
        try:
            serie = self._tipo_producao_default == TIPO_PRODUCAO_SERIE
            self.producao_serie_button.setChecked(serie)
            self.producao_std_button.setChecked(not serie)
        finally:
            self._carregando_producao = False

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
                        tipo_item=form_data.tipo_item,
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

        self.carregar_items()
        self.status_label.setText("Item criado.")
        self._notify_items_changed()

    def editar_item_selecionado(self) -> None:
        """Edit the currently selected item."""
        item_id = self._get_selected_item_id()
        if item_id is None:
            self.status_label.setText("Selecione um item para editar.")
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoItemService(session)
                item = service.get_item_by_id(item_id)
                if item is None:
                    self.status_label.setText("Item selecionado nao foi encontrado.")
                    return

                dialog = NovoItemDialog(self, item_data=self._dialog_data_from_item(item))
                if not dialog.exec():
                    return

                form_data = dialog.get_data()
                service.editar_item_simples(
                    item_id,
                    EditarOrcamentoItemSimplesData(
                        codigo=form_data.codigo,
                        tipo_item=form_data.tipo_item,
                        item=form_data.item,
                        descricao=form_data.descricao,
                        altura=form_data.altura,
                        largura=form_data.largura,
                        profundidade=form_data.profundidade,
                        quantidade=form_data.quantidade,
                        unidade=form_data.unidade,
                        preco_unitario=form_data.preco_unitario,
                    ),
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel editar o item.")
            return

        self.carregar_items()
        self.status_label.setText("Item atualizado.")
        self._notify_items_changed()

    def remover_item_selecionado(self) -> None:
        """Remove the currently selected item after confirmation."""
        item_id = self._get_selected_item_id()
        if item_id is None:
            self.status_label.setText("Selecione um item para remover.")
            return

        response = QMessageBox.question(
            self,
            "Remover Item",
            "Tem a certeza que pretende remover este item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                deleted = OrcamentoItemService(session).remover_item(item_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel remover o item.")
            return

        if not deleted:
            self.status_label.setText("Item selecionado nao foi encontrado.")
            return

        self.carregar_items()
        self.status_label.setText("Item removido.")
        self._notify_items_changed()

    def abrir_modulos_item_selecionado(self) -> None:
        """Open modules for the selected item inside this tab."""
        item = self._get_selected_item()
        if item is None:
            self.status_label.setText("Selecione um item para gerir modulos.")
            return

        self.status_label.clear()
        self._show_modulos_page(item)

    def abrir_custeio_item_selecionado(self) -> None:
        """Open costing for the selected item through the optional callback."""
        item = self._get_selected_item()
        if item is None:
            self.status_label.setText("Selecione um item para abrir o custeio.")
            return

        if self.on_open_item_custeio is None:
            self.status_label.setText("Custeio do item indisponivel.")
            return

        self.status_label.clear()
        self.on_open_item_custeio(item)

    def _show_modulos_page(self, item: OrcamentoItemResumo) -> None:
        """Replace the list view with the selected item's modules page."""
        if self._modulos_page is not None:
            self.stack.removeWidget(self._modulos_page)
            self._modulos_page.deleteLater()

        self._modulos_page = OrcamentoItemModulosPage(
            item.id,
            item_label=self._format_item_label(item),
            orcamento_codigo=self.orcamento_codigo,
            on_back=self._voltar_aos_items,
        )
        self.stack.addWidget(self._modulos_page)
        self.stack.setCurrentWidget(self._modulos_page)

    def _voltar_aos_items(self) -> None:
        """Return to the items table and refresh module counts."""
        self.stack.setCurrentWidget(self.items_list_widget)
        self.carregar_items()

    def _preencher_tabela(
        self,
        items: list[OrcamentoItemResumo],
        module_counts: dict[int, int] | None = None,
    ) -> None:
        """Fill the items table."""
        module_counts = module_counts or {}
        self._items_by_row = {}
        self.table.setRowCount(len(items))

        for row_index, item in enumerate(items):
            self._items_by_row[row_index] = item
            producao_efetiva = tipo_producao_efetivo(
                item.tipo_producao, self._tipo_producao_default
            )
            values = [
                str(item.ordem),
                item.codigo or "",
                get_item_type_label(item.tipo_item),
                self._format_modulos_count(module_counts.get(item.id, 0)),
                item.item,
                item.descricao or "",
                format_mm(item.altura),
                format_mm(item.largura),
                format_mm(item.profundidade),
                format_quantity(item.quantidade),
                item.unidade or "",
                producao_efetiva,
                format_currency(item.preco_unitario),
                format_currency(item.preco_total),
            ]

            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column_index == 0:
                    table_item.setData(Qt.ItemDataRole.UserRole, item.id)
                self.table.setItem(row_index, column_index, table_item)

            self.table.setCellWidget(
                row_index,
                self.TABLE_HEADERS.index("Produção"),
                self._criar_combo_producao(item),
            )

    def _criar_combo_producao(self, item: OrcamentoItemResumo) -> QComboBox:
        """Build the per-item production combo (Padrão / STD / SERIE)."""
        combo = QComboBox()
        combo.setToolTip(self.PRODUCAO_ITEM_TOOLTIP)
        combo.addItem(f"Padrão ({self._tipo_producao_default})", None)
        combo.addItem(TIPO_PRODUCAO_STD, TIPO_PRODUCAO_STD)
        combo.addItem(TIPO_PRODUCAO_SERIE, TIPO_PRODUCAO_SERIE)

        if item.tipo_producao == TIPO_PRODUCAO_STD:
            combo.setCurrentIndex(1)
        elif item.tipo_producao == TIPO_PRODUCAO_SERIE:
            combo.setCurrentIndex(2)
        else:
            combo.setCurrentIndex(0)

        combo.currentIndexChanged.connect(
            lambda _indice, item_id=item.id, c=combo: self._on_producao_item_changed(
                item_id, c
            )
        )
        return combo

    def _on_producao_default_clicked(self, tipo_producao: str) -> None:
        """Save the version's production default and recompute every item."""
        if self._carregando_producao:
            return
        if tipo_producao == self._tipo_producao_default:
            return

        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                item_service.definir_tipo_producao_default(
                    self.orcamento_versao_id, tipo_producao
                )
                items = item_service.list_items_by_versao(self.orcamento_versao_id)
                for item in items:
                    self._recalcular_custeio_do_item(session, item.id)
                item_service.recalcular_total_versao(self.orcamento_versao_id)
                session.commit()
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível mudar o padrão de produção.")
            self.carregar_items()
            return

        self.carregar_items()
        self.status_label.setText(
            f"Padrão de produção: {tipo_producao}. Custos de produção recalculados "
            f"em {len(items)} item(s); as exceções por item foram respeitadas."
        )
        self._notify_items_changed()

    def _on_producao_item_changed(self, item_id: int, combo: QComboBox) -> None:
        """Save one item's production exception and recompute only that item."""
        tipo_producao = combo.currentData()

        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                item_service.definir_tipo_producao_item(item_id, tipo_producao)
                self._recalcular_custeio_do_item(session, item_id)
                item_service.recalcular_total_versao(self.orcamento_versao_id)
                session.commit()
            mensagem = "Produção do item atualizada (custos recalculados)."
        except (SQLAlchemyError, ValueError):
            mensagem = "Não foi possível mudar a produção do item."

        # Reload outside the combo signal (the reload destroys the combo itself).
        def _recarregar() -> None:
            self.carregar_items()
            self.status_label.setText(mensagem)
            self._notify_items_changed()

        QTimer.singleShot(0, _recarregar)

    def _recalcular_custeio_do_item(self, session, item_id: int) -> None:
        """Run the costing Atualizar pipeline for one item (same as the page)."""
        service = OrcamentoItemCusteioLinhaService(session)
        service.recalcular_medidas_do_item(item_id)
        service.aplicar_acabamentos_do_item(item_id)
        service.recalcular_areas_acabamento_do_item(item_id)
        service.recalcular_orlas_do_item(item_id)
        service.recalcular_custo_materia_prima_do_item(item_id)
        service.recalcular_custos_ferragens_do_item(item_id)
        service.recalcular_custos_ml_do_item(item_id)
        service.recalcular_custo_acabamento_do_item(item_id)
        service.aplicar_operacoes_do_item(item_id)
        service.recalcular_custos_producao_do_item(item_id)
        service.recalcular_custo_total_do_item(item_id)

    def _get_selected_item_id(self) -> int | None:
        """Return the selected item id from the table."""
        item = self._get_selected_item()
        if item is not None:
            return item.id

        row = self.table.currentRow()
        if row < 0:
            return None

        table_item = self.table.item(row, 0)
        if table_item is None:
            return None

        item_id = table_item.data(Qt.ItemDataRole.UserRole)
        return int(item_id) if item_id is not None else None

    def _get_selected_item(self) -> OrcamentoItemResumo | None:
        """Return the selected item read model from the table."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._items_by_row.get(row)

    def _handle_row_double_click(self, row: int, _column: int) -> None:
        """Edit an item when the user double-clicks its row."""
        self.table.selectRow(row)
        self.editar_item_selecionado()

    def _notify_items_changed(self) -> None:
        """Notify the parent page that item data changed."""
        if self.on_items_changed is not None:
            self.on_items_changed()

    @staticmethod
    def _format_item_label(item: OrcamentoItemResumo) -> str:
        """Return a short label for the selected item."""
        parts = [item.item.strip()]
        if item.codigo:
            parts.append(item.codigo.strip())

        label = " - ".join(part for part in parts if part)
        return label or f"Item {item.id}"

    @staticmethod
    def _format_modulos_count(count: int) -> str:
        """Return a friendly module count."""
        if count == 1:
            return "1 m\u00f3dulo"

        return f"{count} m\u00f3dulos"

    def _build_breadcrumb_items(self) -> list[str]:
        """Return breadcrumb items for the items page."""
        items: list[str] = []
        if self.orcamento_codigo:
            items.append(f"Or\u00e7amento {self.orcamento_codigo}")

        items.append("Items")
        return items

    def _dialog_data_from_item(self, item: OrcamentoItemResumo) -> NovoItemDialogData:
        """Convert an item read model into dialog data."""
        return NovoItemDialogData(
            codigo=item.codigo,
            item=item.item,
            descricao=item.descricao,
            altura=item.altura,
            largura=item.largura,
            profundidade=item.profundidade,
            quantidade=item.quantidade,
            unidade=item.unidade or "un",
            preco_unitario=item.preco_unitario or Decimal("0"),
            tipo_item=item.tipo_item,
        )
