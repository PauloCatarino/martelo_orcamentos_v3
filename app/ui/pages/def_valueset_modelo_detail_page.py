"""Detail page for one ValueSet model and its lines."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem
from app.domain.valueset_modelo_pesquisa import filtrar_linhas_valueset_modelo
from app.domain.valueset_navegador_chaves import (
    MetaChave,
    agrupar_linhas,
    agrupar_linhas_contiguas,
    metas_por_codigo,
    normalizar_chave,
    rotulo_grupo,
)
from app.services.def_valueset_chave_service import DefValuesetChaveService
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
from app.services.def_valueset_chave_copia_service import (
    DefValuesetChaveCopiaService,
)
from app.services.def_valueset_operacao_propagacao_service import (
    DefValuesetOperacaoPropagacaoService,
)
from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
from app.ui.dialogs.copiar_chaves_valueset_dialog import CopiarChavesValuesetDialog
from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog
from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog
from app.ui.dialogs.propagar_operacoes_valueset_modelo_dialog import (
    PropagarOperacoesValuesetModeloDialog,
)
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.helpers.valueset_modelo_publicacao import (
    publicar_modelo_valueset_para_todos,
)
from app.ui.helpers.valueset_prioridades import (
    avisar_prioridade_repetida_apos_colagem,
)
from app.ui.helpers.valueset_precos import (
    atualizacoes_de_divergencias,
    detetar_divergencias_valueset,
)
from app.ui.tema import (
    BEGE_AREIA,
    CASTANHO_ESCURO,
    CINZA_CASTANHO,
    CINZA_ESCURO,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import BotaoLimparFiltros, CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter
from app.ui.widgets.estilo_tabela_orcamentos import estilo_arvore
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
from app.ui.icones import decorar_barra, icone


class DefValuesetModeloDetailPage(QWidget):
    """Detail page showing one ValueSet model and managing its lines."""

    # Partilhado entre instâncias para permitir copiar de um modelo e colar
    # noutro depois de regressar à lista.
    _copied_snapshot: dict | None = None
    _copied_operacoes: list | None = None

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
        self._todas_linhas: list[DefValuesetModeloLinhaResumo] = []
        self._operacoes_por_linha: dict[int, str] = {}
        # Vocabulário das chaves (nome, grupo, ordem): é o que dá o navegador.
        self._metas_chaves: dict[str, MetaChave] = {}
        # Filtro em curso vindo do navegador / dos chips de grupo.
        self._grupo_selecionado: str | None = None
        self._chave_selecionada: str | None = None
        # O grupo veio a reboque de uma chave (e sai com ela), ou foi escolhido?
        self._grupo_implicito = False
        # Cabeçalhos fechados na tabela, e a que linha corresponde cada um.
        self._grupos_fechados: set[str] = set()
        self._chaves_fechadas: set[str] = set()
        self._cabecalhos_by_row: dict[int, tuple[str, str]] = {}
        self._botoes_chips: list[QPushButton] = []

        self.cabecalho = BarraCabecalho(
            f"Modelo ValueSet: {modelo.nome}",
            [f"Configurações > Modelos ValueSet > {modelo.nome}"],
        )

        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        info_campos = [
            ("Código", modelo.codigo),
            ("Nome", modelo.nome),
            ("Tipo", modelo.tipo or ""),
            ("Âmbito", modelo.ambito),
            ("Ativo", self._format_bool(modelo.ativo)),
        ]
        for indice, (label, value) in enumerate(info_campos):
            titulo = QLabel(f"{label}:")
            titulo_font = titulo.font()
            titulo_font.setBold(True)
            titulo.setFont(titulo_font)
            conteudo = QLabel(value)
            conteudo.setToolTip(value)
            info_layout.addWidget(titulo)
            info_layout.addWidget(conteudo)
            if indice < len(info_campos) - 1:
                separador = QLabel("|")
                separador.setObjectName("valuesetModeloInfoSeparador")
                info_layout.addSpacing(6)
                info_layout.addWidget(separador)
                info_layout.addSpacing(6)
        info_layout.addStretch()

        self.new_button = QPushButton("Nova Linha")
        self.new_button.clicked.connect(self.abrir_nova_linha)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.copy_button = QPushButton("Copiar Dados")
        self.copy_button.setToolTip(
            "Copiar prioridade, dados de material e operações da linha selecionada (Ctrl+C)."
        )
        self.copy_button.clicked.connect(self.copiar_dados)
        self.paste_button = QPushButton("Colar Dados")
        self.paste_button.setToolTip(
            "Colar numa linha existente, mantendo chave, opção e estrutura do destino (Ctrl+V)."
        )
        self.paste_button.clicked.connect(self.colar_dados)
        self.propagate_operations_button = QPushButton("Propagar Operações…")
        self.propagate_operations_button.setToolTip(
            "Selecionar outras linhas com a mesma chave e Ref LE e substituir as operações."
        )
        self.propagate_operations_button.clicked.connect(self.propagar_operacoes)
        self.copiar_chaves_button = QPushButton("Copiar Chaves…")
        self.copiar_chaves_button.setToolTip(
            "Levar chaves inteiras deste modelo para outros modelos. Mostra "
            "primeiro quantas linhas seriam criadas em cada um; nada é apagado."
        )
        self.copiar_chaves_button.clicked.connect(self.copiar_chaves_para_modelos)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.subir_button = QPushButton("↑")
        self.subir_button.setToolTip(
            "Mover as linhas selecionadas uma posição para cima "
            "(Ctrl/Shift para escolher várias)"
        )
        self.subir_button.clicked.connect(lambda: self.mover_linha(para_cima=True))
        self.descer_button = QPushButton("↓")
        self.descer_button.setToolTip(
            "Mover as linhas selecionadas uma posição para baixo "
            "(Ctrl/Shift para escolher várias)"
        )
        self.descer_button.clicked.connect(lambda: self.mover_linha(para_cima=False))
        self.agrupar_button = QPushButton("Agrupar por chave")
        self.agrupar_button.setToolTip(
            "Voltar a arrumar todas as linhas pela ordem do navegador: grupo, "
            "depois a chave, depois a prioridade. Desfaz a ordenação feita com "
            "as setas."
        )
        self.agrupar_button.clicked.connect(self.agrupar_por_chave)
        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(
            lambda _=0: self._aplicar_filtro_linhas()
        )
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_linhas)
        self.check_prices_button = QPushButton("Verificar preços…")
        self.check_prices_button.clicked.connect(self.verificar_precos)
        self.toggle_navegador_button = QPushButton("Ocultar navegador")
        self.toggle_navegador_button.setToolTip(
            "Esconder ou mostrar a lista de chaves à esquerda, para dar toda a "
            "largura à tabela."
        )
        self.toggle_navegador_button.clicked.connect(self.alternar_navegador)
        self.back_button = QPushButton("Voltar à lista")
        self.back_button.setIcon(icone("acao_voltar"))
        self.back_button.setToolTip("Voltar à lista, sem gravar o que estiver por gravar.")
        self.back_button.clicked.connect(self._handle_back)

        # Os botões vão por famílias, separados por uma barra vertical: mexer
        # na linha, copiar conteúdo, ordenar, ir à base, e mudar a vista. Antes
        # estavam todos seguidos e era preciso ler os nomes um a um para achar
        # o que se queria.
        self.mostrar_inativas_check.setToolTip(
            "Mostrar também as linhas desativadas deste modelo."
        )
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)
        grupos_de_botoes = [
            [self.new_button, self.edit_button, self.toggle_button],
            [
                self.copy_button,
                self.paste_button,
                self.propagate_operations_button,
                self.copiar_chaves_button,
            ],
            [self.subir_button, self.descer_button, self.agrupar_button],
            [self.refresh_button, self.check_prices_button],
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
        actions_layout.addWidget(self.back_button)

        self.pesquisa_input = CampoPesquisa(
            placeholder=(
                "Pesquisar chave, opção, referência, descrição, tipo, família ou operação…"
            ),
            largura_max=380,
        )
        self.pesquisa_input.setToolTip(
            "Filtra as linhas deste modelo à medida que escreve. "
            "Use espaços ou % para combinar termos."
        )
        self.pesquisa_input.pesquisa_mudou.connect(self._aplicar_filtro_linhas)

        self.cabecalhos_grupo_check = QCheckBox("Cabeçalhos de grupo na tabela")
        self.cabecalhos_grupo_check.setChecked(True)
        self.cabecalhos_grupo_check.setToolTip(
            "Separar as linhas por grupo e por chave, com uma faixa por cima de "
            "cada bloco. Desligue para ver a tabela corrida."
        )
        self.cabecalhos_grupo_check.stateChanged.connect(
            lambda _=0: self._aplicar_filtro_linhas()
        )
        self.limpar_filtros_button = BotaoLimparFiltros()
        self.limpar_filtros_button.setToolTip(
            "Repor a pesquisa, o grupo e a chave escolhidos e voltar a abrir "
            "todos os blocos."
        )
        self.limpar_filtros_button.clicked.connect(self.limpar_filtros)

        # Chips de grupo: atalho para o grupo todo, sem passar pela árvore.
        # Vão na mesma linha da pesquisa — ocupavam uma linha inteira só para
        # eles, e é altura que faz falta às colunas da tabela.
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(4)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_widget = QWidget()
        self.chips_widget.setLayout(self.chips_layout)

        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(6)
        filtros_layout.addWidget(self.pesquisa_input)
        filtros_layout.addWidget(self.limpar_filtros_button)
        filtros_layout.addWidget(self._separador_vertical())
        filtros_layout.addWidget(self.mostrar_inativas_check)
        filtros_layout.addWidget(self.cabecalhos_grupo_check)
        filtros_layout.addWidget(self.toggle_navegador_button)
        filtros_layout.addWidget(self._separador_vertical())
        filtros_layout.addWidget(self.chips_widget, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetModeloDetailStatus")

        self.table = QTableWidget(0, len(self.LINHA_HEADERS))
        self.table.setHorizontalHeaderLabels(self.LINHA_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Várias linhas de cada vez (Ctrl/Shift), para as mover em bloco.
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
        if ligar_persistencia_larguras(self.table, "valueset_modelo"):
            self._larguras_iniciais_aplicadas = True
        configurar_tabela_valueset(self.table, "valueset_modelo")
        self.table.cellClicked.connect(self._handle_click_celula)

        self.navegador = self._criar_navegador()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.navegador)
        self.splitter.addWidget(self.table)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        if not ligar_persistencia_splitter(self.splitter, "valueset_modelo_chaves"):
            self.splitter.setSizes([260, 900])

        layout = QVBoxLayout()
        # Margens e espaçamento apertados de propósito: cada linha que se poupa
        # aqui em cima é uma linha de tabela que se vê lá em baixo.
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(7)
        layout.addWidget(self.cabecalho)
        layout.addLayout(info_layout)
        layout.addLayout(actions_layout)
        layout.addLayout(filtros_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.splitter, stretch=1)

        self.setLayout(layout)
        self.carregar_linhas()

    def _separador_vertical(self) -> QFrame:
        """Barra fina que separa duas famílias de botões na mesma linha."""
        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.VLine)
        separador.setFrameShadow(QFrame.Shadow.Plain)
        separador.setStyleSheet(f"color: {CINZA_CASTANHO};")
        return separador

    def _criar_navegador(self) -> QWidget:
        """Painel esquerdo: os grupos e as chaves deste modelo."""
        titulo = QLabel("Navegador de chaves")
        fonte = titulo.font()
        fonte.setBold(True)
        titulo.setFont(fonte)
        titulo.setToolTip(
            "As chaves deste modelo, arrumadas pelo grupo do vocabulário. "
            "Clique numa chave para filtrar a tabela; clique outra vez para "
            "mostrar tudo."
        )

        self.arvore_chaves = QTreeWidget()
        self.arvore_chaves.setColumnCount(2)
        self.arvore_chaves.setHeaderLabels(["Chave", "Linhas"])
        self.arvore_chaves.setRootIsDecorated(True)
        self.arvore_chaves.setAlternatingRowColors(True)
        self.arvore_chaves.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
        )
        self.arvore_chaves.setStyleSheet(estilo_arvore())
        self.arvore_chaves.setToolTip(
            "Clique numa chave para filtrar a tabela por ela; clique num grupo "
            "para filtrar o grupo inteiro."
        )
        cabecalho = self.arvore_chaves.header()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecalho.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setStretchLastSection(False)
        self.arvore_chaves.itemClicked.connect(self._handle_clique_navegador)

        painel = QWidget()
        painel_layout = QVBoxLayout()
        painel_layout.setContentsMargins(0, 0, 0, 0)
        painel_layout.setSpacing(6)
        painel_layout.addWidget(titulo)
        painel_layout.addWidget(self.arvore_chaves, stretch=1)
        painel.setLayout(painel_layout)
        return painel

    def carregar_linhas(self) -> None:
        """Load the model lines into the table."""
        timer = getattr(self, "_prioridade_flash_timer", None)
        if timer is not None:
            timer.stop()
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = DefValuesetModeloLinhaService(session).listar_linhas_do_modelo(
                    self.modelo.id
                )
                operacoes = {
                    operacao.id: operacao.codigo
                    for operacao in DefOperacaoService(session).listar_operacoes()
                }
                # Uma consulta para as operações de todas as linhas: com ~100
                # linhas, uma consulta por linha fazia a página demorar a abrir.
                ligacoes_por_linha = DefValuesetModeloLinhaOperacaoService(
                    session
                ).listar_operacoes_ativas_de_linhas([linha.id for linha in linhas])
                self._operacoes_por_linha = {
                    linha_id: "; ".join(
                        operacoes.get(
                            ligacao.def_operacao_id, f"#{ligacao.def_operacao_id}"
                        )
                        for ligacao in ligacoes
                    )
                    for linha_id, ligacoes in ligacoes_por_linha.items()
                }
                self._metas_chaves = metas_por_codigo(
                    DefValuesetChaveService(session).listar_chaves()
                )
        except SQLAlchemyError as error:
            self._todas_linhas = []
            self._operacoes_por_linha = {}
            self._metas_chaves = {}
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar as linhas do modelo.", error)
            )
            return

        self._todas_linhas = linhas
        self._aplicar_filtro_linhas()

    def _aplicar_filtro_linhas(self, _texto: str = "") -> None:
        """Filtra em memória as linhas e operações do modelo atual."""
        pesquisadas = self._linhas_pesquisadas()
        linhas = [
            linha for linha in pesquisadas if self._passa_no_navegador(linha)
        ]

        self._desenhar_chips(pesquisadas)
        self._desenhar_navegador(pesquisadas)
        self._preencher(linhas)

        if not linhas:
            if self._ha_filtro_ativo():
                self.status_label.setText(
                    "Nenhuma linha corresponde à pesquisa ou aos filtros."
                )
            else:
                self.status_label.setText("Sem linhas neste modelo.")
        else:
            self.status_label.setText(
                f"Linhas encontradas: {len(linhas)}.{self._sufixo_filtros()}"
            )
            self._avisar_prioridades_repetidas(linhas)

    def _linhas_pesquisadas(self) -> list[DefValuesetModeloLinhaResumo]:
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

    def _passa_no_navegador(self, linha: DefValuesetModeloLinhaResumo) -> bool:
        """Diz se a linha sobrevive ao grupo/chave escolhidos à esquerda."""
        meta = self._meta_da_linha(linha)
        if self._grupo_selecionado is not None and meta.grupo != self._grupo_selecionado:
            return False
        if (
            self._chave_selecionada is not None
            and meta.codigo != self._chave_selecionada
        ):
            return False
        return True

    def _meta_da_linha(self, linha: DefValuesetModeloLinhaResumo) -> MetaChave:
        """O que o vocabulário sabe da chave desta linha (órfã: "Sem grupo")."""
        codigo = normalizar_chave(getattr(linha, "chave", None))
        meta = self._metas_chaves.get(codigo)
        if meta is not None:
            return meta
        return MetaChave(codigo=codigo, nome=codigo)

    def _ha_filtro_ativo(self) -> bool:
        """Há pesquisa escrita ou grupo/chave escolhidos?"""
        return bool(
            self.pesquisa_input.texto().strip()
            or self._grupo_selecionado is not None
            or self._chave_selecionada is not None
        )

    def _sufixo_filtros(self) -> str:
        """Diz na linha de estado que grupo/chave estão a filtrar."""
        partes = []
        if self._grupo_selecionado is not None:
            partes.append(f"grupo: {rotulo_grupo(self._grupo_selecionado)}")
        if self._chave_selecionada is not None:
            partes.append(f"chave: {self._chave_selecionada}")
        if not partes:
            return ""
        return "  ·  " + "  ·  ".join(partes)

    def limpar_filtros(self) -> None:
        """Repor a pesquisa, o grupo, a chave e os blocos fechados."""
        self._grupo_selecionado = None
        self._grupo_implicito = False
        self._chave_selecionada = None
        self._grupos_fechados.clear()
        self._chaves_fechadas.clear()
        self.pesquisa_input.limpar()
        self._aplicar_filtro_linhas()

    def alternar_navegador(self) -> None:
        """Esconder/mostrar o painel das chaves, para dar largura à tabela."""
        visivel = not self.navegador.isVisible()
        self.navegador.setVisible(visivel)
        self.toggle_navegador_button.setText(
            "Ocultar navegador" if visivel else "Mostrar navegador"
        )

    def _desenhar_chips(self, linhas: list[DefValuesetModeloLinhaResumo]) -> None:
        """Um botão por grupo com a contagem, mais "Todos"."""
        # Esvaziar o layout INTEIRO, e não só os botões: o espaçador do fim
        # também é um item, e deixá-lo lá empurrava os chips mais para a
        # direita a cada redesenho, até irem parar ao canto.
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._botoes_chips = []

        grupos = agrupar_linhas(linhas, self._metas_chaves)
        entradas: list[tuple[str | None, str, int]] = [
            (None, "Todos", len(linhas))
        ]
        entradas.extend(
            (grupo.codigo, grupo.rotulo, grupo.total) for grupo in grupos
        )

        for codigo, rotulo, total in entradas:
            botao = QPushButton(f"{rotulo}  ({total})")
            botao.setCheckable(True)
            botao.setChecked(self._grupo_selecionado == codigo)
            botao.setToolTip(
                "Mostrar todas as chaves do modelo."
                if codigo is None
                else f"Mostrar só as chaves do grupo {rotulo}."
            )
            botao.clicked.connect(
                lambda _checked=False, alvo=codigo: self._escolher_grupo(alvo)
            )
            self.chips_layout.addWidget(botao)
            self._botoes_chips.append(botao)

        self.chips_layout.addStretch()

    def _escolher_grupo(self, codigo: str | None) -> None:
        """Filtrar por um grupo (ou desligar o filtro, se já era esse)."""
        if codigo is None or self._grupo_selecionado == codigo:
            self._grupo_selecionado = None
        else:
            self._grupo_selecionado = codigo
        self._grupo_implicito = False
        self._chave_selecionada = None
        self._aplicar_filtro_linhas()

    def _desenhar_navegador(
        self, linhas: list[DefValuesetModeloLinhaResumo]
    ) -> None:
        """Reconstruir a árvore de grupos e chaves do painel esquerdo."""
        arvore = getattr(self, "arvore_chaves", None)
        if arvore is None:
            return

        arvore.blockSignals(True)
        arvore.clear()
        for grupo in agrupar_linhas(linhas, self._metas_chaves):
            no_grupo = QTreeWidgetItem([grupo.rotulo, str(grupo.total)])
            fonte = no_grupo.font(0)
            fonte.setBold(True)
            no_grupo.setFont(0, fonte)
            no_grupo.setForeground(0, QBrush(QColor(CASTANHO_ESCURO)))
            no_grupo.setData(0, Qt.ItemDataRole.UserRole, ("grupo", grupo.codigo))
            no_grupo.setToolTip(0, f"Filtrar pelo grupo {grupo.rotulo}.")
            arvore.addTopLevelItem(no_grupo)

            for chave in grupo.chaves:
                no_chave = QTreeWidgetItem([chave.nome, str(chave.total)])
                no_chave.setData(
                    0, Qt.ItemDataRole.UserRole, ("chave", chave.codigo)
                )
                no_chave.setToolTip(
                    0,
                    f"{chave.codigo} — {chave.total} opção(ões). "
                    "Clique para filtrar a tabela por esta chave.",
                )
                if chave.codigo == self._chave_selecionada:
                    fonte_chave = no_chave.font(0)
                    fonte_chave.setBold(True)
                    no_chave.setFont(0, fonte_chave)
                no_grupo.addChild(no_chave)

            no_grupo.setExpanded(grupo.codigo not in self._grupos_fechados)
        arvore.blockSignals(False)

    def _handle_clique_navegador(self, item: QTreeWidgetItem, _coluna: int) -> None:
        """Clicar numa chave filtra a tabela; clicar num grupo filtra o grupo."""
        dados = item.data(0, Qt.ItemDataRole.UserRole)
        if not dados:
            return

        tipo, codigo = dados
        if tipo == "grupo":
            self._escolher_grupo(codigo)
            return

        if self._chave_selecionada == codigo:
            self._chave_selecionada = None
            # O grupo só ficou escolhido para acompanhar a chave: sai com ela,
            # senão o segundo clique deixava metade do filtro para trás.
            if self._grupo_implicito:
                self._grupo_selecionado = None
                self._grupo_implicito = False
        else:
            self._chave_selecionada = codigo
            pai = item.parent()
            dados_pai = pai.data(0, Qt.ItemDataRole.UserRole) if pai else None
            if dados_pai and self._grupo_selecionado != dados_pai[1]:
                self._grupo_selecionado = dados_pai[1]
                self._grupo_implicito = True
        self._aplicar_filtro_linhas()

    def mover_linha(self, *, para_cima: bool) -> None:
        """Move the selected line(s) one position up or down."""
        ids_selecionados = self._ids_selecionados()
        if not ids_selecionados:
            self.status_label.setText("Selecione uma linha para mover.")
            return

        try:
            with SessionLocal() as session:
                movida = DefValuesetModeloLinhaService(session).mover_linhas(
                    self.modelo.id,
                    ids_selecionados,
                    para_cima=para_cima,
                    # Só se movem entre as linhas à vista: com as inativas
                    # escondidas, trocar com uma delas não se veria.
                    ids_visiveis=self._ids_visiveis(),
                )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível mover a linha.", error)
            )
            return

        if not movida:
            extremo = "primeira" if para_cima else "última"
            self.status_label.setText(f"A seleção já está na {extremo} posição.")
            return

        self.carregar_linhas()
        self._selecionar_linhas(ids_selecionados)
        total = len(ids_selecionados)
        self.status_label.setText(
            "Linha movida." if total == 1 else f"{total} linhas movidas."
        )

    def _ids_visiveis(self) -> list[int]:
        """Ids of the lines currently in the table, in display order."""
        return [
            linha.id
            for _row, linha in sorted(self._linhas_by_row.items())
        ]

    def _ids_selecionados(self) -> list[int]:
        """Ids of the selected lines, in display order."""
        modelo_selecao = self.table.selectionModel()
        if modelo_selecao is None:
            return []

        linhas = sorted(indice.row() for indice in modelo_selecao.selectedRows())
        if not linhas and self.table.currentRow() >= 0:
            linhas = [self.table.currentRow()]

        return [
            self._linhas_by_row[row].id for row in linhas if row in self._linhas_by_row
        ]

    def _selecionar_linhas(self, linha_ids: list[int]) -> None:
        """Keep the moved lines selected after the table is rebuilt."""
        alvos = set(linha_ids)
        modelo_selecao = self.table.selectionModel()
        if modelo_selecao is None:
            return

        modelo_selecao.clearSelection()
        flags = (
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows
        )
        for row, linha in self._linhas_by_row.items():
            if linha.id in alvos:
                modelo_selecao.select(self.table.model().index(row, 0), flags)

    def agrupar_por_chave(self) -> None:
        """Rearrange every line by key, undoing the manual ordering."""
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "Voltar a arrumar todas as linhas pela ordem do navegador "
            "(grupo, chave, prioridade)? A ordenação que fez com as setas é "
            "substituída.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                total = DefValuesetModeloLinhaService(session).agrupar_linhas_por_chave(
                    self.modelo.id
                )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível arrumar as linhas.", error)
            )
            return

        self.carregar_linhas()
        self.status_label.setText(
            f"{total} linhas arrumadas por grupo e por chave."
        )

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
        saved_as_operacoes = 0
        saved_as_substituiu = False
        modelo_novo: DefValuesetModeloResumo | None = None

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as, saved_as_codigo, saved_as_linhas
            nonlocal saved_as_operacoes, saved_as_substituiu, modelo_novo

            try:
                dados_novos = self._criar_modelo_data_from_form_data(form_data)
                if (form_data.ambito or "").strip().upper() == "GLOBAL":
                    result = publicar_modelo_valueset_para_todos(
                        dialog,
                        self.modelo.id,
                        dados_novos,
                    )
                    if result is None:
                        return False
                    saved_as_substituiu = True
                    saved_as_operacoes = result.operacoes_copiadas
                else:
                    with SessionLocal() as session:
                        result = DefValuesetModeloService(session).duplicar_modelo(
                            self.modelo.id,
                            dados_novos,
                        )
            except IntegrityError:
                dialog.set_error("Já existe um modelo com esse código.")
                return False
            except PermissionError as error:
                dialog.set_error(str(error))
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

        if saved_as_substituiu:
            mensagem = (
                f"Modelo global {saved_as_codigo} substituído: "
                f"{saved_as_linhas} linhas e {saved_as_operacoes} operações copiadas."
            )
        else:
            mensagem = f"Modelo gravado como {saved_as_codigo}."
        if self.on_modelo_duplicado is not None:
            self.on_modelo_duplicado(modelo_novo, mensagem)
            return

        if saved_as_substituiu:
            self.status_label.setText(mensagem)
        else:
            self.status_label.setText(f"{mensagem} {saved_as_linhas} linhas copiadas.")

    def _preencher(self, linhas: list[DefValuesetModeloLinhaResumo]) -> None:
        """Fill the table with model lines."""
        self._linhas_by_row = {}
        self._cabecalhos_by_row = {}
        self.table.clearSpans()

        if self.cabecalhos_grupo_check.isChecked():
            self._preencher_com_cabecalhos(linhas)
        else:
            self._preencher_corrido(linhas)

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

    def _preencher_corrido(self, linhas: list[DefValuesetModeloLinhaResumo]) -> None:
        """A tabela como sempre foi: uma linha por linha, sem faixas."""
        # As linhas já vêm na ordem que o utilizador arrumou (coluna Ordem);
        # re-ordenar aqui por chave desfazia o trabalho das setas.
        estados = preparar_linhas_valueset(linhas, ordenar=False)
        self.table.setRowCount(len(estados))
        for row_index, estado in enumerate(estados):
            self._escrever_linha(row_index, estado)

    def _preencher_com_cabecalhos(
        self, linhas: list[DefValuesetModeloLinhaResumo]
    ) -> None:
        """A tabela com uma faixa por grupo e outra por chave.

        As faixas de chave fecham e abrem com um clique: num modelo de ~200
        linhas, dá para fechar o que já está tratado e trabalhar só no resto.

        As faixas seguem a ordem que está na coluna ``Ordem`` — não reordenam
        nada. Se reordenassem, a seta "para cima" mandava a linha para um sítio
        diferente daquele que se vê. Para pôr tudo junto pela ordem do
        navegador é o botão "Agrupar por chave" que serve.
        """
        grupos = agrupar_linhas_contiguas(linhas, self._metas_chaves)
        self.table.setRowCount(0)
        row_index = 0

        for grupo in grupos:
            fechado = grupo.codigo in self._grupos_fechados
            self.table.insertRow(row_index)
            self._escrever_cabecalho(
                row_index,
                texto=(
                    f"{'▸' if fechado else '▾'} {grupo.rotulo.upper()} — "
                    f"{grupo.total} linha(s)"
                ),
                tooltip="Clique para fechar ou abrir este grupo.",
                dados=("grupo", grupo.codigo),
                fundo=BEGE_AREIA,
                cor_texto=CASTANHO_ESCURO,
            )
            row_index += 1
            if fechado:
                continue

            for chave in grupo.chaves:
                chave_fechada = chave.codigo in self._chaves_fechadas
                self.table.insertRow(row_index)
                self._escrever_cabecalho(
                    row_index,
                    texto=(
                        f"{'▸' if chave_fechada else '▾'} {chave.nome} · "
                        f"{chave.codigo} · {chave.total} opção(ões)"
                    ),
                    tooltip="Clique para fechar ou abrir esta chave.",
                    dados=("chave", chave.codigo),
                    fundo=CINZA_CASTANHO,
                    cor_texto=CINZA_ESCURO,
                )
                row_index += 1
                if chave_fechada:
                    continue

                for estado in preparar_linhas_valueset(chave.linhas, ordenar=False):
                    self.table.insertRow(row_index)
                    self._escrever_linha(row_index, estado)
                    row_index += 1

    def _escrever_cabecalho(
        self,
        row_index: int,
        *,
        texto: str,
        tooltip: str,
        dados: tuple[str, str],
        fundo: str,
        cor_texto: str,
    ) -> None:
        """Escreve uma faixa que atravessa a tabela toda."""
        item = QTableWidgetItem(texto)
        # Faixa: não é uma linha de dados, por isso não entra na seleção nem
        # nas setas — só responde ao clique que a fecha e abre.
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setBackground(QBrush(QColor(fundo)))
        item.setForeground(QBrush(QColor(cor_texto)))
        item.setToolTip(tooltip)
        fonte = item.font()
        fonte.setBold(True)
        item.setFont(fonte)
        self.table.setItem(row_index, 0, item)
        self.table.setSpan(row_index, 0, 1, len(self.LINHA_HEADERS))
        self._cabecalhos_by_row[row_index] = dados

    def _escrever_linha(self, row_index: int, estado) -> None:
        """Escreve uma linha de dados do modelo."""
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

    def abrir_nova_linha(self) -> None:
        """Open the dialog to create a new model line."""
        self._abrir_dialog_criar_linha(success_message="Linha criada.")

    def _instalar_atalhos_clipboard(self) -> None:
        """Bind copy/paste only while the model table has focus."""
        for sequencia, handler in (
            (QKeySequence.StandardKey.Copy, self.copiar_dados),
            (QKeySequence.StandardKey.Paste, self.colar_dados),
        ):
            atalho = QShortcut(sequencia, self.table)
            atalho.setContext(Qt.ShortcutContext.WidgetShortcut)
            atalho.activated.connect(handler)

    def copiar_dados(self) -> None:
        """Copy reusable material content and detached operation snapshots."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para copiar.")
            return

        try:
            with SessionLocal() as session:
                type(self)._copied_snapshot = DefValuesetModeloLinhaService(
                    session
                ).copiar_snapshot_linha(linha.id)
                type(self)._copied_operacoes = DefValuesetModeloLinhaOperacaoService(
                    session
                ).listar_operacoes_da_linha(linha.id)
        except (SQLAlchemyError, ValueError) as error:
            type(self)._copied_snapshot = None
            type(self)._copied_operacoes = None
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível copiar os dados da linha.", error)
            )
            return

        self.status_label.setText(
            "Dados e operações da linha copiados. Selecione uma linha de destino."
        )

    def colar_dados(self) -> None:
        """Replace the selected line content, preserving its identity."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha de destino.")
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
                "as operações? As operações da linha de destino serão substituídas.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            colar_operacoes = confirm == QMessageBox.StandardButton.Yes

        try:
            with SessionLocal() as session:
                try:
                    DefValuesetModeloLinhaService(session).aplicar_snapshot_linha(
                        linha.id, snapshot, commit=False
                    )
                    if colar_operacoes:
                        DefValuesetModeloLinhaOperacaoService(
                            session
                        ).substituir_operacoes_de(
                            operacoes or [], linha.id, commit=False
                        )
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível colar os dados da linha.", error)
            )
            return

        self.carregar_linhas()
        aviso_prioridade = avisar_prioridade_repetida_apos_colagem(
            self,
            table=self.table,
            headers=self.LINHA_HEADERS,
            linhas_by_row=self._linhas_by_row,
            linha_id=linha.id,
        )
        if aviso_prioridade:
            self.status_label.setText(aviso_prioridade)
            return
        if colar_operacoes:
            self.status_label.setText(
                "Dados e operações colados; a identidade da linha de destino foi mantida."
            )
        else:
            self.status_label.setText(
                "Dados colados; a identidade e as operações da linha de destino foram mantidas."
            )

    def _abrir_menu_contexto(self, pos) -> None:
        """Show the model-line actions on right click."""
        item = self.table.itemAt(pos)
        if item is not None and item.row() in self._cabecalhos_by_row:
            return  # faixa de grupo/chave: não há linha sobre que agir
        if item is not None:
            selected_rows = {
                index.row() for index in self.table.selectionModel().selectedRows()
            }
            if item.row() not in selected_rows:
                self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.addAction("Editar Linha", self.abrir_editar_linha)
        menu.addAction("Copiar Dados (Ctrl+C)", self.copiar_dados)
        menu.addAction("Colar Dados (Ctrl+V)", self.colar_dados)
        menu.addAction("Propagar Operações…", self.propagar_operacoes)
        menu.addAction("Ativar/Desativar", self.alternar_linha_ativa)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def propagar_operacoes(self) -> None:
        """Preview and propagate source operations to explicit model-line targets."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione a linha de origem das operações.")
            return

        try:
            with SessionLocal() as session:
                contexto = DefValuesetOperacaoPropagacaoService(
                    session
                ).preparar_contexto(linha.id, app_session.current_user)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível localizar os destinos.", error)
            )
            return

        if not contexto.destinos:
            self.status_label.setText(
                "Não existem outras linhas com a mesma chave ValueSet e a mesma Ref LE."
            )
            return

        dialog = PropagarOperacoesValuesetModeloDialog(contexto, parent=self)
        if not dialog.exec():
            self.status_label.setText("Propagação cancelada; nenhuma linha foi alterada.")
            return

        try:
            with SessionLocal() as session:
                resultado = DefValuesetOperacaoPropagacaoService(session).executar(
                    contexto, dialog.selected_ids, app_session.current_user
                )
        except (ValueError, PermissionError) as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível propagar as operações.", error)
            )
            return

        self.carregar_linhas()
        self.status_label.setText(
            f"Operações propagadas para {resultado.destinos_atualizados} linha(s): "
            f"{resultado.substituidas} substituída(s), "
            f"{resultado.adicionadas} adicionada(s) e "
            f"{resultado.desativadas} desativada(s)."
        )

    def copiar_chaves_para_modelos(self) -> None:
        """Levar chaves inteiras deste modelo para outros modelos."""
        try:
            with SessionLocal() as session:
                chaves = DefValuesetChaveCopiaService(session).listar_chaves_do_modelo(
                    self.modelo.id
                )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível ler as chaves do modelo.", error)
            )
            return

        if not chaves:
            self.status_label.setText("Este modelo não tem chaves para copiar.")
            return

        def recalcular(chaves_escolhidas, modo):
            """A conta refaz-se a cada mudança, sempre com dados frescos."""
            with SessionLocal() as session:
                return DefValuesetChaveCopiaService(session).preparar_contexto(
                    self.modelo.id,
                    chaves_escolhidas,
                    app_session.current_user,
                    modo=modo,
                )

        # Se houver uma chave a filtrar a tabela, é essa que o utilizador tem
        # à frente — vai já marcada.
        iniciais = [self._chave_selecionada] if self._chave_selecionada else []
        dialog = CopiarChavesValuesetDialog(
            self.modelo.codigo,
            chaves,
            recalcular,
            chaves_iniciais=iniciais,
            parent=self,
        )
        if not dialog.exec():
            self.status_label.setText("Cópia cancelada; nenhum modelo foi alterado.")
            return

        contexto = dialog.contexto
        destinos = dialog.destinos_escolhidos
        if contexto is None or not destinos:
            self.status_label.setText("Nenhum modelo foi escolhido.")
            return

        try:
            with SessionLocal() as session:
                resultado = DefValuesetChaveCopiaService(session).executar(
                    contexto, destinos, app_session.current_user
                )
        except (ValueError, PermissionError) as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível copiar as chaves.", error)
            )
            return

        self.status_label.setText(
            f"{resultado.linhas_criadas} linha(s) criadas e "
            f"{resultado.linhas_atualizadas} atualizadas em "
            f"{resultado.modelos_afetados} modelo(s), com "
            f"{resultado.operacoes_copiadas} operação(ões)."
        )

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

    def _criar_linha_from_form_data(self, form_data, *, copiar_operacoes_de=None):
        """Create one model line from dialog data.

        ``copiar_operacoes_de`` is the line the new one is being copied from
        ("Gravar como…"): the operations of the variant travel with it, senão a
        opção nova custeava diferente da original sem se dar por isso.
        """
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

            if copiar_operacoes_de is not None:
                DefValuesetModeloLinhaOperacaoService(
                    session
                ).copiar_operacoes_entre_linhas(copiar_operacoes_de, result.id)

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
                self._criar_linha_from_form_data(
                    form_data, copiar_operacoes_de=linha.id
                )
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
            self.status_label.setText(
                "Linha gravada como nova opção, com as operações da original."
            )
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

    def _handle_click_celula(self, row: int, _column: int) -> None:
        """Um clique numa faixa fecha ou abre o bloco dela."""
        self._alternar_cabecalho(row)

    def _alternar_cabecalho(self, row: int) -> bool:
        """Fecha/abre o bloco da faixa nesta linha. Diz se era mesmo uma faixa."""
        dados = self._cabecalhos_by_row.get(row)
        if dados is None:
            return False

        tipo, codigo = dados
        fechados = self._grupos_fechados if tipo == "grupo" else self._chaves_fechadas
        if codigo in fechados:
            fechados.discard(codigo)
        else:
            fechados.add(codigo)
        self._aplicar_filtro_linhas()
        return True

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        # Duplo clique numa faixa é só o segundo clique a fechar e a reabrir o
        # bloco — não há linha nenhuma para editar.
        if row in self._cabecalhos_by_row:
            return
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
