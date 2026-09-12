"""Budget ValueSet page (import model + list lines)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem
from app.domain.valueset_modelo_pesquisa import filtrar_linhas_valueset_modelo
from app.domain.valueset_navegador_chaves import metas_por_codigo
from app.services.def_valueset_chave_service import DefValuesetChaveService
from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services.def_operacao_service import DefOperacaoService
from app.services.orcamento_valueset_linha_operacao_service import (
    OrcamentoValuesetLinhaOperacaoService,
)
from app.services.orcamento_valueset_linha_service import (
    CriarOrcamentoValuesetLinhaData,
    EditarOrcamentoValuesetLinhaData,
    OrcamentoValuesetLinhaService,
)
from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog
from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.helpers.valueset_prioridades import (
    avisar_prioridade_repetida_apos_colagem,
)
from app.ui.helpers.valueset_precos import (
    atualizacoes_de_divergencias,
    atualizar_modelo_origem_por_divergencias,
    detetar_divergencias_valueset,
)
from app.ui.tema import CINZA_CASTANHO
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import BotaoLimparFiltros, CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter
from app.ui.widgets.navegador_chaves_valueset import (
    NavegadorChavesValueset,
    escrever_faixa_grupo,
)
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
from app.ui.icones import decorar_barra


class OrcamentoValuesetPage(QWidget):
    """Page listing the ValueSet lines of a budget version."""

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

    def __init__(self, orcamento_versao_id: int) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id
        self._linhas_by_row: dict[int, OrcamentoValuesetLinhaResumo] = {}
        self._operacoes_por_linha: dict[int, str] = {}
        self._todas_linhas: list[OrcamentoValuesetLinhaResumo] = []
        # Que linha da tabela é uma faixa de grupo, e de que grupo.
        self._faixas_by_row: dict[int, str] = {}

        self.cabecalho = BarraCabecalho(
            "ValueSet do Orçamento",
            [
                "Materiais, ferragens, acabamentos, orlas, sistemas e acessórios "
                "definidos por defeito para este orçamento."
            ],
        )

        self.import_button = QPushButton("Importar Modelo")
        self.import_button.clicked.connect(self.importar_modelo)
        self.new_button = QPushButton("Nova Linha")
        self.new_button.setToolTip(
            "Criar uma nova opção ValueSet apenas neste orçamento."
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
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        # Os botões vão por famílias, separados por uma barra vertical, como
        # na página do modelo: trazer de fora, mexer no conteúdo, ir à base.
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)
        grupos_de_botoes = [
            [self.import_button, self.new_button, self.edit_button, self.toggle_button],
            [self.copy_button, self.paste_button, self.clear_button],
            [self.refresh_button],
        ]
        for indice, grupo in enumerate(grupos_de_botoes):
            for botao in grupo:
                actions_layout.addWidget(botao)
            if indice < len(grupos_de_botoes) - 1:
                actions_layout.addWidget(self._separador_vertical())
        # Os icones vem do TEXTO de cada botao (ver app/ui/icones.py): a
        # mesma acao fica com a mesma cara em todas as paginas.
        decorar_barra(actions_layout)
        actions_layout.addStretch()

        self.pesquisa_input = CampoPesquisa(
            placeholder=(
                "Pesquisar chave, opção, referência, descrição, tipo, família ou operação…"
            ),
            largura_max=380,
        )
        self.pesquisa_input.setToolTip(
            "Filtra as linhas deste orçamento à medida que escreve. "
            "Use espaços ou % para combinar termos."
        )
        self.pesquisa_input.pesquisa_mudou.connect(self._aplicar_filtros)

        self.faixas_check = QCheckBox("Faixas de grupo na tabela")
        self.faixas_check.setChecked(True)
        self.faixas_check.setToolTip(
            "Separar as linhas por grupo, com uma faixa por cima de cada bloco. "
            "Desligue para ver a tabela corrida."
        )
        self.faixas_check.stateChanged.connect(lambda _=0: self._aplicar_filtros())

        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.setToolTip(
            "Mostrar também as linhas desativadas deste orçamento."
        )
        self.mostrar_inativas_check.stateChanged.connect(
            lambda _=0: self._aplicar_filtros()
        )

        self.limpar_filtros_button = BotaoLimparFiltros()
        self.limpar_filtros_button.setToolTip(
            "Repor a pesquisa, o grupo e a chave escolhidos e voltar a abrir "
            "todos os blocos."
        )
        self.limpar_filtros_button.clicked.connect(self.limpar_filtros)

        self.navegador = NavegadorChavesValueset(mostrar_editadas=True)
        self.navegador.filtro_mudou.connect(self._aplicar_filtros)

        self.toggle_navegador_button = QPushButton("Ocultar navegador")
        self.toggle_navegador_button.setToolTip(
            "Esconder ou mostrar a lista de chaves à esquerda, para dar toda a "
            "largura à tabela."
        )
        self.toggle_navegador_button.clicked.connect(self.alternar_navegador)

        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(6)
        filtros_layout.addWidget(self.pesquisa_input)
        filtros_layout.addWidget(self.limpar_filtros_button)
        filtros_layout.addWidget(self._separador_vertical())
        filtros_layout.addWidget(self.mostrar_inativas_check)
        filtros_layout.addWidget(self.faixas_check)
        filtros_layout.addWidget(self.toggle_navegador_button)
        filtros_layout.addWidget(self._separador_vertical())
        filtros_layout.addWidget(self.navegador.chips, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoValuesetStatus")

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
        if ligar_persistencia_larguras(self.table, "valueset_orcamento"):
            self._larguras_iniciais_aplicadas = True
        configurar_tabela_valueset(self.table, "valueset_orcamento")
        self.table.cellClicked.connect(self._handle_click_celula)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.navegador)
        self.splitter.addWidget(self.table)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        if not ligar_persistencia_splitter(self.splitter, "valueset_orcamento_chaves"):
            self.splitter.setSizes([260, 900])

        layout = QVBoxLayout()
        # Cada linha que se poupa aqui em cima é uma linha de tabela a mais.
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(7)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addLayout(filtros_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.splitter, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def _separador_vertical(self) -> QFrame:
        """Barra fina que separa duas famílias de botões na mesma linha."""
        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.VLine)
        separador.setFrameShadow(QFrame.Shadow.Plain)
        separador.setStyleSheet(f"color: {CINZA_CASTANHO};")
        return separador

    def carregar(self) -> None:
        """Load the ValueSet lines of the budget version."""
        timer = getattr(self, "_prioridade_flash_timer", None)
        if timer is not None:
            timer.stop()
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = OrcamentoValuesetLinhaService(session).listar_linhas_da_versao(
                    self.orcamento_versao_id
                )
                operacoes_codigos = {
                    operacao.id: operacao.codigo
                    for operacao in DefOperacaoService(session).listar_operacoes()
                }
                # Uma consulta para as operações de todas as linhas: com ~100
                # linhas, uma por linha fazia a página demorar a abrir.
                ligacoes_por_linha = OrcamentoValuesetLinhaOperacaoService(
                    session
                ).listar_operacoes_ativas_de_linhas([linha.id for linha in linhas])
                self._operacoes_por_linha = {
                    linha_id: "; ".join(
                        operacoes_codigos.get(
                            ligacao.def_operacao_id, f"#{ligacao.def_operacao_id}"
                        )
                        for ligacao in ligacoes
                    )
                    for linha_id, ligacoes in ligacoes_por_linha.items()
                }
                self.navegador.definir_metas(
                    metas_por_codigo(DefValuesetChaveService(session).listar_chaves())
                )
        except SQLAlchemyError as error:
            self._todas_linhas = []
            self._operacoes_por_linha = {}
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar o ValueSet do orcamento.", error)
            )
            return

        self._todas_linhas = linhas
        self._aplicar_filtros()

    def _aplicar_filtros(self, _texto: str = "") -> None:
        """Filtra em memória e repinta a tabela, os chips e o navegador."""
        pesquisadas = self._linhas_pesquisadas()
        linhas = [l for l in pesquisadas if self.navegador.aceita(l)]

        self.navegador.atualizar(pesquisadas)
        self._preencher(linhas)

        if not self._todas_linhas:
            self.status_label.setText(
                "Sem ValueSet. Use 'Importar Modelo' para preencher este orçamento."
            )
            return
        if not linhas:
            self.status_label.setText(
                "Nenhuma linha corresponde à pesquisa ou aos filtros."
            )
            return

        editadas = sum(1 for l in linhas if l.editado_localmente)
        estado = f"Linhas encontradas: {len(linhas)}."
        if editadas:
            estado += f" {editadas} afinada(s) à mão neste orçamento."
        self.status_label.setText(estado + self.navegador.sufixo_estado())
        self._avisar_prioridades_repetidas(linhas)

    def _linhas_pesquisadas(self) -> list[OrcamentoValuesetLinhaResumo]:
        """As linhas que passam o "mostrar inativas" e a caixa de pesquisa.

        É esta a base dos chips e do navegador: as contagens que eles mostram
        são as da pesquisa, e não mudam por se estar a ver só um grupo.
        """
        linhas = self._todas_linhas
        if not self.mostrar_inativas_check.isChecked():
            linhas = [linha for linha in linhas if linha.ativo]
        return filtrar_linhas_valueset_modelo(
            linhas,
            self.pesquisa_input.texto(),
            self._operacoes_por_linha,
        )

    def limpar_filtros(self) -> None:
        """Repor a pesquisa e tudo o que o navegador esteja a filtrar."""
        self.pesquisa_input.limpar()
        self.navegador.limpar_filtros()

    def alternar_navegador(self) -> None:
        """Esconder/mostrar o painel das chaves, para dar largura à tabela."""
        visivel = not self.navegador.isVisible()
        self.navegador.setVisible(visivel)
        self.toggle_navegador_button.setText(
            "Ocultar navegador" if visivel else "Mostrar navegador"
        )

    def _handle_click_celula(self, row: int, _column: int) -> None:
        """Um clique numa faixa fecha ou abre o grupo dela."""
        grupo = self._faixas_by_row.get(row)
        if grupo is not None:
            self.navegador.alternar_grupo_fechado(grupo)

    def _preencher(self, linhas: list[OrcamentoValuesetLinhaResumo]) -> None:
        """Fill the table with ValueSet lines."""
        self._linhas_by_row = {}
        self._faixas_by_row = {}
        self.table.clearSpans()

        if self.faixas_check.isChecked():
            self._preencher_com_faixas(linhas)
        else:
            self._preencher_corrido(linhas)

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

    def _preencher_corrido(
        self, linhas: list[OrcamentoValuesetLinhaResumo]
    ) -> None:
        """A tabela como sempre foi: uma linha por linha, sem faixas."""
        estados = preparar_linhas_valueset(linhas)
        self.table.setRowCount(len(estados))
        for row_index, estado in enumerate(estados):
            self._escrever_linha(row_index, estado)

    def _preencher_com_faixas(
        self, linhas: list[OrcamentoValuesetLinhaResumo]
    ) -> None:
        """A tabela com uma faixa por grupo, que fecha e abre com um clique.

        Só de grupo, e não de chave: aqui há ~70 chaves para ~100 linhas, e uma
        faixa por chave quase duplicava o que está no ecrã sem ganhar nada.
        """
        ordenadas = [
            estado.linha for estado in preparar_linhas_valueset(linhas)
        ]
        self.table.setRowCount(0)
        row_index = 0

        for grupo in self.navegador.agrupar_contiguo(ordenadas):
            fechado = self.navegador.grupo_fechado(grupo.codigo)
            editadas = sum(
                1
                for chave in grupo.chaves
                for l in chave.linhas
                if l.editado_localmente
            )
            texto = (
                f"{'▸' if fechado else '▾'} {grupo.rotulo.upper()} — "
                f"{grupo.total} linha(s)"
            )
            if editadas:
                texto += f" · ✎ {editadas} afinada(s) à mão"
            self.table.insertRow(row_index)
            escrever_faixa_grupo(
                self.table,
                row_index,
                texto=texto,
                colunas=len(self.TABLE_HEADERS),
            )
            self._faixas_by_row[row_index] = grupo.codigo
            row_index += 1
            if fechado:
                continue

            do_grupo = [l for chave in grupo.chaves for l in chave.linhas]
            for estado in preparar_linhas_valueset(do_grupo, ordenar=False):
                self.table.insertRow(row_index)
                self._escrever_linha(row_index, estado)
                row_index += 1

    def _escrever_linha(self, row_index: int, estado) -> None:
        """Escreve uma linha de dados do ValueSet."""
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

    def _criar_linha_local(self, form_data, *, linha_origem=None):
        """Create one local option and copy source operations atomically."""
        with SessionLocal() as session:
            service = OrcamentoValuesetLinhaService(session)
            existentes = service.listar_por_chave(
                self.orcamento_versao_id, form_data.chave
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
                CriarOrcamentoValuesetLinhaData(
                    orcamento_versao_id=self.orcamento_versao_id,
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
                    origem_modelo_id=None,
                    origem_modelo_codigo=None,
                    editado_localmente=True,
                    observacoes=form_data.observacoes,
                    ativo=form_data.ativo,
                ),
                commit=False,
            )

            if linha_origem is not None:
                operacoes_service = OrcamentoValuesetLinhaOperacaoService(session)
                operacoes = operacoes_service.listar_operacoes_da_linha(
                    linha_origem.id
                )
                operacoes_service.copiar_operacoes_de(operacoes, result.id)

            session.commit()
            return result

    def abrir_nova_linha(self) -> None:
        """Create a ValueSet option local to this budget."""
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

        dialog = OrcamentoValuesetLinhaDialog(parent=self, on_save=handle_save)
        if dialog.exec() and criada is not None:
            self.carregar()
            prioridade = criada.prioridade if criada.prioridade is not None else "vazia"
            self.status_label.setText(
                f"Nova opção local criada com prioridade {prioridade}."
            )

    def abrir_editar_linha(self) -> None:
        """Open the edit dialog for the selected ValueSet line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        saved = False
        saved_as = None

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
                            preco_orla_0_4_m2=form_data.preco_orla_0_4_m2,
                            preco_orla_1_0_m2=form_data.preco_orla_1_0_m2,
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

        dialog = OrcamentoValuesetLinhaDialog(
            linha,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha ValueSet atualizada.")
        elif saved_as is not None:
            self.carregar()
            prioridade = (
                saved_as.prioridade if saved_as.prioridade is not None else "vazia"
            )
            self.status_label.setText(
                "Linha gravada como nova opção local, com as operações da original "
                f"e prioridade {prioridade}."
            )
        elif dialog.operacoes_alteradas:
            self.carregar()
            self.status_label.setText("Operações da linha atualizadas.")

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        # Duplo clique numa faixa é só o segundo clique a fechar e a reabrir o
        # grupo — não há linha nenhuma para editar.
        if row in self._faixas_by_row:
            return
        self.abrir_editar_linha()

    def copiar_dados(self) -> None:
        """Copy the materia-prima snapshot and operations of the selected line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return

        try:
            with SessionLocal() as session:
                type(self)._copied_snapshot = OrcamentoValuesetLinhaService(
                    session
                ).copiar_snapshot_linha(linha.id)
                type(self)._copied_operacoes = OrcamentoValuesetLinhaOperacaoService(
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
                    OrcamentoValuesetLinhaService(session).aplicar_snapshot_linha(
                        linha.id, snapshot, commit=False
                    )
                    if colar_operacoes:
                        OrcamentoValuesetLinhaOperacaoService(
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
        if item is not None and item.row() in self._faixas_by_row:
            return  # faixa de grupo: não há linha sobre que agir
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
