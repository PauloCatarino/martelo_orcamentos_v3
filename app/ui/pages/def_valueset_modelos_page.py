"""Page for managing ValueSet models (library)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_valueset_modelo_service import (
    CriarDefValuesetModeloData,
    DefValuesetModeloService,
    EditarDefValuesetModeloData,
)
from app.services.permission_service import is_admin
from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.estilo_tabela_orcamentos import configurar_tabela_orcamentos
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

    def __init__(self, on_back=None) -> None:
        super().__init__()

        self.on_back = on_back
        # {tabela: {row: resumo}} for the two tabs (own / global).
        self._por_linha: dict[QTableWidget, dict[int, DefValuesetModeloResumo]] = {}
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
        self.mostrar_inativos_check = QCheckBox("Mostrar inativos")
        self.mostrar_inativos_check.stateChanged.connect(
            lambda _=0: self.carregar_modelos()
        )
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.mostrar_inativos_check)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetModelosStatus")

        self.tabela_utilizador = self._criar_tabela("valueset_modelos_utilizador")
        self.tabela_globais = self._criar_tabela("valueset_modelos_globais")
        self.tabs = QTabWidget()
        self.tabs.addTab(self.tabela_utilizador, "Utilizador")
        self.tabs.addTab(self.tabela_globais, "Global")

        self.list_widget = QWidget()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)
        list_layout.addWidget(self.cabecalho)
        list_layout.addLayout(actions_layout)
        list_layout.addWidget(self.status_label)
        list_layout.addWidget(self.tabs, stretch=1)
        self.list_widget.setLayout(list_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.list_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.setLayout(layout)
        self.carregar_modelos()

    def _criar_tabela(self, chave_larguras: str) -> QTableWidget:
        """Build one models table configured like the rest of the app."""
        tabela = QTableWidget(0, len(self.TABLE_HEADERS))
        tabela.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        tabela.verticalHeader().setVisible(False)
        tabela.setAlternatingRowColors(True)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tabela.horizontalHeader().setStretchLastSection(False)
        configurar_tabela_orcamentos(tabela, compacta=True)
        tabela.cellDoubleClicked.connect(
            lambda row, _col, alvo=tabela: self._handle_double_click(alvo, row)
        )
        ligar_persistencia_larguras(tabela, chave_larguras)
        return tabela

    def carregar_modelos(self) -> None:
        """Load ValueSet models into the two tabs (own / global)."""
        self.status_label.clear()

        user_id = self._current_user_id()
        admin = is_admin(app_session.current_user)
        try:
            with SessionLocal() as session:
                utilizador, globais = DefValuesetModeloService(
                    session
                ).listar_modelos_para_separadores(
                    user_id, is_admin=admin, incluir_inativos=True
                )
        except SQLAlchemyError as error:
            self.tabela_utilizador.setRowCount(0)
            self.tabela_globais.setRowCount(0)
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar os modelos ValueSet.", error)
            )
            return

        if not self.mostrar_inativos_check.isChecked():
            utilizador = [modelo for modelo in utilizador if modelo.ativo]
            globais = [modelo for modelo in globais if modelo.ativo]

        self._preencher_tabela(self.tabela_utilizador, utilizador)
        self._preencher_tabela(self.tabela_globais, globais)

        if not utilizador and not globais:
            self.status_label.setText("Sem modelos ValueSet para mostrar.")

    def _preencher_tabela(
        self, tabela: QTableWidget, modelos: list[DefValuesetModeloResumo]
    ) -> None:
        """Fill one table with ValueSet models."""
        por_linha: dict[int, DefValuesetModeloResumo] = {}
        tabela.setRowCount(len(modelos))

        for row_index, modelo in enumerate(modelos):
            por_linha[row_index] = modelo
            values = [
                modelo.codigo,
                modelo.nome,
                modelo.tipo or "",
                modelo.ambito,
                self._dono_display(modelo),
                self._format_bool(modelo.ativo),
            ]
            for column_index, value in enumerate(values):
                tabela.setItem(row_index, column_index, QTableWidgetItem(value))

        self._por_linha[tabela] = por_linha

    def _dono_display(self, modelo: DefValuesetModeloResumo) -> str:
        """Owner label: GLOBAL for shared models, else the owner username."""
        if self._e_global(modelo):
            return "GLOBAL"
        return modelo.owner_username or ""

    @staticmethod
    def _e_global(modelo: DefValuesetModeloResumo) -> bool:
        ambito = (modelo.ambito or "").strip().upper()
        return ambito == "GLOBAL" or bool(modelo.visivel_para_todos)

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
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar o modelo.", error)
                )
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
                            user_id=modelo.user_id,
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
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar o modelo.", error)
                )
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
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar o modelo.", error)
                )
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
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar o estado do modelo.", error)
            )
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

    def abrir_modelo_por_id(self, modelo_id: int) -> None:
        """Reload and open one ValueSet model from the audit page."""
        self.carregar_modelos()
        for tabela in (self.tabela_utilizador, self.tabela_globais):
            for row, modelo in self._por_linha.get(tabela, {}).items():
                if modelo.id == modelo_id:
                    self.tabs.setCurrentWidget(tabela)
                    tabela.selectRow(row)
                    self._show_detail_page(modelo)
                    return
        self.status_label.setText("O modelo ValueSet indicado já não existe.")

    def _show_detail_page(self, modelo: DefValuesetModeloResumo) -> None:
        """Replace the list with the model detail page."""
        if self._detail_page is not None:
            self.stack.removeWidget(self._detail_page)
            self._detail_page.deleteLater()

        self._detail_page = DefValuesetModeloDetailPage(
            modelo,
            on_back=self._voltar_a_lista,
            on_modelo_duplicado=self._abrir_modelo_duplicado,
        )
        self.stack.addWidget(self._detail_page)
        self.stack.setCurrentWidget(self._detail_page)

    def _abrir_modelo_duplicado(
        self, modelo: DefValuesetModeloResumo, mensagem: str
    ) -> None:
        """Open the newly duplicated model detail."""
        self._show_detail_page(modelo)
        if self._detail_page is not None:
            self._detail_page.status_label.setText(mensagem)

    def _voltar_a_lista(self) -> None:
        """Return to the model list."""
        self.stack.setCurrentWidget(self.list_widget)
        self.carregar_modelos()

    def _get_selected_modelo(self) -> DefValuesetModeloResumo | None:
        """Return the selected ValueSet model from the active tab."""
        tabela = self.tabs.currentWidget()
        if not isinstance(tabela, QTableWidget):
            return None
        row = tabela.currentRow()
        if row < 0:
            return None
        return self._por_linha.get(tabela, {}).get(row)

    def _criar_modelo_data_from_form_data(self, form_data) -> CriarDefValuesetModeloData:
        """Build create-service data from dialog data."""
        return CriarDefValuesetModeloData(
            codigo=form_data.codigo,
            nome=form_data.nome,
            descricao=form_data.descricao,
            tipo=form_data.tipo,
            ambito=form_data.ambito,
            user_id=self._current_user_id(),
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
        """Select one model row by code across both tabs."""
        for tabela in (self.tabela_utilizador, self.tabela_globais):
            for row_index, modelo in self._por_linha.get(tabela, {}).items():
                if modelo.codigo == codigo:
                    self.tabs.setCurrentWidget(tabela)
                    tabela.selectRow(row_index)
                    return

    def _handle_double_click(self, tabela: QTableWidget, row: int) -> None:
        """Open the model detail when the user double-clicks its row."""
        self.tabs.setCurrentWidget(tabela)
        tabela.selectRow(row)
        self.abrir_modelo_selecionado()

    @staticmethod
    def _current_user_id() -> int | None:
        """Return the logged-in user's id, or None."""
        user = app_session.current_user
        return user.id if user is not None else None

    def _error_message(self, error: ValueError) -> str:
        """Map a service ValueError to a friendly message."""
        if "codigo ja existe" in str(error):
            return "Já existe um modelo com esse código."

        return "Não foi possível guardar o modelo."

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
