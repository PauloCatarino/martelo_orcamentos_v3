"""Budget ValueSet page (import model + list lines)."""

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
from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services.def_operacao_service import DefOperacaoService
from app.services.orcamento_valueset_linha_operacao_service import (
    OrcamentoValuesetLinhaOperacaoService,
)
from app.services.orcamento_valueset_linha_service import (
    SNAPSHOT_FIELDS,
    EditarOrcamentoValuesetLinhaData,
    OrcamentoValuesetLinhaService,
)
from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog
from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.helpers.valueset_precos import (
    atualizacoes_de_divergencias,
    atualizar_modelo_origem_por_divergencias,
    detetar_divergencias_valueset,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class OrcamentoValuesetPage(QWidget):
    """Page listing the ValueSet lines of a budget version."""

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
        "Prioridade",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
        "Operações",
    ]

    def __init__(self, orcamento_versao_id: int) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id
        self._linhas_by_row: dict[int, OrcamentoValuesetLinhaResumo] = {}
        self._operacoes_por_linha: dict[int, str] = {}
        self._copied_snapshot: dict | None = None
        self._copied_operacoes: list | None = None

        self.cabecalho = BarraCabecalho(
            "ValueSet do Orçamento",
            [
                "Materiais, ferragens, acabamentos, orlas, sistemas e acessórios "
                "definidos por defeito para este orçamento."
            ],
        )

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
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.import_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.copy_button)
        actions_layout.addWidget(self.paste_button)
        actions_layout.addWidget(self.clear_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoValuesetStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._abrir_menu_contexto)
        ligar_persistencia_larguras(self.table, "orcamento_valueset")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Load the ValueSet lines of the budget version."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = OrcamentoValuesetLinhaService(session).listar_linhas_da_versao(
                    self.orcamento_versao_id
                )
                operacao_service = OrcamentoValuesetLinhaOperacaoService(session)
                operacoes_codigos = {
                    operacao.id: operacao.codigo
                    for operacao in DefOperacaoService(session).listar_operacoes()
                }
                self._operacoes_por_linha = {}
                for linha in linhas:
                    ligacoes = operacao_service.listar_operacoes_ativas_da_linha(linha.id)
                    self._operacoes_por_linha[linha.id] = "; ".join(
                        operacoes_codigos.get(
                            ligacao.def_operacao_id, f"#{ligacao.def_operacao_id}"
                        )
                        for ligacao in ligacoes
                    )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar o ValueSet do orcamento.", error)
            )
            return

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText(
                "Sem ValueSet. Use 'Importar Modelo' para preencher este orçamento."
            )
        else:
            self._avisar_prioridades_repetidas(linhas)

    def _preencher(self, linhas: list[OrcamentoValuesetLinhaResumo]) -> None:
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
                self._format_prioridade(linha.prioridade),
                str(linha.ordem),
                linha.origem_modelo_codigo or linha.origem_dados or "",
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
                self._operacoes_por_linha.get(linha.id, ""),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def importar_modelo(self) -> None:
        """Open the model picker and import the selected model."""
        dialog = ImportarValuesetModeloDialog(parent=self)
        if not dialog.exec() or dialog.selected_modelo is None:
            return

        modelo = dialog.selected_modelo
        substituir = self._perguntar_modo_importacao_modelo()
        if substituir is None:
            return

        try:
            with SessionLocal() as session:
                result = OrcamentoValuesetLinhaService(session).importar_modelo_para_orcamento(
                    self.orcamento_versao_id, modelo.id, substituir=substituir
                )
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível importar o modelo.", error)
            )
            return

        self.carregar()
        if substituir:
            mensagem = (
                f"Modelo {result.modelo_codigo}: tabela substituída, "
                f"{result.eliminadas} linhas eliminadas, "
                f"{result.criadas} linhas inseridas."
            )
        else:
            mensagem = (
                f"Modelo {result.modelo_codigo} importado: "
                f"{result.criadas} criadas, {result.atualizadas} atualizadas, "
                f"{result.ignoradas} ignoradas (editadas localmente)."
            )

        self.status_label.setText(mensagem)
        self._verificar_precos_apos_importacao(modelo.id, mensagem)

    def _perguntar_modo_importacao_modelo(self) -> bool | None:
        """Ask whether importing a model should replace or merge the table."""
        message = QMessageBox(self)
        message.setWindowTitle("Importar modelo ValueSet")
        message.setText("O que pretende fazer aos dados atuais do ValueSet?")
        message.setInformativeText(
            "Substituir tudo: elimina todas as linhas atuais do ValueSet "
            "(incluindo as editadas localmente) e insere as linhas do modelo.\n"
            "Atualizar: atualiza as linhas existentes; as editadas localmente "
            "são mantidas."
        )
        substituir_button = message.addButton(
            "Substituir tudo", QMessageBox.ButtonRole.DestructiveRole
        )
        atualizar_button = message.addButton(
            "Atualizar", QMessageBox.ButtonRole.AcceptRole
        )
        cancelar_button = message.addButton(
            "Cancelar", QMessageBox.ButtonRole.RejectRole
        )
        message.setDefaultButton(atualizar_button)
        message.setEscapeButton(cancelar_button)
        message.exec()

        clicked = message.clickedButton()
        if clicked is substituir_button:
            return True
        if clicked is atualizar_button:
            return False
        return None

    def _verificar_precos_apos_importacao(
        self, modelo_id: int, mensagem_base: str
    ) -> None:
        """Check imported ValueSet prices only after an explicit import action."""
        try:
            with SessionLocal() as session:
                linhas = OrcamentoValuesetLinhaService(session).listar_linhas_da_versao(
                    self.orcamento_versao_id
                )
                divergencias = detetar_divergencias_valueset(
                    session, [linha for linha in linhas if linha.ativo]
                )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível verificar os preços.", error)
            )
            return

        if not divergencias:
            return

        dialog = AtualizarPrecosValuesetDialog(
            divergencias,
            mostrar_atualizar_modelo_origem=True,
            parent=self,
        )
        if not dialog.exec():
            return

        selecionadas = dialog.selected_divergencias
        if not selecionadas:
            self.status_label.setText(
                f"{mensagem_base} {self._status_precos(0, len(divergencias))}"
            )
            return

        atualizadas_modelo = 0
        try:
            with SessionLocal() as session:
                atualizadas = OrcamentoValuesetLinhaService(
                    session
                ).atualizar_precos_linhas(atualizacoes_de_divergencias(selecionadas))
                if dialog.atualizar_modelo_origem:
                    atualizadas_modelo = atualizar_modelo_origem_por_divergencias(
                        session, modelo_id, selecionadas
                    )
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar os preços.", error)
            )
            return

        self.carregar()
        mensagem = (
            f"{mensagem_base} "
            f"{self._status_precos(atualizadas, len(divergencias) - atualizadas)}"
        )
        if dialog.atualizar_modelo_origem:
            mensagem += f" Modelo de origem atualizado em {atualizadas_modelo} linha(s)."
        self.status_label.setText(mensagem)

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected lines after confirmation."""
        linhas = self._get_selected_linhas()
        if not linhas:
            self.status_label.setText("Selecione uma ou mais linhas.")
            return

        total = len(linhas)
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Tem a certeza que pretende ativar/desativar {total} linha(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        atualizadas = 0
        try:
            with SessionLocal() as session:
                service = OrcamentoValuesetLinhaService(session)
                for linha in linhas:
                    try:
                        with session.begin_nested():
                            if linha.ativo:
                                atualizadas += int(
                                    service.desativar_linha(linha.id, commit=False)
                                )
                            else:
                                atualizadas += int(
                                    service.ativar_linha(linha.id, commit=False)
                                )
                    except (SQLAlchemyError, ValueError):
                        continue
                session.commit()
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar o estado da linha.", error)
            )
            return

        self.carregar()
        if atualizadas == total:
            self.status_label.setText(f"Estado atualizado em {atualizadas} linha(s).")
        else:
            self.status_label.setText(
                f"Estado atualizado em {atualizadas} de {total} linhas."
            )

    def abrir_editar_linha(self) -> None:
        """Open the edit dialog for the selected ValueSet line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoValuesetLinhaService(session).editar_linha(
                        linha.id,
                        EditarOrcamentoValuesetLinhaData(
                            orcamento_versao_id=self.orcamento_versao_id,
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
                            origem_modelo_id=linha.origem_modelo_id,
                            origem_modelo_codigo=linha.origem_modelo_codigo,
                            editado_localmente=form_data.editado_localmente,
                            padrao=linha.padrao,
                            prioridade=form_data.prioridade,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
                        ),
                    )
            except (IntegrityError, ValueError) as error:
                dialog.set_error(
                    mensagem_erro_bd(
                        "Não foi possível guardar a linha. Verifique os dados.", error
                    )
                )
                return False

            saved = True
            return True

        dialog = OrcamentoValuesetLinhaDialog(linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha ValueSet atualizada.")
        elif dialog.operacoes_alteradas:
            self.carregar()
            self.status_label.setText("Operações da linha atualizadas.")

    def _handle_double_click(self, _row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.abrir_editar_linha()

    def copiar_dados(self) -> None:
        """Copy the materia-prima snapshot and operations of the selected line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        self._copied_snapshot = {field: getattr(linha, field) for field in SNAPSHOT_FIELDS}
        self._copied_snapshot["prioridade"] = linha.prioridade

        try:
            with SessionLocal() as session:
                self._copied_operacoes = OrcamentoValuesetLinhaOperacaoService(
                    session
                ).listar_operacoes_da_linha(linha.id)
        except SQLAlchemyError:
            self._copied_operacoes = []

        self.status_label.setText("Dados da linha copiados.")

    def colar_dados(self) -> None:
        """Apply the copied snapshot to the selected line.

        If the copied line had operations, the user is asked whether to also
        paste them (replacing the destination line's operations).
        """
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        if self._copied_snapshot is None:
            self.status_label.setText("Não existem dados copiados.")
            return

        colar_operacoes = False
        total_operacoes = len(self._copied_operacoes) if self._copied_operacoes else 0
        if total_operacoes:
            confirm = QMessageBox.question(
                self,
                "Colar operações",
                f"A linha copiada tem {total_operacoes} operação(ões). Colar também "
                "as operações? (substituem as da linha de destino)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            colar_operacoes = confirm == QMessageBox.StandardButton.Yes

        try:
            with SessionLocal() as session:
                OrcamentoValuesetLinhaService(session).aplicar_snapshot_linha(
                    linha.id, self._copied_snapshot
                )
                if colar_operacoes:
                    OrcamentoValuesetLinhaOperacaoService(session).copiar_operacoes_de(
                        self._copied_operacoes, linha.id
                    )
                    session.commit()
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível colar os dados.", error)
            )
            return

        self.carregar()
        if colar_operacoes:
            self.status_label.setText(
                "Dados e operações colados — valide as operações na linha de destino."
            )
        else:
            self.status_label.setText("Dados colados na linha.")

    def limpar_dados(self) -> None:
        """Clear the materia-prima snapshot of the selected lines."""
        linhas = self._get_selected_linhas()
        if not linhas:
            self.status_label.setText("Selecione uma ou mais linhas.")
            return

        total = len(linhas)
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Tem a certeza que pretende limpar os dados de {total} linha(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        limpas = 0
        try:
            with SessionLocal() as session:
                service = OrcamentoValuesetLinhaService(session)
                for linha in linhas:
                    try:
                        with session.begin_nested():
                            service.limpar_snapshot_linha(linha.id, commit=False)
                            limpas += 1
                    except (SQLAlchemyError, ValueError):
                        continue
                session.commit()
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível limpar os dados.", error)
            )
            return

        self.carregar()
        if limpas == total:
            self.status_label.setText(f"Dados limpos em {limpas} linha(s).")
        else:
            self.status_label.setText(f"Dados limpos em {limpas} de {total} linhas.")

    def _abrir_menu_contexto(self, pos) -> None:
        """Show a right-click menu with the quick line actions."""
        item = self.table.itemAt(pos)
        if item is not None:
            selected_rows = {
                index.row() for index in self.table.selectionModel().selectedRows()
            }
            if item.row() not in selected_rows:
                self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.addAction("Editar Linha", self.abrir_editar_linha)
        menu.addAction("Copiar Dados", self.copiar_dados)
        menu.addAction("Colar Dados", self.colar_dados)
        menu.addAction("Limpar Dados", self.limpar_dados)
        menu.addAction("Ativar/Desativar", self.alternar_linha_ativa)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _get_selected_linha(self) -> OrcamentoValuesetLinhaResumo | None:
        """Return the selected ValueSet line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _get_selected_linhas(self) -> list[OrcamentoValuesetLinhaResumo]:
        """Return selected ValueSet lines ordered by table row."""
        selection = self.table.selectionModel()
        if selection is None:
            return []

        linhas: list[OrcamentoValuesetLinhaResumo] = []
        seen_rows: set[int] = set()
        for index in sorted(selection.selectedRows(), key=lambda idx: idx.row()):
            row = index.row()
            if row in seen_rows:
                continue
            seen_rows.add(row)
            linha = self._linhas_by_row.get(row)
            if linha is not None:
                linhas.append(linha)
        return linhas

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"

    def _status_precos(self, atualizados: int, mantidos: int) -> str:
        """Format the final price-update status."""
        mantido_label = "mantido" if mantidos == 1 else "mantidos"
        return f"{atualizados} preços atualizados; {mantidos} {mantido_label}."

    def _format_prioridade(self, prioridade: int | None) -> str:
        """Format the priority for display ("—" when empty)."""
        return "—" if prioridade is None else str(prioridade)

    def _avisar_prioridades_repetidas(self, linhas) -> None:
        """Soft warning when two active lines of one key share a priority."""
        contagem: dict[tuple[str, int], int] = {}
        for linha in linhas:
            if not linha.ativo or linha.prioridade is None:
                continue
            par = (linha.chave, linha.prioridade)
            contagem[par] = contagem.get(par, 0) + 1

        chaves = sorted({chave for (chave, _), total in contagem.items() if total > 1})
        if chaves:
            self.status_label.setText(
                "Aviso: prioridade repetida nas chaves: "
                + ", ".join(chaves)
                + ". O desempate é pelo id da linha."
            )
