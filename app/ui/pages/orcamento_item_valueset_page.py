"""Budget item ValueSet page (create from budget + list lines)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
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
from app.services.def_operacao_service import DefOperacaoService
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_valueset_linha_operacao_service import (
    OrcamentoItemValuesetLinhaOperacaoService,
)
from app.services.orcamento_item_valueset_linha_service import (
    CriarOrcamentoItemValuesetLinhaData,
    EditarOrcamentoItemValuesetLinhaData,
    OrcamentoItemValuesetLinhaService,
)
from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog
from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
    OrcamentoItemValuesetLinhaDialog,
)
from app.ui.dialogs.propagar_valueset_custeio_dialog import PropagarValuesetCusteioDialog
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.helpers.valueset_prioridades import (
    avisar_prioridade_repetida_apos_colagem,
)
from app.ui.helpers.valueset_precos import (
    atualizacoes_de_divergencias,
    atualizar_modelo_origem_por_divergencias,
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
from app.utils.formatters import format_currency, format_quantity


class OrcamentoItemValuesetPage(QWidget):
    """Page listing the ValueSet lines of a budget item."""

    #: Pedido para abrir o quadro com TODAS as diferenças ValueSet -> Custeio.
    #: Quem trata é a página de custeio, que é dona do item e do recálculo.
    pedido_rever_diferencas = Signal()

    _copied_snapshot: dict | None = None
    _copied_operacoes: list | None = None

    TABLE_HEADERS = [
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

    def __init__(self, orcamento_item_id: int) -> None:
        super().__init__()

        self.orcamento_item_id = orcamento_item_id
        self._linhas_by_row: dict[int, OrcamentoItemValuesetLinhaResumo] = {}
        self._operacoes_por_linha: dict[int, str] = {}

        self.cabecalho = BarraCabecalho(
            "ValueSet do Item",
            [
                "Materiais, ferragens, acabamentos, orlas, sistemas e acessórios "
                "definidos por defeito para este item."
            ],
        )

        self.create_button = QPushButton("Criar a partir do Orçamento")
        self.create_button.clicked.connect(self.criar_do_orcamento)
        self.import_button = QPushButton("Importar Modelo")
        self.import_button.clicked.connect(self.importar_modelo)
        self.new_button = QPushButton("Nova Linha")
        self.new_button.setToolTip(
            "Criar uma nova opção ValueSet apenas neste item."
        )
        self.new_button.clicked.connect(self.abrir_nova_linha)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.copy_button = QPushButton("Copiar Dados")
        self.copy_button.clicked.connect(self.copiar_dados)
        self.copy_button.setToolTip(
            "Copia prioridade, material e operações da linha selecionada (Ctrl+C)."
        )
        self.paste_button = QPushButton("Colar Dados")
        self.paste_button.clicked.connect(self.colar_dados)
        self.paste_button.setToolTip(
            "Cola os dados numa linha existente, sem criar uma linha nova (Ctrl+V)."
        )
        self.clear_button = QPushButton("Limpar Dados")
        self.clear_button.clicked.connect(self.limpar_dados)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.setToolTip(
            "Ativa ou desativa as linhas selecionadas. Para voltar a ativar uma "
            "linha desativada, ligue primeiro 'Mostrar inativas'."
        )
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.propagate_button = QPushButton("Atualizar Custeio")
        self.propagate_button.setToolTip(
            "Com uma linha selecionada, compara essa chave com o custeio.\n"
            "Sem nada selecionado, mostra TODAS as diferenças entre o ValueSet "
            "e o custeio deste item."
        )
        self.propagate_button.clicked.connect(self.atualizar_custeio_da_linha)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setToolTip("Volta a ler o ValueSet deste item da base de dados.")
        self.refresh_button.clicked.connect(self.carregar)
        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.setToolTip(
            "Mostra também as linhas desativadas, para as poder reativar."
        )
        self.mostrar_inativas_check.toggled.connect(lambda _estado: self.carregar())

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.create_button)
        actions_layout.addWidget(self.import_button)
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.copy_button)
        actions_layout.addWidget(self.paste_button)
        actions_layout.addWidget(self.clear_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.propagate_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.mostrar_inativas_check)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemValuesetStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self._larguras_iniciais_aplicadas = False
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._abrir_menu_contexto)
        self._instalar_atalhos_clipboard()
        # Restaura larguras guardadas; se restaurou, salta o seed por conteúdo.
        if ligar_persistencia_larguras(self.table, "valueset_item"):
            self._larguras_iniciais_aplicadas = True
        configurar_tabela_valueset(self.table, "valueset_item")

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
        """Load the ValueSet lines of the budget item."""
        timer = getattr(self, "_prioridade_flash_timer", None)
        if timer is not None:
            timer.stop()
        self.table.setRowCount(0)
        self.status_label.clear()

        mostrar_inativas = self.mostrar_inativas_check.isChecked()
        try:
            with SessionLocal() as session:
                valueset_service = OrcamentoItemValuesetLinhaService(session)
                linhas = (
                    valueset_service.listar_linhas_do_item(self.orcamento_item_id)
                    if mostrar_inativas
                    else valueset_service.listar_linhas_ativas_do_item(
                        self.orcamento_item_id
                    )
                )
                operacao_service = OrcamentoItemValuesetLinhaOperacaoService(session)
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
                mensagem_erro_bd("Nao foi possivel carregar o ValueSet do item.", error)
            )
            return

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText(
                "Sem ValueSet. Use 'Criar a partir do Orçamento' para preencher este item."
            )
        else:
            self._avisar_prioridades_repetidas(linhas)

    def _preencher(self, linhas: list[OrcamentoItemValuesetLinhaResumo]) -> None:
        """Fill the table with ValueSet lines."""
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
                linha.coresp_orla_0_4 or "",
                linha.coresp_orla_1_0 or "",
                format_quantity(linha.comp_mp),
                format_quantity(linha.larg_mp),
                format_quantity(linha.esp_mp),
                texto_prioridade_valueset(estado),
                str(linha.ordem),
                linha.origem_modelo_codigo or linha.origem_dados or "",
                texto_editado_valueset(estado),
                texto_ativo_valueset(estado),
                self._operacoes_por_linha.get(linha.id, ""),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                aplicar_estilo_item_valueset(
                    item, self.TABLE_HEADERS[column_index], estado
                )
                self.table.setItem(row_index, column_index, item)

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

    def criar_do_orcamento(self) -> None:
        """Create the item ValueSet from the budget version ValueSet."""
        try:
            with SessionLocal() as session:
                linhas_existentes = OrcamentoItemValuesetLinhaService(
                    session
                ).listar_linhas_do_item(self.orcamento_item_id)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd(
                    "Não foi possível verificar o ValueSet atual do item.", error
                )
            )
            return

        substituir = False
        if linhas_existentes:
            escolha = self._perguntar_modo_criar_do_orcamento()
            if escolha is None:
                return
            substituir = escolha

        try:
            with SessionLocal() as session:
                result = OrcamentoItemValuesetLinhaService(
                    session
                ).criar_a_partir_do_orcamento(
                    self.orcamento_item_id, substituir=substituir
                )
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd(
                    "Não foi possível criar o ValueSet a partir do orçamento.", error
                )
            )
            return

        self.carregar()
        if substituir:
            mensagem = (
                "ValueSet do item substituído a partir do orçamento: "
                f"{result.eliminadas} linhas eliminadas, "
                f"{result.criadas} linhas inseridas."
            )
        else:
            mensagem = (
                "ValueSet do item criado a partir do orçamento: "
                f"{result.criadas} criadas, {result.atualizadas} atualizadas, "
                f"{result.ignoradas} ignoradas (editadas localmente, "
                f"de {result.total_origem} linhas)."
            )

        self.status_label.setText(mensagem)
        self._verificar_precos_apos_importacao(None, mensagem)

    def _perguntar_modo_criar_do_orcamento(self) -> bool | None:
        """Ask whether copying from the budget should replace or merge item lines."""
        message = QMessageBox(self)
        message.setWindowTitle("Criar ValueSet a partir do Orçamento")
        message.setText("O ValueSet do item já tem linhas. O que pretende fazer?")
        message.setInformativeText(
            "Substituir tudo: elimina todas as linhas atuais do item "
            "(incluindo as editadas localmente) e recria a partir do orçamento.\n"
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

    def importar_modelo(self) -> None:
        """Open the model picker and import the selected model into the item.

        The user chooses whether the selected model should replace the current
        table or merge with locally edited lines protected.
        """
        dialog = ImportarValuesetModeloDialog(parent=self)
        if not dialog.exec() or dialog.selected_modelo is None:
            return

        modelo = dialog.selected_modelo
        substituir = self._perguntar_modo_importacao_modelo()
        if substituir is None:
            return

        self._importar_modelo_selecionado(modelo, substituir=substituir)

    def _importar_modelo_selecionado(self, modelo, *, substituir: bool) -> None:
        """Import the selected model into this item."""
        try:
            with SessionLocal() as session:
                result = OrcamentoItemValuesetLinhaService(session).importar_modelo_para_item(
                    self.orcamento_item_id, modelo.id, substituir=substituir
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
        self, modelo_id: int | None, mensagem_base: str
    ) -> None:
        """Check item ValueSet prices only after an explicit copy/import action."""
        try:
            with SessionLocal() as session:
                linhas = OrcamentoItemValuesetLinhaService(
                    session
                ).listar_linhas_ativas_do_item(self.orcamento_item_id)
                divergencias = detetar_divergencias_valueset(session, linhas)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível verificar os preços.", error)
            )
            return

        if not divergencias:
            return

        dialog = AtualizarPrecosValuesetDialog(
            divergencias,
            mostrar_atualizar_modelo_origem=modelo_id is not None,
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
                atualizadas = OrcamentoItemValuesetLinhaService(
                    session
                ).atualizar_precos_linhas(atualizacoes_de_divergencias(selecionadas))
                if dialog.atualizar_modelo_origem and modelo_id is not None:
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
        if dialog.atualizar_modelo_origem and modelo_id is not None:
            mensagem += f" Modelo de origem atualizado em {atualizadas_modelo} linha(s)."
        self.status_label.setText(mensagem)

        if atualizadas > 0 and self._perguntar_atualizar_custeio_apos_precos():
            self._atualizar_custeio_para_linhas(
                [divergencia.linha_id for divergencia in selecionadas]
            )

    def _criar_linha_local(self, form_data, *, linha_origem=None):
        """Create one item-only option and copy source operations atomically."""
        with SessionLocal() as session:
            service = OrcamentoItemValuesetLinhaService(session)
            existentes = service.listar_por_chave(
                self.orcamento_item_id, form_data.chave
            )
            prioridades_usadas = {
                linha.prioridade
                for linha in existentes
                if linha.ativo and linha.prioridade is not None
            }
            prioridade = form_data.prioridade
            if prioridade is not None and prioridade in prioridades_usadas:
                prioridade = 1
                while prioridade in prioridades_usadas:
                    prioridade += 1

            proxima_ordem = max((linha.ordem for linha in existentes), default=0) + 1
            result = service.criar_linha(
                CriarOrcamentoItemValuesetLinhaData(
                    orcamento_item_id=self.orcamento_item_id,
                    chave=form_data.chave,
                    codigo_opcao=form_data.codigo_opcao,
                    nome_opcao=form_data.nome_opcao,
                    padrao=False,
                    prioridade=prioridade,
                    ordem=proxima_ordem,
                    descricao=(linha_origem.descricao if linha_origem else None),
                    materia_prima_id=None,
                    ref_materia_prima=form_data.ref_materia_prima,
                    descricao_materia_prima=form_data.descricao_materia_prima,
                    valor_texto=form_data.valor_texto,
                    origem=(linha_origem.origem if linha_origem else None),
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
                    origem_dados="EDITADO_LOCALMENTE",
                    herdado_do_orcamento=False,
                    editado_localmente=True,
                    observacoes=form_data.observacoes,
                    ativo=form_data.ativo,
                ),
                commit=False,
            )

            if linha_origem is not None:
                operacoes_service = OrcamentoItemValuesetLinhaOperacaoService(session)
                operacoes = operacoes_service.listar_operacoes_da_linha(
                    linha_origem.id
                )
                operacoes_service.copiar_operacoes_de(operacoes, result.id)

            session.commit()
            return result

    def abrir_nova_linha(self) -> None:
        """Create a ValueSet option local to this budget item."""
        criada = None

        def handle_save(form_data) -> bool:
            nonlocal criada
            try:
                criada = self._criar_linha_local(form_data)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(
                    mensagem_erro_bd(
                        "Não foi possível criar a linha. Verifique os dados.", error
                    )
                )
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível criar a linha.", error)
                )
                return False
            return True

        dialog = OrcamentoItemValuesetLinhaDialog(parent=self, on_save=handle_save)
        if dialog.exec() and criada is not None:
            self.carregar()
            prioridade = criada.prioridade if criada.prioridade is not None else "vazia"
            self.status_label.setText(
                f"Nova opção local do item criada com prioridade {prioridade}."
            )

    def abrir_editar_linha(self) -> None:
        """Open the edit dialog for the selected ValueSet line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        saved = False
        saved_as = None

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
                            preco_orla_0_4_m2=form_data.preco_orla_0_4_m2,
                            preco_orla_1_0_m2=form_data.preco_orla_1_0_m2,
                            comp_mp=form_data.comp_mp,
                            larg_mp=form_data.larg_mp,
                            esp_mp=form_data.esp_mp,
                            origem_dados=form_data.origem_dados,
                            herdado_do_orcamento=linha.herdado_do_orcamento,
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

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as
            try:
                saved_as = self._criar_linha_local(
                    form_data, linha_origem=linha
                )
            except (IntegrityError, ValueError) as error:
                dialog.set_error(
                    mensagem_erro_bd(
                        "Não foi possível gravar como nova opção. Verifique os dados.",
                        error,
                    )
                )
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd(
                        "Não foi possível gravar como nova opção.", error
                    )
                )
                return False
            return True

        dialog = OrcamentoItemValuesetLinhaDialog(
            linha,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha ValueSet atualizada.")
            self._perguntar_propagar_custeio(linha.id)
        elif saved_as is not None:
            self.carregar()
            prioridade = (
                saved_as.prioridade if saved_as.prioridade is not None else "vazia"
            )
            self.status_label.setText(
                "Linha gravada como nova opção local do item, com as operações "
                f"da original e prioridade {prioridade}."
            )
            self._perguntar_propagar_custeio(saved_as.id)
        elif dialog.operacoes_alteradas:
            self.carregar()
            self.status_label.setText("Operações da linha atualizadas.")

    def atualizar_custeio_da_linha(self) -> None:
        """Compare and propagate the ValueSet into the cost lines.

        Com uma linha selecionada, revê só essa chave. Sem nada selecionado,
        pede o quadro com todas as diferenças do item — é o caminho prático
        quando se trocaram vários materiais de uma vez.
        """
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText(
                "A procurar diferenças entre o ValueSet e o custeio deste item..."
            )
            self.pedido_rever_diferencas.emit()
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
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível carregar a linha ValueSet.", error)
            )
            return

        if linha is not None:
            self._propagar_para_custeio(linha)

    def _perguntar_atualizar_custeio_apos_precos(self) -> bool:
        """Ask whether to review costing after updating ValueSet prices."""
        resposta = QMessageBox.question(
            self,
            "Atualizar custeio",
            "Atualizar o custeio agora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes

    def _atualizar_custeio_para_linhas(self, valueset_linha_ids: list[int]) -> None:
        """Run the existing cost propagation flow for the updated ValueSet lines."""
        for valueset_linha_id in valueset_linha_ids:
            try:
                with SessionLocal() as session:
                    linha = OrcamentoItemValuesetLinhaService(session).obter_por_id(
                        valueset_linha_id
                    )
            except SQLAlchemyError as error:
                self.status_label.setText(
                    mensagem_erro_bd(
                        "Não foi possível carregar a linha ValueSet.", error
                    )
                )
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
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar as linhas de custeio.", error)
            )
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
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar as linhas de custeio.", error)
            )
            return

        self.status_label.setText(f"Linhas de custeio atualizadas: {atualizadas}.")

    def copiar_dados(self) -> None:
        """Copy the materia-prima snapshot and operations of the selected line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        try:
            with SessionLocal() as session:
                type(self)._copied_snapshot = OrcamentoItemValuesetLinhaService(
                    session
                ).copiar_snapshot_linha(linha.id)
                type(self)._copied_operacoes = OrcamentoItemValuesetLinhaOperacaoService(
                    session
                ).listar_operacoes_da_linha(linha.id)
        except (SQLAlchemyError, ValueError) as error:
            type(self)._copied_snapshot = None
            type(self)._copied_operacoes = None
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível copiar os dados.", error)
            )
            return

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

        snapshot = type(self)._copied_snapshot
        operacoes = type(self)._copied_operacoes
        if snapshot is None:
            self.status_label.setText("Não existem dados copiados.")
            return

        colar_operacoes = False
        total_operacoes = len(operacoes) if operacoes else 0
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
                try:
                    OrcamentoItemValuesetLinhaService(session).aplicar_snapshot_linha(
                        linha.id, snapshot, commit=False
                    )
                    if colar_operacoes:
                        OrcamentoItemValuesetLinhaOperacaoService(
                            session
                        ).copiar_operacoes_de(operacoes or [], linha.id)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível colar os dados.", error)
            )
            return

        self.carregar()
        aviso_prioridade = avisar_prioridade_repetida_apos_colagem(
            self,
            table=self.table,
            headers=self.TABLE_HEADERS,
            linhas_by_row=self._linhas_by_row,
            linha_id=linha.id,
        )
        if aviso_prioridade:
            self.status_label.setText(aviso_prioridade)
            return
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
                service = OrcamentoItemValuesetLinhaService(session)
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

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected lines."""
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
                service = OrcamentoItemValuesetLinhaService(session)
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

    def _abrir_menu_contexto(self, pos) -> None:
        """Show a right-click menu with the line actions."""
        item = self.table.itemAt(pos)
        if item is not None:
            selected_rows = {
                index.row() for index in self.table.selectionModel().selectedRows()
            }
            if item.row() not in selected_rows:
                self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.addAction("Nova Linha", self.abrir_nova_linha)
        menu.addAction("Editar Linha", self.abrir_editar_linha)
        menu.addAction("Copiar Dados (Ctrl+C)", self.copiar_dados)
        menu.addAction("Colar Dados (Ctrl+V)", self.colar_dados)
        menu.addAction("Limpar Dados", self.limpar_dados)
        menu.addAction("Ativar/Desativar", self.alternar_linha_ativa)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _instalar_atalhos_clipboard(self) -> None:
        """Atalhos de conteúdo ativos apenas quando a tabela tem foco."""
        for sequencia, handler in (
            (QKeySequence.StandardKey.Copy, self.copiar_dados),
            (QKeySequence.StandardKey.Paste, self.colar_dados),
        ):
            atalho = QShortcut(sequencia, self.table)
            atalho.setContext(Qt.ShortcutContext.WidgetShortcut)
            atalho.activated.connect(handler)

    def _handle_double_click(self, _row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.abrir_editar_linha()

    def _get_selected_linha(self) -> OrcamentoItemValuesetLinhaResumo | None:
        """Return the selected ValueSet line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _get_selected_linhas(self) -> list[OrcamentoItemValuesetLinhaResumo]:
        """Return selected ValueSet lines ordered by table row."""
        selection = self.table.selectionModel()
        if selection is None:
            return []

        linhas: list[OrcamentoItemValuesetLinhaResumo] = []
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
