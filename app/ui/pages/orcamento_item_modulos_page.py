"""Budget item modules page."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from app.repositories.orcamento_item_modulo_repository import OrcamentoItemModuloResumo
from app.services.orcamento_item_modulo_service import (
    CriarOrcamentoItemModuloSimplesData,
    EditarOrcamentoItemModuloSimplesData,
    OrcamentoItemModuloService,
)
from app.ui.dialogs.novo_modulo_dialog import NovoModuloDialog, NovoModuloDialogData
from app.ui.pages.orcamento_item_modulo_detail_page import OrcamentoItemModuloDetailPage
from app.ui.widgets.breadcrumb import Breadcrumb
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_mm, format_quantity


class OrcamentoItemModulosPage(QWidget):
    """Modules page for one budget item."""

    TABLE_HEADERS = [
        "Ordem",
        "Nome",
        "Descri\u00e7\u00e3o",
        "Altura",
        "Largura",
        "Profundidade",
        "Quantidade",
    ]

    def __init__(
        self,
        orcamento_item_id: int,
        item_label: str | None = None,
        orcamento_codigo: str | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.orcamento_item_id = orcamento_item_id
        self.item_label = item_label
        self.orcamento_codigo = orcamento_codigo
        self.on_back = on_back
        self._modulos_by_row: dict[int, OrcamentoItemModuloResumo] = {}
        self._detail_page: OrcamentoItemModuloDetailPage | None = None
        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())

        title_text = "M\u00f3dulos do item"
        if item_label:
            title_text = f"{title_text}: {item_label}"

        title = QLabel(title_text)
        title.setObjectName("orcamentoItemModulosTitle")

        self.back_button = QPushButton("Voltar aos Items")
        self.back_button.clicked.connect(self._handle_back)
        self.back_button.setVisible(on_back is not None)

        header_layout = QHBoxLayout()
        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.new_button = QPushButton("Novo M\u00f3dulo")
        self.new_button.clicked.connect(self.abrir_novo_modulo)

        self.open_button = QPushButton("Abrir M\u00f3dulo")
        self.open_button.clicked.connect(self.abrir_modulo_selecionado)

        self.edit_button = QPushButton("Editar M\u00f3dulo")
        self.edit_button.clicked.connect(self.editar_modulo_selecionado)

        self.remove_button = QPushButton("Remover M\u00f3dulo")
        self.remove_button.clicked.connect(self.remover_modulo_selecionado)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_modulos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.remove_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemModulosStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)
        ligar_persistencia_larguras(self.table, "orcamento_item_modulos")

        self.modulos_list_widget = QWidget()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(10)
        list_layout.addWidget(self.breadcrumb)
        list_layout.addLayout(header_layout)
        list_layout.addLayout(actions_layout)
        list_layout.addWidget(self.status_label)
        list_layout.addWidget(self.table, stretch=1)
        self.modulos_list_widget.setLayout(list_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.modulos_list_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.setLayout(layout)
        self.carregar_modulos()

    def carregar_modulos(self) -> None:
        """Load item modules into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                modulos = OrcamentoItemModuloService(session).listar_modulos(self.orcamento_item_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os modulos.")
            return

        self._preencher_tabela(modulos)

        if not modulos:
            self.status_label.setText("Sem modulos para mostrar.")

    def _handle_back(self) -> None:
        """Call the optional back callback."""
        if self.on_back is not None:
            self.on_back()

    def abrir_novo_modulo(self) -> None:
        """Open the new module dialog and create the module."""
        dialog = NovoModuloDialog(self)

        if not dialog.exec():
            return

        form_data = dialog.get_data()

        try:
            with SessionLocal() as session:
                OrcamentoItemModuloService(session).criar_modulo_simples(
                    CriarOrcamentoItemModuloSimplesData(
                        orcamento_item_id=self.orcamento_item_id,
                        nome=form_data.nome,
                        descricao=form_data.descricao,
                        altura=form_data.altura,
                        largura=form_data.largura,
                        profundidade=form_data.profundidade,
                        quantidade=form_data.quantidade,
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel criar o modulo.")
            return

        self.carregar_modulos()
        self.status_label.setText("Modulo criado.")

    def editar_modulo_selecionado(self) -> None:
        """Edit the currently selected module."""
        modulo_id = self._get_selected_modulo_id()
        if modulo_id is None:
            self.status_label.setText("Selecione um modulo para editar.")
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoItemModuloService(session)
                modulo = service.get_modulo_by_id(modulo_id)
                if modulo is None:
                    self.status_label.setText("Modulo selecionado nao foi encontrado.")
                    return

                dialog = NovoModuloDialog(self, modulo_data=self._dialog_data_from_modulo(modulo))
                if not dialog.exec():
                    return

                form_data = dialog.get_data()
                service.editar_modulo_simples(
                    modulo_id,
                    EditarOrcamentoItemModuloSimplesData(
                        nome=form_data.nome,
                        descricao=form_data.descricao,
                        altura=form_data.altura,
                        largura=form_data.largura,
                        profundidade=form_data.profundidade,
                        quantidade=form_data.quantidade,
                    ),
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel editar o modulo.")
            return

        self.carregar_modulos()
        self.status_label.setText("Modulo atualizado.")

    def abrir_modulo_selecionado(self) -> None:
        """Open the currently selected module detail page."""
        modulo_id = self._get_selected_modulo_id()
        if modulo_id is None:
            self.status_label.setText("Selecione um modulo para abrir.")
            return

        try:
            with SessionLocal() as session:
                modulo = OrcamentoItemModuloService(session).get_modulo_by_id(modulo_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel abrir o modulo.")
            return

        if modulo is None:
            self.status_label.setText("Modulo selecionado nao foi encontrado.")
            return

        self.status_label.clear()
        self._show_detail_page(modulo)

    def _show_detail_page(self, modulo: OrcamentoItemModuloResumo) -> None:
        """Replace the module list with the module detail page."""
        if self._detail_page is not None:
            self.stack.removeWidget(self._detail_page)
            self._detail_page.deleteLater()

        self._detail_page = OrcamentoItemModuloDetailPage(
            modulo,
            on_back=self._voltar_aos_modulos,
            orcamento_codigo=self.orcamento_codigo,
            item_label=self.item_label,
        )
        self.stack.addWidget(self._detail_page)
        self.stack.setCurrentWidget(self._detail_page)

    def _voltar_aos_modulos(self) -> None:
        """Return to the already-loaded modules table."""
        self.stack.setCurrentWidget(self.modulos_list_widget)

    def remover_modulo_selecionado(self) -> None:
        """Remove the currently selected module after confirmation."""
        modulo_id = self._get_selected_modulo_id()
        if modulo_id is None:
            self.status_label.setText("Selecione um modulo para remover.")
            return

        response = QMessageBox.question(
            self,
            "Remover M\u00f3dulo",
            "Tem a certeza que pretende remover este m\u00f3dulo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                deleted = OrcamentoItemModuloService(session).remover_modulo(modulo_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel remover o modulo.")
            return

        if not deleted:
            self.status_label.setText("Modulo selecionado nao foi encontrado.")
            return

        self.carregar_modulos()
        self.status_label.setText("Modulo removido.")

    def _preencher_tabela(self, modulos: list[OrcamentoItemModuloResumo]) -> None:
        """Fill the modules table."""
        self._modulos_by_row = {}
        self.table.setRowCount(len(modulos))

        for row_index, modulo in enumerate(modulos):
            self._modulos_by_row[row_index] = modulo
            values = [
                str(modulo.ordem),
                modulo.nome,
                modulo.descricao or "",
                format_mm(modulo.altura),
                format_mm(modulo.largura),
                format_mm(modulo.profundidade),
                format_quantity(modulo.quantidade),
            ]

            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column_index == 0:
                    table_item.setData(Qt.ItemDataRole.UserRole, modulo.id)
                self.table.setItem(row_index, column_index, table_item)

    def _get_selected_modulo_id(self) -> int | None:
        """Return the selected module id from the table."""
        modulo = self._get_selected_modulo()
        if modulo is not None:
            return modulo.id

        row = self.table.currentRow()
        if row < 0:
            return None

        table_item = self.table.item(row, 0)
        if table_item is None:
            return None

        modulo_id = table_item.data(Qt.ItemDataRole.UserRole)
        return int(modulo_id) if modulo_id is not None else None

    def _get_selected_modulo(self) -> OrcamentoItemModuloResumo | None:
        """Return the selected module read model from the table."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._modulos_by_row.get(row)

    def _build_breadcrumb_items(self) -> list[str]:
        """Return breadcrumb items for the modules page."""
        items: list[str] = []
        if self.orcamento_codigo:
            items.append(f"Or\u00e7amento {self.orcamento_codigo}")
        if self.item_label:
            items.append(f"Item: {self.item_label}")

        items.append("M\u00f3dulos")
        return items

    def _handle_row_double_click(self, row: int, _column: int) -> None:
        """Open a module when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_modulo_selecionado()

    def _dialog_data_from_modulo(self, modulo: OrcamentoItemModuloResumo) -> NovoModuloDialogData:
        """Convert a module read model into dialog data."""
        return NovoModuloDialogData(
            nome=modulo.nome,
            descricao=modulo.descricao,
            altura=modulo.altura,
            largura=modulo.largura,
            profundidade=modulo.profundidade,
            quantidade=modulo.quantidade or Decimal("1"),
        )
