"""Piece definitions page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.orla_types import format_orla_code
from app.domain.peca_natureza_types import get_peca_natureza_label
from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_componente_service import DefPecaComponenteService
from app.services.def_peca_service import (
    CriarDefPecaData,
    DefPecaService,
    EditarDefPecaData,
)
from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog
from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog
from app.ui.pages.def_peca_detail_page import DefPecaDetailPage
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class DefPecasPage(QWidget):
    """Page for listing reusable piece definitions."""

    TABLE_HEADERS = [
        "C\u00f3digo",
        "Nome",
        "Natureza",
        "Função",
        "Grupo",
        "Orlas",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self._pecas_by_row: dict[int, DefPecaResumo] = {}
        self._pecas_by_id: dict[int, DefPecaResumo] = {}
        self._tree_items_by_id: dict[int, QTreeWidgetItem] = {}
        self._detail_page: DefPecaDetailPage | None = None

        self.cabecalho = BarraCabecalho(
            "Defini\u00e7\u00f5es de Pe\u00e7as",
            ["Biblioteca de pe\u00e7as dispon\u00edveis para m\u00f3dulos, pe\u00e7as soltas e custeio"],
        )

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_pecas)

        self.new_button = QPushButton("Nova Pe\u00e7a")
        self.new_button.clicked.connect(self.abrir_nova_peca)

        self.open_button = QPushButton("Abrir Pe\u00e7a")
        self.open_button.clicked.connect(self.abrir_peca_selecionada)

        self.edit_button = QPushButton("Editar Pe\u00e7a")
        self.edit_button.clicked.connect(self.abrir_editar_peca)

        self.duplicate_button = QPushButton("Duplicar Pe\u00e7a")
        self.duplicate_button.clicked.connect(self.duplicar_peca_selecionada)

        self.toggle_ativo_button = QPushButton("Ativar/Desativar")
        self.toggle_ativo_button.clicked.connect(self.alternar_peca_ativa)

        self.toggle_vista_button = QPushButton("Ver em \u00c1rvore")
        self.toggle_vista_button.clicked.connect(self.alternar_vista)

        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(
            lambda _state=0: self.carregar_pecas()
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.duplicate_button)
        actions_layout.addWidget(self.toggle_ativo_button)
        actions_layout.addWidget(self.toggle_vista_button)
        actions_layout.addWidget(self.mostrar_inativas_check)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("defPecasStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)
        ligar_persistencia_larguras(self.table, "def_pecas")

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Pe\u00e7as")
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._handle_tree_item_double_click)

        self.lista_stack = QStackedWidget()
        self.lista_stack.addWidget(self.table)
        self.lista_stack.addWidget(self.tree)

        self.list_widget = QWidget()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)
        list_layout.addWidget(self.cabecalho)
        list_layout.addLayout(actions_layout)
        list_layout.addWidget(self.status_label)
        list_layout.addWidget(self.lista_stack, stretch=1)
        self.list_widget.setLayout(list_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.list_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.setLayout(layout)
        self.carregar_pecas()

    def carregar_pecas(self, select_codigo: str | None = None) -> None:
        """Load piece definitions into the table and tree views."""
        self.table.setRowCount(0)
        self.tree.clear()
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as definicoes de pecas.")
            return

        if not self.mostrar_inativas_check.isChecked():
            pecas = [peca for peca in pecas if peca.ativo]

        self._pecas_by_id = {peca.id: peca for peca in pecas}
        self._preencher_tabela(pecas)
        self._preencher_arvore(pecas)
        if select_codigo:
            self._select_peca_by_codigo(select_codigo)

        if not pecas:
            self.status_label.setText("Sem definicoes de pecas para mostrar.")

    def abrir_nova_peca(self) -> None:
        """Open the new piece definition dialog."""
        created_codigo: str | None = None

        def handle_save(form_data) -> bool:
            nonlocal created_codigo

            try:
                with SessionLocal() as session:
                    DefPecaService(session).criar_peca(
                        self._criar_peca_data_from_form_data(form_data)
                    )
            except IntegrityError:
                dialog.set_error("J\u00e1 existe uma pe\u00e7a com esse c\u00f3digo.")
                return False
            except (SQLAlchemyError, ValueError):
                dialog.set_error("N\u00e3o foi poss\u00edvel criar a pe\u00e7a.")
                return False

            created_codigo = form_data.codigo
            return True

        dialog = NovaDefPecaDialog(self, on_save=handle_save)

        if not dialog.exec():
            return

        if created_codigo is None:
            return

        self.carregar_pecas(select_codigo=created_codigo)
        self.status_label.setText(f"Pe\u00e7a {created_codigo} criada.")

    def abrir_editar_peca(self) -> None:
        """Open the edit dialog for the selected piece definition."""
        peca = self._get_selected_peca()
        if peca is None:
            self.status_label.setText("Selecione uma pe\u00e7a para editar.")
            return

        updated_codigo: str | None = None
        saved_as_codigo: str | None = None

        def handle_save(form_data) -> bool:
            nonlocal updated_codigo

            try:
                with SessionLocal() as session:
                    DefPecaService(session).editar_peca(
                        peca.id,
                        EditarDefPecaData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            grupo=form_data.grupo,
                            tipo_peca=form_data.tipo_peca,
                            natureza=form_data.natureza,
                            orientacao=form_data.orientacao,
                            funcao=form_data.funcao,
                            # Formulas are managed in the Regras tab; a general
                            # data edit must preserve them unchanged.
                            formula_comp=peca.formula_comp,
                            formula_larg=peca.formula_larg,
                            formula_esp=peca.formula_esp,
                            orla_c1=form_data.orla_c1,
                            orla_c2=form_data.orla_c2,
                            orla_l1=form_data.orla_l1,
                            orla_l2=form_data.orla_l2,
                            chave_valueset_material=form_data.chave_valueset_material,
                            permite_acabamento=form_data.permite_acabamento,
                            chave_valueset_acabamento_sup=form_data.chave_valueset_acabamento_sup,
                            chave_valueset_acabamento_inf=form_data.chave_valueset_acabamento_inf,
                            sem_material=form_data.sem_material,
                            ativo=form_data.ativo,
                        ),
                    )
            except IntegrityError:
                dialog.set_error("J\u00e1 existe uma pe\u00e7a com esse c\u00f3digo.")
                return False
            except (SQLAlchemyError, ValueError):
                dialog.set_error("N\u00e3o foi poss\u00edvel guardar a pe\u00e7a.")
                return False

            updated_codigo = form_data.codigo
            return True

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as_codigo

            try:
                with SessionLocal() as session:
                    resultado = DefPecaService(session).gravar_peca_como(
                        peca.id,
                        self._criar_peca_data_from_form_data(form_data),
                    )
            except IntegrityError:
                dialog.set_error("Já existe uma peça com esse código.")
                return False
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível gravar a peça como nova.")
                return False

            saved_as_codigo = resultado.codigo
            return True

        dialog = EditarDefPecaDialog(
            peca,
            self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )

        if not dialog.exec():
            return

        if updated_codigo is not None:
            self.carregar_pecas(select_codigo=updated_codigo)
            self.status_label.setText(f"Pe\u00e7a {updated_codigo} atualizada.")
        elif saved_as_codigo is not None:
            self.carregar_pecas(select_codigo=saved_as_codigo)
            self.status_label.setText(f"Pe\u00e7a {saved_as_codigo} gravada como nova.")

    def duplicar_peca_selecionada(self) -> None:
        """Duplicate the selected piece definition."""
        peca = self._get_selected_peca()
        if peca is None:
            self.status_label.setText("Selecione uma pe\u00e7a para duplicar.")
            return

        novo_codigo, ok = QInputDialog.getText(
            self,
            "Duplicar Pe\u00e7a",
            "Novo c\u00f3digo:",
            text=f"{peca.codigo}_COPIA",
        )
        novo_codigo = novo_codigo.strip()
        if not ok or not novo_codigo:
            return

        try:
            with SessionLocal() as session:
                resultado = DefPecaService(session).duplicar_peca(
                    peca.id,
                    novo_codigo,
                )
        except IntegrityError:
            self.status_label.setText("J\u00e1 existe uma pe\u00e7a com esse c\u00f3digo.")
            return
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("N\u00e3o foi poss\u00edvel duplicar a pe\u00e7a.")
            return

        self.carregar_pecas(select_codigo=resultado.codigo)
        self.status_label.setText(
            f"Pe\u00e7a {resultado.codigo} duplicada. "
            "Edite-a para ajustar o nome e outros dados."
        )

    def alternar_peca_ativa(self) -> None:
        """Toggle the active state of the selected piece after confirmation."""
        peca = self._get_selected_peca()
        if peca is None:
            self.status_label.setText("Selecione uma pe\u00e7a para ativar/desativar.")
            return

        acao = "desativar" if peca.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} a pe\u00e7a {peca.codigo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefPecaService(session)
                if peca.ativo:
                    service.desativar_peca(peca.id)
                else:
                    service.ativar_peca(peca.id)
        except SQLAlchemyError:
            self.status_label.setText("N\u00e3o foi poss\u00edvel atualizar o estado da pe\u00e7a.")
            return

        estado = "desativada" if peca.ativo else "reativada"
        self.carregar_pecas()
        self.status_label.setText(f"Pe\u00e7a {peca.codigo} {estado}.")

    def alternar_vista(self) -> None:
        """Switch between the table and tree views."""
        if self.lista_stack.currentWidget() == self.table:
            self.lista_stack.setCurrentWidget(self.tree)
            self.toggle_vista_button.setText("Ver em Lista")
        else:
            self.lista_stack.setCurrentWidget(self.table)
            self.toggle_vista_button.setText("Ver em \u00c1rvore")

    def _preencher_tabela(self, pecas: list[DefPecaResumo]) -> None:
        """Fill the table with piece definition read models."""
        self._pecas_by_row = {}
        self.table.setRowCount(len(pecas))

        for row_index, peca in enumerate(pecas):
            self._pecas_by_row[row_index] = peca
            values = [
                peca.codigo,
                peca.nome,
                get_peca_natureza_label(peca.natureza),
                peca.funcao or "",
                peca.grupo or "",
                format_orla_code(peca.orla_c1, peca.orla_c2, peca.orla_l1, peca.orla_l2),
                "Sim" if peca.ativo else "N\u00e3o",
            ]

            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column_index == 0:
                    table_item.setData(Qt.ItemDataRole.UserRole, peca.id)
                self.table.setItem(row_index, column_index, table_item)

    def _preencher_arvore(self, pecas: list[DefPecaResumo]) -> None:
        """Fill the tree view grouped by piece group."""
        self._tree_items_by_id = {}
        self.tree.clear()

        grupos: dict[str, QTreeWidgetItem] = {}
        for peca in pecas:
            grupo = (peca.grupo or "").strip().upper() or "SEM GRUPO"
            parent = grupos.get(grupo)
            if parent is None:
                parent = QTreeWidgetItem([grupo])
                self.tree.addTopLevelItem(parent)
                grupos[grupo] = parent

            codigo_orlas = format_orla_code(
                peca.orla_c1,
                peca.orla_c2,
                peca.orla_l1,
                peca.orla_l2,
            )
            texto = f"{peca.codigo} - {peca.nome} [{codigo_orlas}]"
            leaf = QTreeWidgetItem([texto])
            leaf.setData(0, Qt.ItemDataRole.UserRole, peca.id)
            parent.addChild(leaf)
            self._tree_items_by_id[peca.id] = leaf

        self.tree.expandAll()

    def abrir_peca_selecionada(self) -> None:
        """Open the currently selected piece definition detail."""
        peca = self._get_selected_peca()
        if peca is None:
            self.status_label.setText("Selecione uma pe\u00e7a para abrir.")
            return

        try:
            with SessionLocal() as session:
                componentes = DefPecaComponenteService(session).listar_componentes(peca.id)
                all_pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel abrir a definicao de peca.")
            return

        component_labels = {
            item.id: f"{item.codigo} - {item.nome}"
            for item in all_pecas
        }

        self.status_label.clear()
        self._show_detail_page(peca, componentes, component_labels)

    def abrir_peca_por_id(self, peca_id: int) -> None:
        """Open one piece detail directly from another technical page."""
        self.carregar_pecas()
        peca = self._pecas_by_id.get(peca_id)
        if peca is None:
            self.status_label.setText("A peça indicada já não existe.")
            return
        tree_item = self._tree_items_by_id.get(peca_id)
        if tree_item is not None:
            self.tree.setCurrentItem(tree_item)
        for row, atual in self._pecas_by_row.items():
            if atual.id == peca_id:
                self.table.selectRow(row)
                break
        try:
            with SessionLocal() as session:
                componentes = DefPecaComponenteService(session).listar_componentes(
                    peca.id
                )
                all_pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível abrir a definição de peça.")
            return
        labels = {item.id: f"{item.codigo} - {item.nome}" for item in all_pecas}
        self._show_detail_page(peca, componentes, labels)

    def _show_detail_page(
        self,
        peca: DefPecaResumo,
        componentes: list,
        component_labels: dict[int, str],
    ) -> None:
        """Replace the list with the piece definition detail page."""
        if self._detail_page is not None:
            self.stack.removeWidget(self._detail_page)
            self._detail_page.deleteLater()

        self._detail_page = DefPecaDetailPage(
            peca,
            componentes=componentes,
            component_labels=component_labels,
            on_back=self._voltar_a_lista,
        )
        self.stack.addWidget(self._detail_page)
        self.stack.setCurrentWidget(self._detail_page)

    def _voltar_a_lista(self) -> None:
        """Return to the already-loaded piece definition table."""
        self.stack.setCurrentWidget(self.list_widget)

    def _get_selected_peca(self) -> DefPecaResumo | None:
        """Return the selected piece definition read model."""
        if self.lista_stack.currentWidget() == self.tree:
            item = self.tree.currentItem()
            if item is None:
                return None

            peca_id = item.data(0, Qt.ItemDataRole.UserRole)
            if peca_id is None:
                return None

            return self._pecas_by_id.get(int(peca_id))

        row = self.table.currentRow()
        if row < 0:
            return None

        return self._pecas_by_row.get(row)

    def _criar_peca_data_from_form_data(self, form_data) -> CriarDefPecaData:
        """Build create-service data from piece-dialog data."""
        return CriarDefPecaData(
            codigo=form_data.codigo,
            nome=form_data.nome,
            descricao=form_data.descricao,
            grupo=form_data.grupo,
            tipo_peca=form_data.tipo_peca,
            natureza=form_data.natureza,
            orientacao=form_data.orientacao,
            funcao=form_data.funcao,
            orla_c1=form_data.orla_c1,
            orla_c2=form_data.orla_c2,
            orla_l1=form_data.orla_l1,
            orla_l2=form_data.orla_l2,
            chave_valueset_material=form_data.chave_valueset_material,
            permite_acabamento=form_data.permite_acabamento,
            chave_valueset_acabamento_sup=form_data.chave_valueset_acabamento_sup,
            chave_valueset_acabamento_inf=form_data.chave_valueset_acabamento_inf,
            sem_material=form_data.sem_material,
            ativo=form_data.ativo,
        )

    def _select_peca_by_codigo(self, codigo: str) -> None:
        """Select one table row by piece code."""
        for row_index, peca in self._pecas_by_row.items():
            if peca.codigo == codigo:
                self.table.selectRow(row_index)
                tree_item = self._tree_items_by_id.get(peca.id)
                if tree_item is not None:
                    self.tree.setCurrentItem(tree_item)
                return

    def _handle_row_double_click(self, row: int, _column: int) -> None:
        """Edit a piece definition when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_editar_peca()

    def _handle_tree_item_double_click(
        self, item: QTreeWidgetItem, _column: int
    ) -> None:
        """Edit a piece definition when the user double-clicks a tree leaf."""
        if item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        self.tree.setCurrentItem(item)
        self.abrir_editar_peca()
