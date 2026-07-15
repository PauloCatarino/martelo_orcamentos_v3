"""Detail page for one ValueSet model and its lines."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFormLayout,
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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_operacao_service import DefOperacaoService
from app.services.def_valueset_modelo_service import (
    CriarDefValuesetModeloData,
    DefValuesetModeloService,
)
from app.services.def_valueset_modelo_linha_operacao_service import (
    DefValuesetModeloLinhaOperacaoService,
)
from app.services.def_valueset_modelo_linha_service import (
    CriarDefValuesetModeloLinhaData,
    DefValuesetModeloLinhaService,
    EditarDefValuesetModeloLinhaData,
)
from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog
from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.helpers.valueset_precos import (
    atualizacoes_de_divergencias,
    detetar_divergencias_valueset,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.estilo_tabela_valueset import (
    aplicar_estilo_item_valueset,
    configurar_tabela_valueset,
    preparar_linhas_valueset,
    texto_ativo_valueset,
    texto_chave_valueset,
    texto_editado_valueset,
    texto_opcao_valueset,
    texto_prioridade_valueset,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency


class DefValuesetModeloDetailPage(QWidget):
    """Detail page showing one ValueSet model and managing its lines."""

    LINHA_HEADERS = [
        "Chave",
        "Opção",
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
        "Prioridade",
        "Ordem",
        "Editado localmente",
        "Ativo",
        "Operações",
    ]

    def __init__(
        self,
        modelo: DefValuesetModeloResumo,
        on_back: Callable[[], None] | None = None,
        on_modelo_duplicado: Callable[[DefValuesetModeloResumo, str], None] | None = None,
    ) -> None:
        super().__init__()

        self.modelo = modelo
        self.on_back = on_back
        self.on_modelo_duplicado = on_modelo_duplicado
        self._linhas_by_row: dict[int, DefValuesetModeloLinhaResumo] = {}
        self._operacoes_por_linha: dict[int, str] = {}

        self.cabecalho = BarraCabecalho(
            f"Modelo ValueSet: {modelo.nome}",
            [f"Configurações > Modelos ValueSet > {modelo.nome}"],
        )

        form = QFormLayout()
        for label, value in [
            ("Código", modelo.codigo),
            ("Nome", modelo.nome),
            ("Tipo", modelo.tipo or ""),
            ("Âmbito", modelo.ambito),
            ("Ativo", self._format_bool(modelo.ativo)),
        ]:
            form.addRow(f"{label}:", QLabel(value))

        self.new_button = QPushButton("Nova Linha")
        self.new_button.clicked.connect(self.abrir_nova_linha)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(
            lambda _=0: self.carregar_linhas()
        )
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_linhas)
        self.check_prices_button = QPushButton("Verificar preços…")
        self.check_prices_button.clicked.connect(self.verificar_precos)
        self.back_button = QPushButton("Voltar à lista")
        self.back_button.clicked.connect(self._handle_back)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.mostrar_inativas_check)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.check_prices_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.back_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetModeloDetailStatus")

        self.table = QTableWidget(0, len(self.LINHA_HEADERS))
        self.table.setHorizontalHeaderLabels(self.LINHA_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self._larguras_iniciais_aplicadas = False
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        # Restaura larguras guardadas; se restaurou, salta o seed por conteúdo.
        if ligar_persistencia_larguras(self.table, "valueset_modelo"):
            self._larguras_iniciais_aplicadas = True
        configurar_tabela_valueset(self.table, "valueset_modelo")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(form)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_linhas()

    def carregar_linhas(self) -> None:
        """Load the model lines into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = DefValuesetModeloLinhaService(session).listar_linhas_do_modelo(
                    self.modelo.id
                )
                operacao_service = DefValuesetModeloLinhaOperacaoService(session)
                operacoes = {
                    operacao.id: operacao.codigo
                    for operacao in DefOperacaoService(session).listar_operacoes()
                }
                self._operacoes_por_linha = {}
                for linha in linhas:
                    ligacoes = operacao_service.listar_operacoes_ativas_da_linha(
                        linha.id
                    )
                    self._operacoes_por_linha[linha.id] = "; ".join(
                        operacoes.get(ligacao.def_operacao_id, f"#{ligacao.def_operacao_id}")
                        for ligacao in ligacoes
                    )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar as linhas do modelo.", error)
            )
            return

        if not self.mostrar_inativas_check.isChecked():
            linhas = [linha for linha in linhas if linha.ativo]

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText("Sem linhas neste modelo.")
        else:
            self._avisar_prioridades_repetidas(linhas)

    def verificar_precos(self) -> None:
        """Explicitly check model line prices against the material catalog."""
        try:
            with SessionLocal() as session:
                linhas = DefValuesetModeloLinhaService(session).listar_linhas_do_modelo(
                    self.modelo.id
                )
                divergencias = detetar_divergencias_valueset(session, linhas)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível verificar os preços.", error)
            )
            return

        if not divergencias:
            self.status_label.setText("Sem divergências de preço.")
            return

        dialog = AtualizarPrecosValuesetDialog(divergencias, parent=self)
        if not dialog.exec():
            self.status_label.setText(self._status_precos(0, len(divergencias)))
            return

        selecionadas = dialog.selected_divergencias
        if not selecionadas:
            self.status_label.setText(self._status_precos(0, len(divergencias)))
            return

        try:
            with SessionLocal() as session:
                atualizadas = DefValuesetModeloLinhaService(
                    session
                ).atualizar_precos_linhas(atualizacoes_de_divergencias(selecionadas))
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar os preços.", error)
            )
            return

        self.carregar_linhas()
        self.status_label.setText(
            self._status_precos(atualizadas, len(divergencias) - atualizadas)
        )

    def gravar_modelo_como(self) -> None:
        """Save this ValueSet model as a new model."""
        saved_as = False
        saved_as_codigo: str | None = None
        saved_as_linhas = 0
        modelo_novo: DefValuesetModeloResumo | None = None

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as, saved_as_codigo, saved_as_linhas, modelo_novo

            try:
                with SessionLocal() as session:
                    result = DefValuesetModeloService(session).duplicar_modelo(
                        self.modelo.id,
                        self._criar_modelo_data_from_form_data(form_data),
                    )
            except IntegrityError:
                dialog.set_error("Já existe um modelo com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._modelo_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar o modelo.", error)
                )
                return False

            saved_as = True
            modelo_novo = result.modelo
            saved_as_codigo = result.modelo.codigo
            saved_as_linhas = result.linhas_copiadas
            return True

        dialog = DefValuesetModeloDialog(
            modelo=self.modelo,
            parent=self,
            on_save_as=handle_save_as,
        )
        save_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setVisible(False)

        if not dialog.exec() or not saved_as or modelo_novo is None:
            return

        mensagem = f"Modelo gravado como {saved_as_codigo}."
        if self.on_modelo_duplicado is not None:
            self.on_modelo_duplicado(modelo_novo, mensagem)
            return

        self.status_label.setText(f"{mensagem} {saved_as_linhas} linhas copiadas.")

    def _preencher(self, linhas: list[DefValuesetModeloLinhaResumo]) -> None:
        """Fill the table with model lines."""
        self._linhas_by_row = {}
        estados = preparar_linhas_valueset(linhas)
        self.table.setRowCount(len(estados))

        for row_index, estado in enumerate(estados):
            linha = estado.linha
            self._linhas_by_row[row_index] = linha
            values = [
                texto_chave_valueset(estado),
                texto_opcao_valueset(
                    estado, linha.nome_opcao or linha.codigo_opcao or ""
                ),
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
                texto_prioridade_valueset(estado),
                str(linha.ordem),
                texto_editado_valueset(estado),
                texto_ativo_valueset(estado),
                self._operacoes_por_linha.get(linha.id, ""),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                aplicar_estilo_item_valueset(
                    item, self.LINHA_HEADERS[column_index], estado
                )
                self.table.setItem(row_index, column_index, item)

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

    def abrir_nova_linha(self) -> None:
        """Open the dialog to create a new model line."""
        self._abrir_dialog_criar_linha(success_message="Linha criada.")

    def _abrir_dialog_criar_linha(
        self,
        *,
        success_message: str,
    ) -> None:
        """Open a create dialog for a model line."""
        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                self._criar_linha_from_form_data(form_data)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a linha.", error)
                )
                return False

            saved = True
            return True

        dialog = DefValuesetModeloLinhaDialog(parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar_linhas()
            self.status_label.setText(success_message)

    def _criar_linha_from_form_data(self, form_data):
        """Create one model line from dialog data."""
        with SessionLocal() as session:
            service = DefValuesetModeloLinhaService(session)
            result = service.criar_linha(
                CriarDefValuesetModeloLinhaData(
                    def_valueset_modelo_id=self.modelo.id,
                    chave=form_data.chave,
                    codigo_opcao=form_data.codigo_opcao,
                    nome_opcao=form_data.nome_opcao,
                    ref_materia_prima=form_data.ref_materia_prima,
                    descricao_materia_prima=form_data.descricao_materia_prima,
                    valor_texto=form_data.valor_texto,
                    prioridade=form_data.prioridade,
                    ordem=form_data.ordem,
                    observacoes=form_data.observacoes,
                    ativo=form_data.ativo,
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
                    preco_orla_0_4_m2=form_data.preco_orla_0_4_m2,
                    preco_orla_1_0_m2=form_data.preco_orla_1_0_m2,
                    comp_mp=form_data.comp_mp,
                    larg_mp=form_data.larg_mp,
                    esp_mp=form_data.esp_mp,
                    origem_dados=form_data.origem_dados,
                    editado_localmente=form_data.editado_localmente,
                )
            )

            return result

    def _criar_modelo_data_from_form_data(self, form_data) -> CriarDefValuesetModeloData:
        """Build create-service data from model dialog data."""
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

    def abrir_editar_linha(self) -> None:
        """Open the dialog to edit the selected model line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        saved = False
        saved_as = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    service = DefValuesetModeloLinhaService(session)
                    service.editar_linha(
                        linha.id,
                        EditarDefValuesetModeloLinhaData(
                            def_valueset_modelo_id=self.modelo.id,
                            chave=form_data.chave,
                            codigo_opcao=form_data.codigo_opcao,
                            nome_opcao=form_data.nome_opcao,
                            ref_materia_prima=form_data.ref_materia_prima,
                            descricao_materia_prima=form_data.descricao_materia_prima,
                            valor_texto=form_data.valor_texto,
                            padrao=linha.padrao,
                            prioridade=form_data.prioridade,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
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
                            preco_orla_0_4_m2=form_data.preco_orla_0_4_m2,
                            preco_orla_1_0_m2=form_data.preco_orla_1_0_m2,
                            comp_mp=form_data.comp_mp,
                            larg_mp=form_data.larg_mp,
                            esp_mp=form_data.esp_mp,
                            origem_dados=form_data.origem_dados,
                            editado_localmente=form_data.editado_localmente,
                        ),
                    )
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a linha.", error)
                )
                return False

            saved = True
            return True

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as

            try:
                self._criar_linha_from_form_data(form_data)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a linha.", error)
                )
                return False

            saved_as = True
            return True

        dialog = DefValuesetModeloLinhaDialog(
            linha=linha,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar_linhas()
            self.status_label.setText("Linha atualizada.")
        elif saved_as:
            self.carregar_linhas()
            self.status_label.setText("Linha gravada como nova opção.")
        elif dialog.operacoes_alteradas:
            self.carregar_linhas()
            self.status_label.setText("Operações da linha atualizadas.")

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected model line after confirmation."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para ativar/desativar.")
            return

        acao = "desativar" if linha.ativo else "reativar"
        aviso = ""
        if linha.ativo and linha.prioridade is not None:
            aviso = " A escolha automatica desta chave passa para a proxima prioridade."
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta linha?{aviso}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefValuesetModeloLinhaService(session)
                if linha.ativo:
                    service.desativar_linha(linha.id)
                else:
                    service.ativar_linha(linha.id)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar o estado da linha.", error)
            )
            return

        estado = "desativada" if linha.ativo else "reativada"
        self.carregar_linhas()
        self.status_label.setText(f"Linha {estado}.")

    def _get_selected_linha(self) -> DefValuesetModeloLinhaResumo | None:
        """Return the selected model line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_editar_linha()

    def _handle_back(self) -> None:
        """Return to the model list."""
        if self.on_back is not None:
            self.on_back()

    def _linha_error_message(self, error: Exception) -> str:
        """Map a service error to a friendly message."""
        if "opcao ja existe" in str(error):
            return "Já existe uma opção com esse código nesta chave."
        if isinstance(error, ValueError):
            return str(error)

        return mensagem_erro_bd(
            "Não foi possível guardar a linha. Verifique a chave e o código da opção.",
            error,
        )

    def _modelo_error_message(self, error: ValueError) -> str:
        """Map a model service error to a friendly message."""
        if "codigo ja existe" in str(error):
            return "Já existe um modelo com esse código."
        return "Não foi possível guardar o modelo."

    def _format_materia_prima(self, linha: DefValuesetModeloLinhaResumo) -> str:
        """Format the materia-prima / value cell."""
        return (
            linha.ref_materia_prima
            or linha.descricao_materia_prima
            or linha.valor_texto
            or ""
        )

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
