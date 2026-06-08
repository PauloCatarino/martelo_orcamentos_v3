"""Budget item ValueSet page (create from budget + list lines)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaResumo,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_valueset_linha_service import (
    SNAPSHOT_FIELDS,
    EditarOrcamentoItemValuesetLinhaData,
    OrcamentoItemValuesetLinhaService,
)
from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog
from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
    OrcamentoItemValuesetLinhaDialog,
)
from app.ui.dialogs.propagar_valueset_custeio_dialog import PropagarValuesetCusteioDialog
from app.utils.formatters import format_currency, format_quantity


class OrcamentoItemValuesetPage(QWidget):
    """Page listing the ValueSet lines of a budget item."""

    TABLE_HEADERS = [
        "Chave",
        "Opção",
        "Nome opção",
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Padrão",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
    ]

    def __init__(self, orcamento_item_id: int) -> None:
        super().__init__()

        self.orcamento_item_id = orcamento_item_id
        self._linhas_by_row: dict[int, OrcamentoItemValuesetLinhaResumo] = {}
        self._copied_snapshot: dict | None = None

        title = QLabel("ValueSet do Item")
        title.setObjectName("pageTitle")

        info = QLabel(
            "Materiais, ferragens, acabamentos, orlas, sistemas e acessórios "
            "definidos por defeito para este item."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.create_button = QPushButton("Criar a partir do Orçamento")
        self.create_button.clicked.connect(self.criar_do_orcamento)
        self.import_button = QPushButton("Importar Modelo")
        self.import_button.clicked.connect(self.importar_modelo)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.copy_button = QPushButton("Copiar Dados")
        self.copy_button.clicked.connect(self.copiar_dados)
        self.paste_button = QPushButton("Colar Dados")
        self.paste_button.clicked.connect(self.colar_dados)
        self.clear_button = QPushButton("Limpar Dados")
        self.clear_button.clicked.connect(self.limpar_dados)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.propagate_button = QPushButton("Atualizar Custeio")
        self.propagate_button.clicked.connect(self.atualizar_custeio_da_linha)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.create_button)
        actions_layout.addWidget(self.import_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.copy_button)
        actions_layout.addWidget(self.paste_button)
        actions_layout.addWidget(self.clear_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.propagate_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemValuesetStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._abrir_menu_contexto)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Load the ValueSet lines of the budget item."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = OrcamentoItemValuesetLinhaService(
                    session
                ).listar_linhas_ativas_do_item(self.orcamento_item_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar o ValueSet do item.")
            return

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText(
                "Sem ValueSet. Use 'Criar a partir do Orçamento' para preencher este item."
            )

    def _preencher(self, linhas: list[OrcamentoItemValuesetLinhaResumo]) -> None:
        """Fill the table with ValueSet lines."""
        self._linhas_by_row = {}
        self.table.setRowCount(len(linhas))

        for row_index, linha in enumerate(linhas):
            self._linhas_by_row[row_index] = linha
            values = [
                linha.chave,
                linha.codigo_opcao or "",
                linha.nome_opcao or "",
                linha.ref_le or "",
                linha.descricao_no_orcamento or "",
                linha.unidade or "",
                format_currency(linha.preco_tabela),
                formatar_percentagem(linha.margem_percentagem),
                formatar_percentagem(linha.desconto_percentagem),
                format_currency(linha.preco_liquido),
                formatar_percentagem(linha.desperdicio_percentagem),
                linha.tipo_materia_prima or "",
                linha.familia_materia_prima or "",
                linha.coresp_orla_0_4 or "",
                linha.coresp_orla_1_0 or "",
                format_quantity(linha.comp_mp),
                format_quantity(linha.larg_mp),
                format_quantity(linha.esp_mp),
                self._format_bool(linha.padrao),
                str(linha.ordem),
                linha.origem_modelo_codigo or linha.origem_dados or "",
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def criar_do_orcamento(self) -> None:
        """Create the item ValueSet from the budget version ValueSet."""
        try:
            with SessionLocal() as session:
                result = OrcamentoItemValuesetLinhaService(
                    session
                ).criar_a_partir_do_orcamento(self.orcamento_item_id)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText(
                "Não foi possível criar o ValueSet a partir do orçamento."
            )
            return

        self.carregar()
        self.status_label.setText(
            f"ValueSet do item criado a partir do orçamento: "
            f"{result.criadas} criadas, {result.atualizadas} atualizadas, "
            f"{result.ignoradas} ignoradas (de {result.total_origem} linhas)."
        )

    def importar_modelo(self) -> None:
        """Open the model picker and import the selected model into the item.

        When the item already has active ValueSet lines, ask the user to
        confirm replacing them before importing.
        """
        dialog = ImportarValuesetModeloDialog(parent=self)
        if not dialog.exec() or dialog.selected_modelo is None:
            return

        modelo = dialog.selected_modelo

        try:
            with SessionLocal() as session:
                tem_ativas = bool(
                    OrcamentoItemValuesetLinhaService(session).listar_linhas_ativas_do_item(
                        self.orcamento_item_id
                    )
                )
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível importar o modelo.")
            return

        if tem_ativas:
            confirm = QMessageBox.question(
                self,
                "Substituir ValueSet do Item",
                "Este item já tem linhas de ValueSet. Pretende substituir os "
                "dados atuais pelos dados do modelo selecionado?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            self._substituir_por_modelo(modelo)
        else:
            self._importar_modelo_novo(modelo)

    def _importar_modelo_novo(self, modelo) -> None:
        """Import the model into an item with no active ValueSet lines."""
        try:
            with SessionLocal() as session:
                result = OrcamentoItemValuesetLinhaService(session).importar_modelo_para_item(
                    self.orcamento_item_id, modelo.id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível importar o modelo.")
            return

        self.carregar()
        self.status_label.setText(
            f"Modelo {result.modelo_codigo} importado: "
            f"{result.criadas} criadas, {result.atualizadas} atualizadas, "
            f"{result.ignoradas} ignoradas."
        )

    def _substituir_por_modelo(self, modelo) -> None:
        """Replace the item's active ValueSet with the selected model."""
        try:
            with SessionLocal() as session:
                result = OrcamentoItemValuesetLinhaService(session).substituir_por_modelo(
                    self.orcamento_item_id, modelo.id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível importar o modelo.")
            return

        self.carregar()
        self.status_label.setText(
            f"Modelo {result.modelo_codigo} importado: "
            f"{result.desativadas} linhas anteriores desativadas, "
            f"{result.criadas + result.atualizadas} criadas."
        )

    def abrir_editar_linha(self) -> None:
        """Open the edit dialog for the selected ValueSet line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoItemValuesetLinhaService(session).editar_linha(
                        linha.id,
                        EditarOrcamentoItemValuesetLinhaData(
                            orcamento_item_id=self.orcamento_item_id,
                            chave=form_data.chave or linha.chave,
                            codigo_opcao=form_data.codigo_opcao,
                            nome_opcao=form_data.nome_opcao,
                            descricao=linha.descricao,
                            materia_prima_id=linha.materia_prima_id,
                            ref_materia_prima=form_data.ref_materia_prima,
                            descricao_materia_prima=form_data.descricao_materia_prima,
                            valor_texto=form_data.valor_texto,
                            origem=linha.origem,
                            ref_le=form_data.ref_le,
                            descricao_no_orcamento=form_data.descricao_no_orcamento,
                            preco_tabela=form_data.preco_tabela,
                            margem_percentagem=form_data.margem_percentagem,
                            desconto_percentagem=form_data.desconto_percentagem,
                            preco_liquido=form_data.preco_liquido,
                            unidade=form_data.unidade,
                            desperdicio_percentagem=form_data.desperdicio_percentagem,
                            tipo_materia_prima=form_data.tipo_materia_prima,
                            familia_materia_prima=form_data.familia_materia_prima,
                            coresp_orla_0_4=form_data.coresp_orla_0_4,
                            coresp_orla_1_0=form_data.coresp_orla_1_0,
                            comp_mp=form_data.comp_mp,
                            larg_mp=form_data.larg_mp,
                            esp_mp=form_data.esp_mp,
                            origem_dados=form_data.origem_dados,
                            herdado_do_orcamento=linha.herdado_do_orcamento,
                            editado_localmente=form_data.editado_localmente,
                            padrao=form_data.padrao,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
                        ),
                    )
            except (IntegrityError, ValueError):
                dialog.set_error("Não foi possível guardar a linha. Verifique os dados.")
                return False

            saved = True
            return True

        dialog = OrcamentoItemValuesetLinhaDialog(linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha ValueSet atualizada.")
            self._perguntar_propagar_custeio(linha.id)

    def atualizar_custeio_da_linha(self) -> None:
        """Compare and propagate the selected ValueSet line into cost lines."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        self._propagar_para_custeio(linha)

    def _perguntar_propagar_custeio(self, valueset_linha_id: int) -> None:
        """Ask whether to review the cost lines using this ValueSet key."""
        box = QMessageBox(self)
        box.setWindowTitle("Rever custeio")
        box.setText(
            "Quer rever as linhas de custeio associadas a esta chave ValueSet?"
        )
        rever_button = box.addButton("Rever linhas", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Não agora", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not rever_button:
            return

        try:
            with SessionLocal() as session:
                linha = OrcamentoItemValuesetLinhaService(session).obter_por_id(
                    valueset_linha_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar a linha ValueSet.")
            return

        if linha is not None:
            self._propagar_para_custeio(linha)

    def _propagar_para_custeio(self, valueset_linha) -> None:
        """Open the comparison dialog and apply the ValueSet to chosen cost lines."""
        try:
            with SessionLocal() as session:
                linhas = OrcamentoItemCusteioLinhaService(
                    session
                ).listar_linhas_custeio_por_chave(
                    self.orcamento_item_id, valueset_linha.chave
                )
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar as linhas de custeio.")
            return

        if not linhas:
            self.status_label.setText(
                "Não existem linhas de custeio associadas a esta chave ValueSet."
            )
            return

        dialog = PropagarValuesetCusteioDialog(linhas, valueset_linha, parent=self)
        if not dialog.exec() or not dialog.selected_ids:
            return

        try:
            with SessionLocal() as session:
                atualizadas = OrcamentoItemCusteioLinhaService(
                    session
                ).aplicar_valueset_item_em_linhas_custeio(
                    valueset_linha.id, dialog.selected_ids
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar as linhas de custeio.")
            return

        self.status_label.setText(f"Linhas de custeio atualizadas: {atualizadas}.")

    def copiar_dados(self) -> None:
        """Copy the materia-prima snapshot of the selected line into memory."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        self._copied_snapshot = {field: getattr(linha, field) for field in SNAPSHOT_FIELDS}
        self.status_label.setText("Dados da linha copiados.")

    def colar_dados(self) -> None:
        """Apply the copied snapshot to the selected line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        if self._copied_snapshot is None:
            self.status_label.setText("Não existem dados copiados.")
            return

        try:
            with SessionLocal() as session:
                OrcamentoItemValuesetLinhaService(session).aplicar_snapshot_linha(
                    linha.id, self._copied_snapshot
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível colar os dados.")
            return

        self.carregar()
        self.status_label.setText("Dados colados na linha.")

    def limpar_dados(self) -> None:
        """Clear the materia-prima snapshot of the selected line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "Tem a certeza que pretende limpar os dados desta linha?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                OrcamentoItemValuesetLinhaService(session).limpar_snapshot_linha(linha.id)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível limpar os dados.")
            return

        self.carregar()
        self.status_label.setText("Dados da linha limpos.")

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoItemValuesetLinhaService(session)
                if linha.ativo:
                    service.desativar_linha(linha.id)
                else:
                    service.ativar_linha(linha.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado da linha.")
            return

        mensagem = "Linha desativada." if linha.ativo else "Linha ativada."
        self.carregar()
        self.status_label.setText(mensagem)

    def _abrir_menu_contexto(self, pos) -> None:
        """Show a right-click menu with the line actions."""
        item = self.table.itemAt(pos)
        if item is not None:
            self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.addAction("Editar Linha", self.abrir_editar_linha)
        menu.addAction("Copiar Dados", self.copiar_dados)
        menu.addAction("Colar Dados", self.colar_dados)
        menu.addAction("Limpar Dados", self.limpar_dados)
        menu.addAction("Ativar/Desativar", self.alternar_linha_ativa)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _handle_double_click(self, _row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.abrir_editar_linha()

    def _get_selected_linha(self) -> OrcamentoItemValuesetLinhaResumo | None:
        """Return the selected ValueSet line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
