"""Page for managing ValueSet models (library)."""

from __future__ import annotations

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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_valueset_modelo_service import (
    CriarDefValuesetModeloData,
    DefValuesetModeloService,
    EditarDefValuesetModeloData,
)
from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog
from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class DefValuesetModelosPage(QWidget):
    """Admin page for managing ValueSet models (library)."""

    TABLE_HEADERS = [
        "Código",
        "Nome",
        "Tipo",
        "Âmbito",
        "Dono/Utilizador",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self._modelos_by_row: dict[int, DefValuesetModeloResumo] = {}
        self._detail_page: DefValuesetModeloDetailPage | None = None

        self.cabecalho = BarraCabecalho(
            "Modelos ValueSet",
            [
                "Biblioteca de modelos de materiais, ferragens, acabamentos, sistemas "
                "e acessórios usados para preencher ValueSets de orçamentos e items."
            ],
        )

        self.new_button = QPushButton("Novo Modelo")
        self.new_button.clicked.connect(self.abrir_novo_modelo)
        self.open_button = QPushButton("Abrir Modelo")
        self.open_button.clicked.connect(self.abrir_modelo_selecionado)
        self.edit_button = QPushButton("Editar Modelo")
        self.edit_button.clicked.connect(self.abrir_editar_modelo)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_modelo_ativo)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_modelos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetModelosStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        ligar_persistencia_larguras(self.table, "valueset_modelos")

        self.list_widget = QWidget()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)
        list_layout.addWidget(self.cabecalho)
        list_layout.addLayout(actions_layout)
        list_layout.addWidget(self.status_label)
        list_layout.addWidget(self.table, stretch=1)
        self.list_widget.setLayout(list_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.list_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.setLayout(layout)
        self.carregar_modelos()

    def carregar_modelos(self) -> None:
        """Load ValueSet models into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                modelos = DefValuesetModeloService(session).listar_modelos()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os modelos ValueSet.")
            return

        self._preencher(modelos)

        if not modelos:
            self.status_label.setText("Sem modelos ValueSet para mostrar.")

    def _preencher(self, modelos: list[DefValuesetModeloResumo]) -> None:
        """Fill the table with ValueSet models."""
        self._modelos_by_row = {}
        self.table.setRowCount(len(modelos))

        for row_index, modelo in enumerate(modelos):
            self._modelos_by_row[row_index] = modelo
            values = [
                modelo.codigo,
                modelo.nome,
                modelo.tipo or "",
                modelo.ambito,
                str(modelo.user_id) if modelo.user_id else "",
                self._format_bool(modelo.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def abrir_novo_modelo(self) -> None:
        """Open the dialog to create a new ValueSet model."""
        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                self._criar_modelo_from_form_data(form_data)
            except IntegrityError:
                dialog.set_error("Já existe um modelo com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar o modelo.")
                return False

            saved = True
            return True

        dialog = DefValuesetModeloDialog(parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar_modelos()
            self.status_label.setText("Modelo ValueSet criado.")

    def abrir_editar_modelo(self) -> None:
        """Open the dialog to edit the selected ValueSet model."""
        modelo = self._get_selected_modelo()
        if modelo is None:
            self.status_label.setText("Selecione um modelo para editar.")
            return

        saved = False
        saved_as = False
        saved_as_codigo: str | None = None
        saved_as_linhas = 0

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefValuesetModeloService(session).editar_modelo(
                        modelo.id,
                        EditarDefValuesetModeloData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            tipo=form_data.tipo,
                            ambito=form_data.ambito,
                            visivel_para_todos=form_data.visivel_para_todos,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
                        ),
                    )
            except IntegrityError:
                dialog.set_error("Já existe um modelo com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar o modelo.")
                return False

            saved = True
            return True

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as, saved_as_codigo, saved_as_linhas

            try:
                with SessionLocal() as session:
                    result = DefValuesetModeloService(session).duplicar_modelo(
                        modelo.id,
                        self._criar_modelo_data_from_form_data(form_data),
                    )
            except IntegrityError:
                dialog.set_error("Já existe um modelo com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar o modelo.")
                return False

            saved_as = True
            saved_as_codigo = result.modelo.codigo
            saved_as_linhas = result.linhas_copiadas
            return True

        dialog = DefValuesetModeloDialog(
            modelo=modelo,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar_modelos()
            self.status_label.setText("Modelo ValueSet atualizado.")
        elif saved_as:
            self.carregar_modelos()
            if saved_as_codigo:
                self._select_modelo_by_codigo(saved_as_codigo)
            self.status_label.setText(
                f"Modelo gravado como novo ({saved_as_linhas} linhas copiadas)."
            )

    def alternar_modelo_ativo(self) -> None:
        """Toggle the active state of the selected model after confirmation."""
        modelo = self._get_selected_modelo()
        if modelo is None:
            self.status_label.setText("Selecione um modelo para ativar/desativar.")
            return

        acao = "desativar" if modelo.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} o modelo {modelo.codigo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefValuesetModeloService(session)
                if modelo.ativo:
                    service.desativar_modelo(modelo.id)
                else:
                    service.ativar_modelo(modelo.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado do modelo.")
            return

        estado = "desativado" if modelo.ativo else "reativado"
        self.carregar_modelos()
        self.status_label.setText(f"Modelo {estado}.")

    def abrir_modelo_selecionado(self) -> None:
        """Open the detail page for the selected model."""
        modelo = self._get_selected_modelo()
        if modelo is None:
            self.status_label.setText("Selecione um modelo para abrir.")
            return

        self.status_label.clear()
        self._show_detail_page(modelo)

    def _show_detail_page(self, modelo: DefValuesetModeloResumo) -> None:
        """Replace the list with the model detail page."""
        if self._detail_page is not None:
            self.stack.removeWidget(self._detail_page)
            self._detail_page.deleteLater()

        self._detail_page = DefValuesetModeloDetailPage(modelo, on_back=self._voltar_a_lista)
        self.stack.addWidget(self._detail_page)
        self.stack.setCurrentWidget(self._detail_page)

    def _voltar_a_lista(self) -> None:
        """Return to the model list."""
        self.stack.setCurrentWidget(self.list_widget)
        self.carregar_modelos()

    def _get_selected_modelo(self) -> DefValuesetModeloResumo | None:
        """Return the selected ValueSet model."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._modelos_by_row.get(row)

    def _criar_modelo_data_from_form_data(self, form_data) -> CriarDefValuesetModeloData:
        """Build create-service data from dialog data."""
        return CriarDefValuesetModeloData(
            codigo=form_data.codigo,
            nome=form_data.nome,
            descricao=form_data.descricao,
            tipo=form_data.tipo,
            ambito=form_data.ambito,
            visivel_para_todos=form_data.visivel_para_todos,
            observacoes=form_data.observacoes,
            ativo=form_data.ativo,
        )

    def _criar_modelo_from_form_data(self, form_data):
        """Create a ValueSet model from dialog data."""
        with SessionLocal() as session:
            return DefValuesetModeloService(session).criar_modelo(
                self._criar_modelo_data_from_form_data(form_data)
            )

    def _select_modelo_by_codigo(self, codigo: str) -> None:
        """Select one model row by code."""
        for row_index, modelo in self._modelos_by_row.items():
            if modelo.codigo == codigo:
                self.table.selectRow(row_index)
                return

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Open the model detail when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_modelo_selecionado()

    def _error_message(self, error: ValueError) -> str:
        """Map a service ValueError to a friendly message."""
        if "codigo ja existe" in str(error):
            return "Já existe um modelo com esse código."

        return "Não foi possível guardar o modelo."

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
