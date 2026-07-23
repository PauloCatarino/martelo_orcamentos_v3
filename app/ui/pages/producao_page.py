"""Production process list and detail page."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import QDate, QObject, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QPixmap
try:
    from PySide6.QtGui import QFileSystemModel
except ImportError:  # PySide6 6.10 exposes QFileSystemModel from QtWidgets.
    from PySide6.QtWidgets import QFileSystemModel
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableView,
    QTextEdit,
    QStackedWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.datas import normalizar_data
from app.domain import pesquisa_texto
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.models.producao import Producao
from app.services.cutrite_service import (
    execute_cutrite_import,
    execute_cutrite_resumo_pdf,
    prepare_cutrite_import,
    prepare_cutrite_resumo_pdf,
)
from app.services.lista_material_imos_service import (
    execute_lista_material_imos,
    prepare_lista_material_imos,
)
from app.services.producao_service import (
    ProducaoService,
    codigo_processo_com_cliente,
    converter_orcamento,
    criar_nova_versao,
    criar_processo_externo,
    eliminar_processo_completo,
    gerar_nome_enc_imos_ix,
    gerar_nome_plano_cut_rite,
    listar_processos_por_encomenda,
    preparar_nova_versao,
)
from app.services.sinonimos_service import carregar_sinonimos
from app.services.producao_v2_sync_service import (
    ProducaoV2ConfigError,
    aplicar_selecao,
    comparar_v2_com_v3,
)
from app.services.producao_pastas_service import (
    arvore_pastas_processo,
    caminho_versao_de_processo,
    preview_conteudo_pasta,
)
from app.ui import tema
from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog
from app.ui.dialogs.cutrite_progress_dialog import CutRiteProgressDialog
from app.ui.dialogs.nova_versao_processo_dialog import NovaVersaoProcessoDialog
from app.ui.dialogs.novo_processo_dialog import NovoProcessoDialog
from app.ui.dialogs.pastas_processo_dialog import PastasProcessoDialog
from app.ui.dialogs.producao_v2_sync_dialog import ProducaoV2SyncDialog
from app.ui.icones import icone, icone_ficheiro
from app.ui.helpers.detalhe_obra_worker import (
    DetalheObraResolvido,
    DetalheObraWorker,
)
from app.ui.helpers.colunas_producao import (
    COLUNAS_PRODUCAO,
    LARGURAS_DEFAULT_PRODUCAO,
    carregar_config,
    desserializar_config,
    guardar_config,
)
from app.ui.helpers.modelo_producao import ProducaoFilterProxy, ProducaoTableModel
from app.ui.helpers.vistas_producao import (
    VistaProducao,
    carregar_vistas,
    guardar_vistas,
    remover_vista,
    substituir_vista,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter


TIPOS_PASTA_PRODUCAO = (
    "Encomenda de Cliente",
    "Encomenda de Cliente Final",
)

#: Nome da entrada que representa "sem vista" no combo de vistas.
VISTA_SEM_FILTROS = "Todas as obras"

#: Data sentinela dos campos ``QDateEdit`` — apresentada como vazia.
DATA_VAZIA = QDate(1752, 9, 14)

#: Coluna usada para "ordem de entrada" (mais recentes em cima).
COLUNA_ORDEM_ENTRADA = next(
    indice
    for indice, coluna in enumerate(COLUNAS_PRODUCAO)
    if coluna.key == "criada_em"
)


class _ImagemPreviewLabel(QLabel):
    """Clickable preview label that delegates double-clicks to the page."""

    def __init__(self, on_double_click, parent=None) -> None:
        super().__init__(parent)
        self._on_double_click = on_double_click

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._on_double_click()
        super().mouseDoubleClickEvent(event)


class _CutRiteWorker(QObject):
    """Corre a automação CUT-RITE fora da thread da UI."""

    progresso = Signal(str)
    falhou = Signal(str)
    concluido = Signal(str)

    def __init__(self, *, processo_id, pasta_servidor, nome_plano, nome_enc_imos):
        super().__init__()
        self._processo_id = processo_id
        self._pasta_servidor = pasta_servidor
        self._nome_plano = nome_plano
        self._nome_enc_imos = nome_enc_imos

    def run(self) -> None:
        import pythoncom  # pywin32: COM STA nesta thread (necessário para UIA/win32)

        pythoncom.CoInitialize()
        try:
            with SessionLocal() as session:
                context = prepare_cutrite_import(
                    session,
                    current_id=self._processo_id,
                    pasta_servidor=self._pasta_servidor,
                    nome_plano_cut_rite=self._nome_plano,
                    nome_enc_imos=self._nome_enc_imos,
                )
            resultado = execute_cutrite_import(
                context,
                progress_callback=self.progresso.emit,
            )
            destino = ""
            try:
                destino = str(resultado.cutrite_target_data_dir)
            except Exception:
                destino = ""
            self.concluido.emit(destino)
        except Exception as exc:
            self.falhou.emit(str(exc))
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


class _CutRitePdfWorker(QObject):
    """Exporta o resumo do plano CUT-RITE para PDF, fora da thread da UI."""

    progresso = Signal(str)
    falhou = Signal(str)
    concluido = Signal(str)

    def __init__(self, *, processo_id, pasta_servidor, nome_plano):
        super().__init__()
        self._processo_id = processo_id
        self._pasta_servidor = pasta_servidor
        self._nome_plano = nome_plano

    def run(self) -> None:
        import pythoncom  # COM STA nesta thread (UIA/win32)

        pythoncom.CoInitialize()
        try:
            with SessionLocal() as session:
                context = prepare_cutrite_resumo_pdf(
                    session,
                    current_id=self._processo_id,
                    pasta_servidor=self._pasta_servidor,
                    nome_plano_cut_rite=self._nome_plano,
                )
            output = execute_cutrite_resumo_pdf(
                context, progress_callback=self.progresso.emit
            )
            self.concluido.emit(str(output))
        except Exception as exc:
            self.falhou.emit(str(exc))
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


class ProducaoPage(QWidget):
    """Production process page with an editable V3 detail form."""

    TABLE_HEADERS = [coluna.titulo for coluna in COLUNAS_PRODUCAO]
    COLUMN_WIDTHS = LARGURAS_DEFAULT_PRODUCAO

    #: Pede ao worker (noutra thread) os dados da obra que vivem no servidor.
    detalhe_pedido = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[Producao] = []
        self._selected_processo_id: int | None = None
        self._dirty = False
        self._a_preencher_form = False
        self._cliente_id: int | None = None
        self._imagem_path: str | None = None
        self._imagem_preview_pixmap_original: QPixmap | None = None
        self._colunas_visiveis = [
            coluna.key for coluna in COLUNAS_PRODUCAO if coluna.visivel_default
        ]
        self._larguras_colunas = dict(LARGURAS_DEFAULT_PRODUCAO)
        self._guardar_larguras_agendado = False
        self._cutrite_thread = None
        self._cutrite_worker = None
        self._cutrite_dialog = None
        self._aplicando_config_colunas = False
        self._vistas: list[VistaProducao] = []
        self._cache_detalhe: dict[int, DetalheObraResolvido] = {}
        self._pedido_detalhe = 0
        self._iniciar_thread_detalhe()

        self.cabecalho = BarraCabecalho(
            "Produção",
            ["Obras em produção do Martelo V3"],
        )

        self.convert_button = QPushButton("Converter Orçamento")
        self.convert_button.setToolTip("Converter um orçamento adjudicado numa obra de produção")
        self.convert_button.clicked.connect(self._converter_orcamento)

        self.novo_processo_button = QPushButton("Novo Processo")
        self.novo_processo_button.setToolTip(
            "Criar uma obra a partir de uma encomenda do PHC ou do Cliente Final (Streamlit)"
        )
        self.novo_processo_button.clicked.connect(self._novo_processo)

        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setToolTip("Abrir a pasta desta obra no explorador")
        self.open_folder_button.clicked.connect(self._abrir_pasta_versao_selecionada)

        self.nova_versao_button = QPushButton("Nova Versão")
        self.nova_versao_button.setToolTip(
            "Criar nova versão de obra/CUT-RITE do processo selecionado"
        )
        self.nova_versao_button.clicked.connect(self._nova_versao)

        self.lista_material_button = QPushButton("Lista Material_IMOS")
        self.lista_material_button.setIcon(icone_ficheiro("icon_excel.ico"))
        self.lista_material_button.setToolTip(
            "Gerar o Excel 'Lista Material_IMOS' na pasta do processo"
        )
        self.lista_material_button.clicked.connect(self._lista_material_imos)

        self.enviar_cutrite_button = QPushButton("Enviar CUT-RITE")
        self.enviar_cutrite_button.setIcon(icone_ficheiro("icon_cut_rite.ico"))
        self.enviar_cutrite_button.setToolTip(
            "Criar o plano de corte no CUT-RITE a partir da Lista Material"
        )
        self.enviar_cutrite_button.clicked.connect(self._enviar_cutrite)

        self.exportar_resumo_pdf_button = QPushButton("Exportar Resumo (PDF)")
        self.exportar_resumo_pdf_button.setIcon(icone_ficheiro("icon_pdf_cut_rite.ico"))
        self.exportar_resumo_pdf_button.setToolTip(
            "Exportar para PDF o resumo do plano de corte (CUT-RITE) para a pasta da obra"
        )
        self.exportar_resumo_pdf_button.clicked.connect(self._exportar_resumo_pdf)

        self.delete_button = QPushButton("Eliminar")
        self.delete_button.setToolTip("Eliminar obra: registo e/ou pasta no servidor")
        self.delete_button.clicked.connect(self._eliminar_processo)

        self.save_button = QPushButton("Salvar")
        self.save_button.setToolTip("Gravar as alterações da obra selecionada")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setToolTip("Recarregar a lista de obras")
        self.refresh_button.clicked.connect(self.carregar_processos)

        self.atualizar_v2_button = QPushButton("⟳ Atualizar dados V2")
        self.atualizar_v2_button.setToolTip(
            "TEMPORÁRIO (fase de transição): comparar as obras do Martelo V2 com as "
            "do V3 e escolher o que trazer. O V2 nunca é alterado."
        )
        self.atualizar_v2_button.setStyleSheet(
            "QPushButton { border: 2px solid #1D6FA5; color: #1D6FA5; "
            "font-weight: bold; }"
        )
        self.atualizar_v2_button.clicked.connect(self._atualizar_dados_v2)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.convert_button)
        actions_layout.addWidget(self.novo_processo_button)
        actions_layout.addWidget(self.open_folder_button)
        actions_layout.addWidget(self.nova_versao_button)
        actions_layout.addWidget(self.lista_material_button)
        actions_layout.addWidget(self.enviar_cutrite_button)
        actions_layout.addWidget(self.exportar_resumo_pdf_button)
        actions_layout.addWidget(self.delete_button)
        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.atualizar_v2_button)
        actions_layout.addStretch()

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.estado_combo = QComboBox()
        self.cliente_combo = QComboBox()
        self.responsavel_combo = QComboBox()
        self.cliente_combo.setToolTip(
            "Só mostra os clientes com obras do responsável escolhido"
        )
        for combo in (self.estado_combo, self.cliente_combo):
            combo.currentTextChanged.connect(self._render)
        self.responsavel_combo.currentTextChanged.connect(self._on_responsavel_mudou)

        self.vista_combo = QComboBox()
        self.vista_combo.setMinimumWidth(150)
        self.vista_combo.setToolTip(
            "Vistas guardadas: combinações de pesquisa e filtros, suas e só suas"
        )
        self.vista_combo.currentIndexChanged.connect(self._aplicar_vista_escolhida)

        self.vista_button = QPushButton("★")
        self.vista_button.setToolTip("Guardar ou eliminar vistas")
        self.vista_button.setFixedWidth(30)
        self.vista_button.clicked.connect(self._abrir_menu_vistas)

        self.atrasadas_check = QCheckBox("só atrasadas")
        self.atrasadas_check.setToolTip(
            "Mostrar apenas obras com a data de entrega já passada "
            "(obras arquivadas ou finalizadas não contam)"
        )
        self.atrasadas_check.toggled.connect(self._render)

        self.obras_ano_label = QLabel("")
        self.obras_ano_label.setObjectName("producaoObrasAno")
        self.obras_ano_label.setStyleSheet(
            f"QLabel#producaoObrasAno {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; border: 1px solid {tema.CASTANHO_MEDIO}; "
            "border-radius: 4px; padding: 4px 12px; font-weight: bold; }"
        )
        self.obras_ano_label.setToolTip(
            "Obras do ano atual. Com Responsável = Todos conta todas as obras do ano; "
            "com um responsável escolhido conta só as obras desse responsável no ano. "
            "O total de todos os anos está no rodapé da tabela."
        )

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        filters_layout.addWidget(QLabel("Vista"))
        filters_layout.addWidget(self.vista_combo)
        filters_layout.addWidget(self.vista_button)
        filters_layout.addWidget(self.campo_pesquisa)
        filters_layout.addWidget(QLabel("Estado"))
        filters_layout.addWidget(self.estado_combo)
        filters_layout.addWidget(QLabel("Cliente"))
        filters_layout.addWidget(self.cliente_combo)
        filters_layout.addWidget(QLabel("Responsável"))
        filters_layout.addWidget(self.responsavel_combo)
        filters_layout.addWidget(self.atrasadas_check)
        filters_layout.addStretch()
        filters_layout.addWidget(self.obras_ano_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("producaoStatus")

        self.detail_panel = self._criar_painel_detalhe()

        self.modelo = ProducaoTableModel(self)
        self.proxy = ProducaoFilterProxy(self)
        self.proxy.setSourceModel(self.modelo)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(
            COLUNA_ORDEM_ENTRADA,
            Qt.SortOrder.DescendingOrder,
        )
        header = self.table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._abrir_menu_colunas)
        header.setToolTip(
            "Clique com o botão direito para escolher as colunas visíveis. "
            "As larguras e as colunas escolhidas ficam guardadas por utilizador."
        )
        self._aplicar_larguras_colunas()
        header.sectionResized.connect(self._on_coluna_redimensionada)
        self._carregar_config_colunas()
        self.table.selectionModel().selectionChanged.connect(self._on_select_row)
        self.table.doubleClicked.connect(self._handle_table_double_click)

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("producaoFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        # Sem isto o mínimo natural da tabela rouba altura ao detalhe da obra.
        self.table.setMinimumHeight(120)

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(6)
        table_layout.addWidget(self.table, stretch=1)
        table_layout.addWidget(self.footer_label)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.detail_panel)
        self.splitter.addWidget(table_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        # Chave nova: o layout mudou, as alturas guardadas do layout antigo
        # deixariam a tabela demasiado alta.
        if not ligar_persistencia_splitter(self.splitter, "producao_detalhe_amplo"):
            self.splitter.setSizes([660, 210])

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.splitter, stretch=1)

        self.setLayout(layout)
        self._carregar_vistas()
        self._carregar_sinonimos()
        self.carregar_processos()

    def _criar_painel_detalhe(self) -> QScrollArea:
        grupo = QGroupBox("Detalhe da obra")
        grupo.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )

        self.processo_input = self._readonly_line()
        self.nome_plano_corte_input = self._readonly_line()
        self.nome_plano_corte_input.setToolTip(
            "Nome do plano CUT-RITE derivado do processo"
        )
        self.nome_enc_imos_ix_input = self._readonly_line()
        self.nome_enc_imos_ix_input.setToolTip(
            "Nome da encomenda IMOS iX derivado do processo"
        )
        self.ano_input = QLineEdit()
        self.num_enc_phc_input = QLineEdit()
        self.versao_obra_input = QLineEdit()
        self.versao_obra_input.setMaxLength(2)
        self.versao_plano_input = QLineEdit()
        self.versao_plano_input.setMaxLength(2)
        self.cliente_input = self._readonly_line()
        self.cliente_simplex_input = self._readonly_line()
        self.num_cliente_phc_input = self._readonly_line()
        self.num_orcamento_input = QLineEdit()
        self.versao_orc_input = QLineEdit()
        self.preco_total_input = QLineEdit()
        self.qt_artigos_input = QLineEdit()

        self.estado_form_combo = QComboBox()
        self.estado_form_combo.addItems(ESTADOS_PRODUCAO)

        self.responsavel_form_combo = QComboBox()
        self.responsavel_form_combo.setEditable(True)

        self.ref_cliente_input = QLineEdit()
        self.obra_input = QLineEdit()
        self.localizacao_input = QLineEdit()
        self.data_inicio_input = self._campo_data()
        self.data_entrega_input = self._campo_data()

        self.tipo_pasta_combo = QComboBox()
        self.tipo_pasta_combo.addItems(TIPOS_PASTA_PRODUCAO)

        dados_grid = QGridLayout()
        dados_grid.setContentsMargins(0, 0, 0, 0)
        dados_grid.setHorizontalSpacing(6)
        dados_grid.setVerticalSpacing(2)
        campos = [
            ("Processo", self.processo_input),
            (
                "Nome Plano CUT-RITE",
                self.nome_plano_corte_input,
                "icon_cut_rite.ico",
            ),
            (
                "Nome Enc IMOS IX",
                self.nome_enc_imos_ix_input,
                "icon_imos_2025.ico",
            ),
            ("Ano", self.ano_input),
            ("Nº Enc PHC", self.num_enc_phc_input),
            ("V. Obra", self.versao_obra_input),
            ("V. CutRite", self.versao_plano_input),
            ("Cliente", self.cliente_input),
            ("Cliente simplex", self.cliente_simplex_input),
            ("Nº Cliente PHC", self.num_cliente_phc_input),
            ("Nº Orçamento", self.num_orcamento_input),
            ("V. Orç", self.versao_orc_input),
            ("Preço total", self.preco_total_input),
            ("Qt artigos", self.qt_artigos_input),
            ("Estado", self.estado_form_combo),
            ("Responsável", self.responsavel_form_combo),
            ("Ref Cliente", self.ref_cliente_input),
            ("Obra", self.obra_input),
            ("Localização", self.localizacao_input),
            ("Data Início", self.data_inicio_input),
            ("Data Entrega", self.data_entrega_input),
            ("Tipo Pasta", self.tipo_pasta_combo),
        ]
        for index, campo in enumerate(campos):
            label, widget, *icone = campo
            label_widget = (
                self._label_com_icone(label, icone[0])
                if icone
                else label
            )
            self._add_grid_field(
                dados_grid,
                index // 2,
                index % 2,
                label_widget,
                widget,
            )

        # Etiquetas encostadas, campos a esticar com a largura disponível.
        for coluna_label in (0, 2):
            dados_grid.setColumnStretch(coluna_label, 0)
        for coluna_campo in (1, 3):
            dados_grid.setColumnStretch(coluna_campo, 1)
        self._compactar_campos_detalhe(campos)

        dados_widget = QWidget()
        dados_widget.setLayout(dados_grid)
        dados_widget.setMinimumWidth(520)

        painel_imagem = self._criar_painel_imagem()

        # Divisor arrastável: cada utilizador ajusta campos vs imagem e a
        # posição fica guardada.
        self.splitter_detalhe = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_detalhe.setChildrenCollapsible(False)
        self.splitter_detalhe.setHandleWidth(10)
        self.splitter_detalhe.addWidget(dados_widget)
        self.splitter_detalhe.addWidget(painel_imagem)
        self.splitter_detalhe.setStretchFactor(0, 1)
        self.splitter_detalhe.setStretchFactor(1, 1)
        self.splitter_detalhe.setToolTip(
            "Arraste para dar mais espaço aos campos ou à imagem — fica guardado"
        )
        if not ligar_persistencia_splitter(
            self.splitter_detalhe, "producao_detalhe_topo"
        ):
            self.splitter_detalhe.setSizes([900, 900])

        self.descricao_artigos_text = self._text_edit()
        self.materias_usados_text = self._text_edit()
        self.descricao_producao_text = self._text_edit()
        self.notas1_text = self._text_edit()
        self.notas2_text = self._text_edit()
        self.notas3_text = self._text_edit()

        textos_grid = QGridLayout()
        textos_grid.setContentsMargins(0, 0, 0, 0)
        textos_grid.setHorizontalSpacing(10)
        textos_grid.setVerticalSpacing(4)
        textos = [
            ("Descrição artigos", self.descricao_artigos_text),
            ("Matérias usados", self.materias_usados_text),
            ("Descrição produção", self.descricao_producao_text),
            ("Notas 1", self.notas1_text),
            ("Notas 2", self.notas2_text),
            ("Notas 3", self.notas3_text),
        ]
        # 2 linhas x 3 colunas: cada bloco ocupa uma linha de label e outra de campo.
        for index, (label, widget) in enumerate(textos):
            row = (index // 3) * 2
            col = index % 3
            textos_grid.addWidget(QLabel(label), row, col)
            textos_grid.addWidget(widget, row + 1, col)
        for col in range(3):
            textos_grid.setColumnStretch(col, 1)

        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self.splitter_detalhe)
        layout.addLayout(textos_grid)

        self._readonly_widgets = [
            self.processo_input,
            self.nome_plano_corte_input,
            self.nome_enc_imos_ix_input,
            self.cliente_input,
            self.cliente_simplex_input,
            self.num_cliente_phc_input,
        ]
        self._editable_widgets = [
            self.ano_input,
            self.num_enc_phc_input,
            self.versao_obra_input,
            self.versao_plano_input,
            self.num_orcamento_input,
            self.versao_orc_input,
            self.preco_total_input,
            self.qt_artigos_input,
            self.estado_form_combo,
            self.responsavel_form_combo,
            self.ref_cliente_input,
            self.obra_input,
            self.localizacao_input,
            self.data_inicio_input,
            self.data_entrega_input,
            self.tipo_pasta_combo,
            self.descricao_artigos_text,
            self.materias_usados_text,
            self.descricao_producao_text,
            self.notas1_text,
            self.notas2_text,
            self.notas3_text,
        ]
        self._aplicar_tooltips_editaveis()
        self._ligar_sinais_edicao()
        self._preparar_link_pasta_orcamento()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grupo)
        scroll.setMinimumHeight(240)
        return scroll

    def _compactar_campos_detalhe(self, campos: list) -> None:
        """Keep the detail fields short so the whole form stays visible.

        Only the height is fixed: a largura acompanha o divisor arrastável.
        """
        for campo in campos:
            campo[1].setFixedHeight(22)

    @staticmethod
    def _definir_data(campo: QDateEdit, valor: object) -> None:
        """Show one stored date; anything invalid leaves the field empty."""
        texto = normalizar_data(valor)
        data = QDate.fromString(texto, "dd-MM-yyyy") if texto else QDate()
        campo.setDate(data if data.isValid() else DATA_VAZIA)

    @staticmethod
    def _texto_data(campo: QDateEdit) -> str | None:
        """Return the field's date as ``dd-mm-aaaa``, or None when empty."""
        data = campo.date()
        if not data.isValid() or data == DATA_VAZIA:
            return None
        return data.toString("dd-MM-yyyy")

    def _formatar_preco_total(self) -> None:
        """Normalise the price as the user leaves the field."""
        texto = self.preco_total_input.text().strip()
        if not texto:
            self.preco_total_input.setStyleSheet("")
            return

        try:
            valor = self._decimal_or_none(texto)
        except ValueError:
            self.preco_total_input.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
            self.status_label.setText(
                "Preço total inválido — use números, por exemplo 17300,00."
            )
            return

        self.preco_total_input.setStyleSheet("")
        if valor is not None:
            self.preco_total_input.setText(f"{valor:.2f}")

    def _campo_data(self) -> QDateEdit:
        """Date field with calendar popup; empty is the minimum date."""
        campo = QDateEdit()
        campo.setDisplayFormat("dd-MM-yyyy")
        campo.setCalendarPopup(True)
        campo.setMinimumDate(DATA_VAZIA)
        campo.setSpecialValueText(" ")  # data mínima é apresentada como vazio
        campo.setDate(DATA_VAZIA)
        campo.setToolTip(
            "Escolha no calendário ou escreva dd-mm-aaaa. "
            "Para limpar, recue até a data ficar vazia."
        )
        return campo

    def _readonly_line(self) -> QLineEdit:
        line = QLineEdit()
        line.setReadOnly(True)
        line.setStyleSheet(
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO};"
        )
        return line

    def _text_edit(self) -> QTextEdit:
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False)
        text_edit.setMinimumHeight(66)
        return text_edit

    def _criar_painel_imagem(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.imagem_preview = _ImagemPreviewLabel(self._abrir_imagem_pdf)
        self.imagem_preview.setText("Sem imagem")
        self.imagem_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imagem_preview.setMinimumSize(460, 300)
        self.imagem_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.imagem_preview.setStyleSheet(
            f"QLabel {{ border: 1px solid {tema.CINZA_CASTANHO}; "
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO}; }}"
        )
        self.imagem_preview.setToolTip("Imagem do IMOS (automatica)")

        self.fs_model = QFileSystemModel()
        self.arvore_pasta = QTreeView()
        self.arvore_pasta.setModel(self.fs_model)
        self.arvore_pasta.setMinimumSize(460, 300)
        self.arvore_pasta.setHeaderHidden(True)
        self.arvore_pasta.setStyleSheet(
            f"QTreeView {{ background-color: {tema.BEGE_CLARO};"
            f" color: {tema.CASTANHO_ESCURO}; border: 1px solid {tema.CINZA_CASTANHO}; }}"
            f"QTreeView::item {{ color: {tema.CASTANHO_ESCURO}; padding: 2px; }}"
            f"QTreeView::item:hover {{ background: {tema.BEGE_AREIA};"
            f" color: {tema.CASTANHO_ESCURO}; }}"
            f"QTreeView::item:selected {{ background: {tema.CASTANHO_ESCURO};"
            f" color: #FFFFFF; }}"
        )
        self.arvore_pasta.setToolTip(
            "Conteudo da pasta da obra - duplo-clique abre o ficheiro/pasta"
        )
        self.arvore_pasta.doubleClicked.connect(self._abrir_item_arvore)
        for coluna in (1, 2, 3):
            self.arvore_pasta.setColumnHidden(coluna, True)

        self.imagem_stack = QStackedWidget()
        self.imagem_stack.addWidget(self.imagem_preview)
        self.imagem_stack.addWidget(self.arvore_pasta)

        layout.addWidget(self.imagem_stack, stretch=1)
        layout.addWidget(self._criar_campo_pasta_obra())
        return panel

    def _criar_campo_pasta_obra(self) -> QWidget:
        """Read-only, selectable folder path with copy/open shortcuts."""
        painel = QWidget()
        layout = QVBoxLayout(painel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        titulo = QLabel("Pasta da obra")
        titulo.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;")

        self.pasta_obra_input = QLineEdit()
        self.pasta_obra_input.setReadOnly(True)
        self.pasta_obra_input.setCursorPosition(0)
        self.pasta_obra_input.setStyleSheet(
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO};"
        )
        self.pasta_obra_input.setToolTip(
            "Caminho da pasta desta versão da obra — pode selecionar e copiar (Ctrl+C)"
        )

        self.abrir_pasta_campo_button = QPushButton("Abrir")
        self.abrir_pasta_campo_button.setIcon(icone("pasta_abrir"))
        self.abrir_pasta_campo_button.setToolTip(
            "Abrir esta pasta no explorador (o caminho pode ser copiado do campo)"
        )
        self.abrir_pasta_campo_button.clicked.connect(self._abrir_pasta_versao_selecionada)

        linha = QHBoxLayout()
        linha.setContentsMargins(0, 0, 0, 0)
        linha.setSpacing(4)
        linha.addWidget(self.pasta_obra_input, stretch=1)
        linha.addWidget(self.abrir_pasta_campo_button)

        layout.addWidget(titulo)
        layout.addLayout(linha)
        return painel

    def _preparar_link_pasta_orcamento(self) -> None:
        """Add an inline 'open budget folder' action to Nº Orçamento / V. Orç.

        A ação só fica visível quando os dois campos estão preenchidos e a
        pasta do orçamento existe mesmo no servidor.
        """
        self._pasta_orcamento: Path | None = None
        icone_pasta = icone("pasta_abrir")

        self._acoes_pasta_orcamento = []
        for campo in (self.num_orcamento_input, self.versao_orc_input):
            acao = QAction(icone_pasta, "Abrir pasta do orçamento", campo)
            acao.setVisible(False)
            acao.triggered.connect(self._abrir_pasta_orcamento)
            campo.addAction(acao, QLineEdit.ActionPosition.TrailingPosition)
            self._acoes_pasta_orcamento.append(acao)
            campo.editingFinished.connect(self._reavaliar_pasta_orcamento)

    def _definir_link_pasta_orcamento(self, pasta) -> None:
        """Show or hide the inline shortcut to the budget folder."""
        if not hasattr(self, "_acoes_pasta_orcamento"):
            return

        self._pasta_orcamento = pasta
        dica = (
            f"Abrir a pasta do orçamento:\n{pasta}"
            if pasta is not None
            else "Preencha Nº Orçamento e V. Orç para abrir a pasta do orçamento"
        )
        for acao in self._acoes_pasta_orcamento:
            acao.setVisible(pasta is not None)
            acao.setToolTip(dica)

    def _abrir_pasta_orcamento(self) -> None:
        pasta = getattr(self, "_pasta_orcamento", None)
        if pasta is None:
            self.status_label.setText("Pasta do orçamento não encontrada.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))
        self.status_label.setText(f"Aberta a pasta do orçamento: {pasta}")

    def _reavaliar_pasta_orcamento(self) -> None:
        """Re-read the server after the user edits Nº Orçamento / V. Orç."""
        if self._a_preencher_form or self._selected_processo_id is None:
            return
        self._invalidar_cache_detalhe(self._selected_processo_id)
        self._pedir_detalhe_obra(self._processo_visivel_por_id(self._selected_processo_id))

    def _label_com_icone(self, texto: str, nome_icone: str) -> QWidget:
        label_widget = QWidget()
        layout = QHBoxLayout(label_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        icon_label = QLabel()
        icon_label.setPixmap(icone_ficheiro(nome_icone).pixmap(16, 16))
        text_label = QLabel(texto)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch()
        return label_widget

    def _add_grid_field(
        self,
        grid: QGridLayout,
        row: int,
        pair_col: int,
        label: str | QWidget,
        widget: QWidget,
    ) -> None:
        col = pair_col * 2
        label_widget = label if isinstance(label, QWidget) else QLabel(label)
        grid.addWidget(label_widget, row, col)
        grid.addWidget(widget, row, col + 1)

    def _ligar_sinais_edicao(self) -> None:
        for line_edit in (
            self.ano_input,
            self.num_enc_phc_input,
            self.versao_obra_input,
            self.versao_plano_input,
            self.ref_cliente_input,
        ):
            line_edit.textChanged.connect(self._on_campo_derivado_editado)
        for line_edit in (
            self.num_cliente_phc_input,
            self.num_orcamento_input,
            self.versao_orc_input,
            self.preco_total_input,
            self.qt_artigos_input,
            self.ref_cliente_input,
            self.obra_input,
            self.localizacao_input,
        ):
            if line_edit is self.ref_cliente_input:
                continue
            line_edit.textChanged.connect(self._on_user_edit)
        for campo_data in (self.data_inicio_input, self.data_entrega_input):
            campo_data.dateChanged.connect(self._on_user_edit)
        self.preco_total_input.editingFinished.connect(self._formatar_preco_total)
        for combo in (
            self.estado_form_combo,
            self.responsavel_form_combo,
            self.tipo_pasta_combo,
        ):
            combo.currentTextChanged.connect(self._on_user_edit)
        for text_edit in (
            self.descricao_artigos_text,
            self.materias_usados_text,
            self.descricao_producao_text,
            self.notas1_text,
            self.notas2_text,
            self.notas3_text,
        ):
            text_edit.textChanged.connect(self._on_user_edit)

    def _aplicar_tooltips_editaveis(self) -> None:
        self.ano_input.setToolTip("Ano do processo")
        self.num_enc_phc_input.setToolTip("Número da encomenda PHC")
        self.versao_obra_input.setToolTip("Versão da obra")
        self.versao_plano_input.setToolTip("Versão CUT-RITE")
        self.cliente_input.setToolTip("Cliente original do processo (fixo)")
        self.cliente_simplex_input.setToolTip(
            "Nome simplex original usado nos nomes derivados (fixo)"
        )
        self.num_cliente_phc_input.setToolTip("Número do cliente original no PHC")
        self.num_orcamento_input.setToolTip("Número do orçamento de origem")
        self.versao_orc_input.setToolTip("Versão do orçamento de origem")
        self.preco_total_input.setToolTip("Preço total da obra")
        self.qt_artigos_input.setToolTip("Quantidade de artigos")
        self.estado_form_combo.setToolTip("Estado da obra em produção")
        self.responsavel_form_combo.setToolTip("Responsável pela obra")
        self.ref_cliente_input.setToolTip("Referência do cliente")
        self.obra_input.setToolTip("Nome ou descrição curta da obra")
        self.localizacao_input.setToolTip("Localização da obra")
        self.data_inicio_input.setToolTip(
            "Data de início no formato dd-mm-aaaa; use o calendário para escolher"
        )
        self.data_entrega_input.setToolTip(
            "Data de entrega no formato dd-mm-aaaa; use o calendário para escolher"
        )
        self.tipo_pasta_combo.setToolTip("Pasta de destino no servidor")
        self.descricao_artigos_text.setToolTip("Descrição dos artigos da obra")
        self.materias_usados_text.setToolTip("Matérias usadas na obra")
        self.descricao_producao_text.setToolTip("Descrição da produção")
        self.notas1_text.setToolTip("Notas adicionais da obra")
        self.notas2_text.setToolTip("Notas adicionais da obra")
        self.notas3_text.setToolTip("Notas adicionais da obra")

    def carregar_processos(self, selecionar_id: int | None = None) -> None:
        """Load production processes into the table."""
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                processos = ProducaoService(session).listar_processos()
        except SQLAlchemyError:
            self.modelo.definir_processos([])
            self.status_label.setText("Nao foi possivel carregar a producao.")
            return

        self._todos = list(processos)
        self._invalidar_cache_detalhe()
        self.modelo.definir_processos(self._todos)
        if selecionar_id is not None:
            self._selected_processo_id = selecionar_id
        self._atualizar_filtros()
        self._render()

        if not self._todos:
            self.status_label.setText("Sem processos de produção para mostrar.")

    def _render(self, *_args) -> None:
        """Re-apply the search and filters on the proxy model."""
        selected_id = self._selected_processo_id
        self.proxy.definir_filtros(
            texto=self.campo_pesquisa.texto(),
            estado=self._combo_valor(self.estado_combo),
            cliente=self._combo_valor(self.cliente_combo),
            responsavel=self._combo_valor(self.responsavel_combo),
            so_atrasadas=self.atrasadas_check.isChecked(),
        )
        self.footer_label.setText(
            f"{self.proxy.rowCount()} de {self.modelo.rowCount()}"
        )
        self._sugerir_pesquisa_proxima()
        self._atualizar_contador_obras_ano()
        self._restaurar_selecao_apos_render(selected_id)

    def _atualizar_contador_obras_ano(self) -> None:
        """Count this year's works, narrowed by the Responsável filter."""
        ano_atual = str(QDate.currentDate().year())
        responsavel = self._combo_valor(self.responsavel_combo)

        total = 0
        for processo in self._todos:
            if str(getattr(processo, "ano", "") or "").strip() != ano_atual:
                continue
            if responsavel is not None:
                valor = str(getattr(processo, "responsavel", "") or "").strip()
                if valor.lower() != responsavel.strip().lower():
                    continue
            total += 1

        if responsavel is None:
            self.obras_ano_label.setText(f"Obras {ano_atual}: {total}")
        else:
            self.obras_ano_label.setText(f"Obras {ano_atual} · {responsavel}: {total}")

    def _limpar_filtros(self, manter_vista: bool = False) -> None:
        """Clear search and reset all filters to 'Todos'."""
        widgets = [
            self.campo_pesquisa,
            self.estado_combo,
            self.cliente_combo,
            self.responsavel_combo,
            self.atrasadas_check,
        ]
        if not manter_vista:
            widgets.append(self.vista_combo)

        estados_sinais = [(widget, widget.blockSignals(True)) for widget in widgets]
        self.campo_pesquisa.limpar()
        for combo in (self.estado_combo, self.cliente_combo, self.responsavel_combo):
            if combo.count():
                combo.setCurrentIndex(0)
        self.atrasadas_check.setChecked(False)
        if not manter_vista and self.vista_combo.count():
            self.vista_combo.setCurrentIndex(0)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)
        self._atualizar_filtro_clientes()
        self._render()

    def _atualizar_filtros(self) -> None:
        """Populate filter combos from the loaded list, preserving selection."""
        self._popular_combo(
            self.estado_combo,
            self._combinar_valores(list(ESTADOS_PRODUCAO), self._valores_distintos("estado")),
        )
        responsaveis = self._valores_distintos("responsavel")
        self._popular_combo(self.responsavel_combo, responsaveis)
        self._popular_responsaveis_form(responsaveis)
        self._atualizar_filtro_clientes()

    def _on_responsavel_mudou(self, *_args) -> None:
        """Narrow the client list to the chosen Responsável, then re-render."""
        self._atualizar_filtro_clientes()
        self._render()

    def _atualizar_filtro_clientes(self) -> None:
        """List only the clients that have works for the chosen Responsável."""
        responsavel = self._combo_valor(self.responsavel_combo)
        if responsavel is None:
            clientes = self._valores_distintos("nome_cliente")
        else:
            alvo = responsavel.strip().lower()
            clientes = sorted(
                {
                    str(processo.nome_cliente).strip()
                    for processo in self._todos
                    if processo.nome_cliente
                    and str(processo.nome_cliente).strip()
                    and str(getattr(processo, "responsavel", "") or "").strip().lower()
                    == alvo
                },
                key=str.lower,
            )

        self._popular_combo(self.cliente_combo, clientes)

    def _popular_combo(self, combo: QComboBox, valores: list[str]) -> None:
        atual = combo.currentText() or "Todos"
        estado_anterior = combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos")
        for valor in valores:
            combo.addItem(valor)

        indice = combo.findText(atual)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(estado_anterior)

    def _popular_responsaveis_form(self, valores: list[str]) -> None:
        atual = self.responsavel_form_combo.currentText()
        estado_anterior = self.responsavel_form_combo.blockSignals(True)
        self.responsavel_form_combo.clear()
        self.responsavel_form_combo.addItem("")
        for valor in valores:
            self.responsavel_form_combo.addItem(valor)
        self.responsavel_form_combo.setCurrentText(atual)
        self.responsavel_form_combo.blockSignals(estado_anterior)

    def _valores_distintos(self, atributo: str) -> list[str]:
        valores = {
            str(valor).strip()
            for valor in (
                getattr(processo, atributo, None) for processo in self._todos
            )
            if valor is not None and str(valor).strip()
        }
        return sorted(valores, key=str.lower)

    @staticmethod
    def _combinar_valores(primeiros: list[str], restantes: list[str]) -> list[str]:
        valores: list[str] = []
        vistos: set[str] = set()
        for valor in [*primeiros, *restantes]:
            chave = valor.strip().lower()
            if not chave or chave in vistos:
                continue
            valores.append(valor)
            vistos.add(chave)
        return valores

    @staticmethod
    def _combo_valor(combo: QComboBox) -> str | None:
        valor = combo.currentText().strip()
        if not valor or valor == "Todos":
            return None
        return valor

    def _colunas_user_id(self) -> object:
        current_user = app_session.current_user
        return getattr(current_user, "id", None) or "default"

    def _carregar_config_colunas(self) -> None:
        try:
            with SessionLocal() as session:
                visiveis, larguras = carregar_config(session, self._colunas_user_id())
        except SQLAlchemyError:
            visiveis, larguras = desserializar_config(None)

        self._colunas_visiveis = visiveis
        self._larguras_colunas = {**LARGURAS_DEFAULT_PRODUCAO, **larguras}
        self._aplicar_config_colunas()

    def _aplicar_config_colunas(self) -> None:
        visiveis = set(self._colunas_visiveis)
        self._aplicando_config_colunas = True
        try:
            for column_index, coluna in enumerate(COLUNAS_PRODUCAO):
                self.table.setColumnHidden(column_index, coluna.key not in visiveis)
                largura = self._larguras_colunas.get(
                    coluna.key,
                    LARGURAS_DEFAULT_PRODUCAO.get(coluna.key, 100),
                )
                self.table.setColumnWidth(column_index, largura)
        finally:
            self._aplicando_config_colunas = False
        self._vistas: list[VistaProducao] = []

    def _atualizar_dados_v2(self) -> None:
        """Compare V2 with V3 and let the user pick what to bring over.

        Temporary transition feature: V2 is read-only and nothing is written
        into V3 without an explicit selection.
        """
        if self._dirty:
            QMessageBox.warning(
                self,
                "Atualizar dados V2",
                "Grave ou descarte primeiro as alterações da obra selecionada.",
            )
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_label.setText("A comparar com o Martelo V2...")
        try:
            with SessionLocal() as session:
                comparacao = comparar_v2_com_v3(session)
        except ProducaoV2ConfigError as error:
            QApplication.restoreOverrideCursor()
            self.status_label.setText("Ligação ao V2 não configurada.")
            QMessageBox.warning(self, "Atualizar dados V2", str(error))
            return
        except (SQLAlchemyError, OSError, PermissionError) as error:
            QApplication.restoreOverrideCursor()
            self.status_label.setText("Não foi possível ler o Martelo V2.")
            QMessageBox.critical(
                self,
                "Atualizar dados V2",
                f"Não foi possível ler o Martelo V2.\n\nDetalhe: {error}",
            )
            return
        else:
            QApplication.restoreOverrideCursor()

        if comparacao.vazia:
            self.status_label.setText(
                f"V2 e V3 estão iguais ({comparacao.total_v2} obras verificadas)."
            )
            QMessageBox.information(
                self,
                "Atualizar dados V2",
                f"Sem diferenças. Foram verificadas {comparacao.total_v2} obras do V2.",
            )
            return

        dialog = ProducaoV2SyncDialog(comparacao, self)
        if not dialog.exec():
            self.status_label.setText("Atualização a partir do V2 cancelada.")
            return

        obras_novas = dialog.obras_novas_escolhidas
        diferencas = dialog.diferencas_escolhidas
        if not obras_novas and not diferencas:
            self.status_label.setText("Nada selecionado — o V3 ficou como estava.")
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                resultado = aplicar_selecao(
                    session,
                    obras_novas=obras_novas,
                    diferencas=diferencas,
                )
        finally:
            QApplication.restoreOverrideCursor()

        resumo = (
            f"Obras criadas: {resultado.criados}\n"
            f"Obras atualizadas: {resultado.processos_atualizados}\n"
            f"Campos atualizados: {resultado.campos_atualizados}"
        )
        if resultado.erros:
            resumo += "\n\nErros:\n" + "\n".join(f"- {erro}" for erro in resultado.erros[:10])
            if len(resultado.erros) > 10:
                resumo += f"\n... e mais {len(resultado.erros) - 10}"
            QMessageBox.warning(self, "Atualizar dados V2", resumo)
        else:
            QMessageBox.information(self, "Atualizar dados V2", resumo)

        self.status_label.setText(
            f"V2 → V3: {resultado.criados} criadas, "
            f"{resultado.campos_atualizados} campos atualizados."
        )
        self.carregar_processos(selecionar_id=self._selected_processo_id)

    def _abrir_menu_colunas(self, posicao) -> None:
        """Right-click menu on the table header to toggle visible columns."""
        header = self.table.horizontalHeader()
        menu = QMenu(self)
        menu.setToolTipsVisible(True)

        titulo = menu.addAction("Colunas visíveis")
        titulo.setEnabled(False)
        menu.addSeparator()

        visiveis = set(self._colunas_visiveis)
        for coluna in COLUNAS_PRODUCAO:
            acao = menu.addAction(coluna.titulo)
            acao.setCheckable(True)
            acao.setChecked(coluna.key in visiveis)
            acao.setToolTip(f"Mostrar/esconder a coluna «{coluna.titulo}»")
            acao.toggled.connect(
                lambda marcado, key=coluna.key: self._alternar_coluna(key, marcado)
            )

        menu.addSeparator()
        acao_entrada = menu.addAction("Repor ordem de entrada")
        acao_entrada.setToolTip(
            "Voltar a ordenar pelas obras mais recentes no topo (ordem de entrada)"
        )
        acao_entrada.triggered.connect(self._repor_ordem_entrada)

        acao_todas = menu.addAction("Mostrar todas")
        acao_todas.setToolTip("Mostrar todas as colunas disponíveis")
        acao_todas.triggered.connect(self._mostrar_todas_colunas)

        acao_repor = menu.addAction("Repor colunas por defeito")
        acao_repor.setToolTip("Voltar às colunas e larguras iniciais")
        acao_repor.triggered.connect(self._repor_colunas_default)

        menu.exec(header.mapToGlobal(posicao))

    def _alternar_coluna(self, key: str, marcado: bool) -> None:
        visiveis = set(self._colunas_visiveis)
        if marcado:
            visiveis.add(key)
        elif key in visiveis:
            if len(visiveis) == 1:
                self.status_label.setText("Tem de ficar pelo menos uma coluna visível.")
                return
            visiveis.discard(key)

        self._colunas_visiveis = [
            coluna.key for coluna in COLUNAS_PRODUCAO if coluna.key in visiveis
        ]
        self._aplicar_config_colunas()
        self._guardar_config_colunas()

    # ---- motor de pesquisa ------------------------------------------------
    def _carregar_sinonimos(self) -> None:
        """Load this user's synonyms from the AI profile into the proxy."""
        try:
            with SessionLocal() as session:
                sinonimos = carregar_sinonimos(session, self._colunas_user_id_int())
        except SQLAlchemyError:
            sinonimos = {}
        self.proxy.definir_sinonimos(sinonimos)

    def _colunas_user_id_int(self) -> int | None:
        valor = getattr(app_session.current_user, "id", None)
        return int(valor) if valor else None

    def _sugerir_pesquisa_proxima(self) -> None:
        """Quando não há resultados, propor a palavra parecida que existe."""
        texto = self.campo_pesquisa.texto().strip()
        if self.proxy.rowCount() or not texto:
            return

        sugestao = pesquisa_texto.sugerir_pesquisa(texto, self.modelo.vocabulario())
        if sugestao:
            self.status_label.setText(
                f"Sem resultados para «{texto}». Quis dizer «{sugestao}»?"
            )
        else:
            self.status_label.setText(f"Sem resultados para «{texto}».")

    # ---- vistas guardadas -------------------------------------------------
    def _carregar_vistas(self) -> None:
        """Load this user's saved views into the combo."""
        try:
            with SessionLocal() as session:
                self._vistas = carregar_vistas(session, self._colunas_user_id())
        except SQLAlchemyError:
            self._vistas = []
        self._popular_combo_vistas()

    def _popular_combo_vistas(self, selecionar: str = "") -> None:
        estado_anterior = self.vista_combo.blockSignals(True)
        self.vista_combo.clear()
        self.vista_combo.addItem(VISTA_SEM_FILTROS)
        for vista in self._vistas:
            self.vista_combo.addItem(vista.nome)
        indice = self.vista_combo.findText(selecionar) if selecionar else 0
        self.vista_combo.setCurrentIndex(max(indice, 0))
        self.vista_combo.blockSignals(estado_anterior)

    def _vista_atual(self) -> VistaProducao | None:
        nome = self.vista_combo.currentText()
        if nome == VISTA_SEM_FILTROS:
            return None
        return next((v for v in self._vistas if v.nome == nome), None)

    def _aplicar_vista_escolhida(self, *_args) -> None:
        vista = self._vista_atual()
        if vista is None:
            self._limpar_filtros(manter_vista=True)
            return

        widgets = (
            self.campo_pesquisa,
            self.estado_combo,
            self.cliente_combo,
            self.responsavel_combo,
            self.atrasadas_check,
        )
        estados_sinais = [(w, w.blockSignals(True)) for w in widgets]
        self.campo_pesquisa.definir_texto(vista.texto)
        self.responsavel_combo.setCurrentText(vista.responsavel)
        self._atualizar_filtro_clientes()
        self.estado_combo.setCurrentText(vista.estado)
        self.cliente_combo.setCurrentText(vista.cliente)
        self.atrasadas_check.setChecked(vista.so_atrasadas)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)

        self.status_label.setText(f"Vista «{vista.nome}» aplicada.")
        self._render()

    def _vista_dos_filtros_atuais(self, nome: str) -> VistaProducao:
        return VistaProducao(
            nome=nome,
            texto=self.campo_pesquisa.texto(),
            estado=self.estado_combo.currentText() or "Todos",
            cliente=self.cliente_combo.currentText() or "Todos",
            responsavel=self.responsavel_combo.currentText() or "Todos",
            so_atrasadas=self.atrasadas_check.isChecked(),
        )

    def _abrir_menu_vistas(self) -> None:
        menu = QMenu(self)
        menu.setToolTipsVisible(True)

        acao_guardar = menu.addAction("Guardar filtros atuais como vista…")
        acao_guardar.setToolTip("Cria uma vista nova com a combinação de filtros atual")
        acao_guardar.triggered.connect(self._guardar_vista_atual)

        vista = self._vista_atual()
        acao_eliminar = menu.addAction(
            f"Eliminar a vista «{vista.nome}»" if vista else "Eliminar vista"
        )
        acao_eliminar.setEnabled(vista is not None)
        acao_eliminar.triggered.connect(self._eliminar_vista_atual)

        menu.exec(self.vista_button.mapToGlobal(self.vista_button.rect().bottomLeft()))

    def _guardar_vista_atual(self) -> None:
        sugestao = self.vista_combo.currentText()
        if sugestao == VISTA_SEM_FILTROS:
            sugestao = ""

        nome, confirmou = QInputDialog.getText(
            self,
            "Guardar vista",
            "Nome da vista:",
            text=sugestao,
        )
        if not confirmou:
            return

        nome = nome.strip()
        if not nome:
            self.status_label.setText("A vista precisa de um nome.")
            return
        if nome == VISTA_SEM_FILTROS:
            self.status_label.setText(f"«{VISTA_SEM_FILTROS}» é um nome reservado.")
            return

        self._vistas = substituir_vista(
            self._vistas,
            self._vista_dos_filtros_atuais(nome),
        )
        if self._gravar_vistas():
            self._popular_combo_vistas(selecionar=nome)
            self.status_label.setText(f"Vista «{nome}» guardada.")

    def _eliminar_vista_atual(self) -> None:
        vista = self._vista_atual()
        if vista is None:
            return

        resposta = QMessageBox.question(
            self,
            "Eliminar vista",
            f"Eliminar a vista «{vista.nome}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        self._vistas = remover_vista(self._vistas, vista.nome)
        if self._gravar_vistas():
            self._popular_combo_vistas()
            self.status_label.setText(f"Vista «{vista.nome}» eliminada.")

    def _gravar_vistas(self) -> bool:
        try:
            with SessionLocal() as session:
                guardar_vistas(session, self._colunas_user_id(), self._vistas)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível guardar as vistas.")
            return False
        return True

    def _repor_ordem_entrada(self) -> None:
        """Sort by entry order again: newest works on top."""
        self.table.sortByColumn(COLUNA_ORDEM_ENTRADA, Qt.SortOrder.DescendingOrder)
        self.status_label.setText("Ordenado por ordem de entrada (mais recentes em cima).")

    def _mostrar_todas_colunas(self) -> None:
        self._colunas_visiveis = [coluna.key for coluna in COLUNAS_PRODUCAO]
        self._aplicar_config_colunas()
        self._guardar_config_colunas()

    def _repor_colunas_default(self) -> None:
        self._colunas_visiveis = [
            coluna.key for coluna in COLUNAS_PRODUCAO if coluna.visivel_default
        ]
        self._larguras_colunas = dict(LARGURAS_DEFAULT_PRODUCAO)
        self._aplicar_config_colunas()
        self._guardar_config_colunas()

    def _on_coluna_redimensionada(
        self,
        logical_index: int,
        _old_size: int,
        new_size: int,
    ) -> None:
        if self._aplicando_config_colunas:
            return
        if logical_index < 0 or logical_index >= len(COLUNAS_PRODUCAO):
            return

        self._larguras_colunas[COLUNAS_PRODUCAO[logical_index].key] = int(new_size)
        if self._guardar_larguras_agendado:
            return

        self._guardar_larguras_agendado = True
        QTimer.singleShot(800, self._guardar_config_colunas_debounced)

    def _guardar_config_colunas_debounced(self) -> None:
        self._guardar_larguras_agendado = False
        self._guardar_config_colunas()

    def _guardar_config_colunas(self) -> None:
        for column_index, coluna in enumerate(COLUNAS_PRODUCAO):
            self._larguras_colunas[coluna.key] = self.table.columnWidth(column_index)

        try:
            with SessionLocal() as session:
                guardar_config(
                    session,
                    self._colunas_user_id(),
                    self._colunas_visiveis,
                    self._larguras_colunas,
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel guardar as colunas.")

    def _processo_na_linha_visivel(self, row: int) -> Producao | None:
        """Return the process shown on one *visible* (proxy) row."""
        if row < 0 or row >= self.proxy.rowCount():
            return None
        indice = self.proxy.index(row, 0)
        return indice.data(ProducaoTableModel.ROLE_PROCESSO)

    def _restaurar_selecao_apos_render(self, selected_id: int | None) -> None:
        if selected_id is not None and self._selecionar_processo_id(selected_id):
            if not self._dirty:
                processo = self._processo_visivel_por_id(selected_id)
                if processo is not None:
                    self._fill_form(processo)
            return

        if self._dirty:
            return

        primeiro = self._processo_na_linha_visivel(0)
        if primeiro is not None:
            self._selecionar_processo_id(primeiro.id)
            self._fill_form(primeiro)
        else:
            self._clear_form()

    def _on_select_row(self, *_args) -> None:
        processo = self._processo_na_linha_visivel(self.table.currentIndex().row())
        if processo is None:
            return

        if self._selected_processo_id == processo.id:
            return

        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                if self._selected_processo_id is not None:
                    self._selecionar_processo_id(self._selected_processo_id)
                return
            self._set_dirty(False)

        self._fill_form(processo)

    def _handle_table_double_click(self, index) -> None:
        column = index.column() if index is not None and index.isValid() else -1
        if column < 0 or column >= len(COLUNAS_PRODUCAO):
            return
        if COLUNAS_PRODUCAO[column].key != "processo":
            return

        processo = index.data(ProducaoTableModel.ROLE_PROCESSO)
        if processo is None:
            return

        self.table.selectRow(index.row())
        self._abrir_pastas_processo(processo)

    def _abrir_pastas_processo(self, processo: Producao) -> None:
        try:
            with SessionLocal() as session:
                root_path, arvore = arvore_pastas_processo(
                    session,
                    ano=processo.ano,
                    num_enc_phc=processo.num_enc_phc,
                    tipo_pasta=processo.tipo_pasta,
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as pastas do processo.")
            return

        dialog = PastasProcessoDialog(
            codigo_processo=self._format_value(processo.codigo_processo),
            root_path=root_path,
            arvore=arvore,
            parent=self,
        )
        dialog.exec()

    def _abrir_pasta_versao_selecionada(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para abrir a pasta.")
            return

        try:
            with SessionLocal() as session:
                processo_db = session.get(Producao, processo.id)
                if processo_db is None:
                    raise ValueError("Processo de producao nao encontrado.")
                caminho = caminho_versao_de_processo(session, processo_db)
        except (SQLAlchemyError, ValueError) as error:
            QMessageBox.warning(self, "Abrir pasta", str(error))
            return

        try:
            pasta_existe = caminho.is_dir()
        except OSError:
            pasta_existe = False
        if not pasta_existe:
            self.status_label.setText("Pasta ainda não criada.")
            QMessageBox.warning(self, "Abrir pasta", "Pasta ainda não criada.")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))

    def _lista_material_imos(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para gerar a Lista Material.")
            return

        nome_enc = self.nome_enc_imos_ix_input.text().strip()
        if not nome_enc:
            QMessageBox.warning(self, "Lista Material IMOS", "Nome Enc IMOS IX em falta.")
            return

        values = {
            "RESPONSAVEL": self.responsavel_form_combo.currentText().strip(),
            "REF_CLIENTE": self.ref_cliente_input.text().strip(),
            "OBRA": self.obra_input.text().strip(),
            "NOME_ENC_IMOS_IX": nome_enc,
            "NUM_CLIENTE_PHC": self.num_cliente_phc_input.text().strip(),
            "NOME_CLIENTE": self.cliente_input.text().strip(),
            "NOME_CLIENTE_SIMPLEX": self.cliente_simplex_input.text().strip(),
            "LOCALIZACAO": self.localizacao_input.text().strip(),
            "DESCRICAO_PRODUCAO": self.descricao_producao_text.toPlainText().strip(),
            "DESCRICAO_ARTIGOS": self.descricao_artigos_text.toPlainText().strip(),
            "MATERIAIS": self.materias_usados_text.toPlainText().strip(),
            "QTD": self.qt_artigos_input.text().strip(),
            "PLANO_CORTE": self.nome_plano_corte_input.text().strip(),
            "DATA_CONCLUSAO": self._texto_data(self.data_entrega_input) or "",
            "DATA_INICIO": self._texto_data(self.data_inicio_input) or "",
            "ENC_PHC": self.num_enc_phc_input.text().strip(),
        }

        try:
            with SessionLocal() as session:
                context = prepare_lista_material_imos(
                    session,
                    processo_id=processo.id,
                    nome_enc_imos=nome_enc,
                    values=values,
                )
        except ValueError as error:
            if str(error).startswith("Modelo Excel nao encontrado"):
                QMessageBox.critical(self, "Lista Material IMOS", str(error))
            else:
                QMessageBox.warning(self, "Lista Material IMOS", str(error))
            return

        if context.output_path.exists():
            resposta = QMessageBox.question(
                self,
                "Lista Material IMOS",
                f"O Excel da Lista Material da obra {processo.codigo_processo} já existe:\n"
                f"{context.output_path}\n\nPretende abrir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if resposta == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(context.output_path)))
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_label.setText("A gerar a Lista Material (Excel)...")
        QApplication.processEvents()
        try:
            output_path = execute_lista_material_imos(context)
        except Exception as error:  # Excel COM / PowerShell
            QMessageBox.critical(
                self,
                "Lista Material IMOS",
                "Não foi possível criar o Excel 'Lista Material_IMOS'.\n\n"
                f"Detalhe: {error}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.status_label.setText("Lista Material criada.")
        QMessageBox.information(
            self, "Lista Material IMOS", f"Ficheiro criado:\n{output_path}"
        )

    def _enviar_cutrite(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para enviar ao CUT-RITE.")
            return

        nome_plano = self.nome_plano_corte_input.text().strip()
        nome_enc = self.nome_enc_imos_ix_input.text().strip()
        if not nome_plano:
            QMessageBox.warning(self, "Enviar CUT-RITE", "Nome Plano CUT-RITE em falta.")
            return

        pasta_servidor = str(getattr(processo, "pasta_servidor", "") or "").strip()
        if not pasta_servidor:
            QMessageBox.warning(
                self,
                "Enviar CUT-RITE",
                "Pasta do processo em falta. Crie a pasta antes de enviar ao CUT-RITE.",
            )
            return

        self._cutrite_dialog = CutRiteProgressDialog(self)
        self._cutrite_dialog.add_step("A iniciar o envio para o CUT-RITE.")
        self._cutrite_dialog.show()
        self.enviar_cutrite_button.setEnabled(False)

        self._cutrite_thread = QThread(self)
        self._cutrite_worker = _CutRiteWorker(
            processo_id=processo.id,
            pasta_servidor=pasta_servidor,
            nome_plano=nome_plano,
            nome_enc_imos=nome_enc,
        )
        self._cutrite_worker.moveToThread(self._cutrite_thread)
        self._cutrite_thread.started.connect(self._cutrite_worker.run)
        self._cutrite_worker.progresso.connect(self._cutrite_dialog.add_step)
        self._cutrite_worker.falhou.connect(self._cutrite_falhou)
        self._cutrite_worker.concluido.connect(self._cutrite_concluido)
        self._cutrite_worker.falhou.connect(self._cutrite_thread.quit)
        self._cutrite_worker.concluido.connect(self._cutrite_thread.quit)
        self._cutrite_thread.finished.connect(self._cutrite_worker.deleteLater)
        self._cutrite_thread.finished.connect(self._cutrite_thread.deleteLater)
        self._cutrite_thread.finished.connect(self._finalizar_cutrite)
        self._cutrite_thread.start()

    def _cutrite_concluido(self, destino: str) -> None:
        if self._cutrite_dialog is not None:
            self._cutrite_dialog.finish(success=True)
        self.status_label.setText("Plano CUT-RITE criado.")
        mensagem = "Plano CUT-RITE criado e gravado."
        if destino:
            mensagem += f"\n\nFicheiros em:\n{destino}"
        QMessageBox.information(self, "Enviar CUT-RITE", mensagem)

    def _cutrite_falhou(self, erro: str) -> None:
        if self._cutrite_dialog is not None:
            self._cutrite_dialog.add_step(f"ERRO: {erro}")
            self._cutrite_dialog.finish(success=False)
        self.status_label.setText("Falha ao enviar para o CUT-RITE.")
        QMessageBox.critical(
            self,
            "Enviar CUT-RITE",
            f"Não foi possível concluir o envio para o CUT-RITE.\n\n{erro}",
        )

    def _finalizar_cutrite(self) -> None:
        self.enviar_cutrite_button.setEnabled(True)
        self._cutrite_thread = None
        self._cutrite_worker = None

    def _exportar_resumo_pdf(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para exportar o resumo.")
            return

        nome_plano = self.nome_plano_corte_input.text().strip()
        if not nome_plano:
            QMessageBox.warning(self, "Exportar Resumo (PDF)", "Nome Plano CUT-RITE em falta.")
            return

        pasta_servidor = str(getattr(processo, "pasta_servidor", "") or "").strip()
        if not pasta_servidor:
            QMessageBox.warning(
                self,
                "Exportar Resumo (PDF)",
                "Pasta do processo em falta. Crie a pasta antes de exportar o resumo.",
            )
            return

        self._cutrite_dialog = CutRiteProgressDialog(self)
        self._cutrite_dialog.setWindowTitle("Exportar Resumo (PDF)")
        self._cutrite_dialog.add_step("A iniciar a exportacao do resumo em PDF.")
        self._cutrite_dialog.show()
        self.exportar_resumo_pdf_button.setEnabled(False)

        self._cutrite_thread = QThread(self)
        self._cutrite_worker = _CutRitePdfWorker(
            processo_id=processo.id,
            pasta_servidor=pasta_servidor,
            nome_plano=nome_plano,
        )
        self._cutrite_worker.moveToThread(self._cutrite_thread)
        self._cutrite_thread.started.connect(self._cutrite_worker.run)
        self._cutrite_worker.progresso.connect(self._cutrite_dialog.add_step)
        self._cutrite_worker.falhou.connect(self._resumo_pdf_falhou)
        self._cutrite_worker.concluido.connect(self._resumo_pdf_concluido)
        self._cutrite_worker.falhou.connect(self._cutrite_thread.quit)
        self._cutrite_worker.concluido.connect(self._cutrite_thread.quit)
        self._cutrite_thread.finished.connect(self._cutrite_worker.deleteLater)
        self._cutrite_thread.finished.connect(self._cutrite_thread.deleteLater)
        self._cutrite_thread.finished.connect(self._finalizar_resumo_pdf)
        self._cutrite_thread.start()

    def _resumo_pdf_concluido(self, caminho: str) -> None:
        if self._cutrite_dialog is not None:
            self._cutrite_dialog.finish(success=True)
        self.status_label.setText("Resumo PDF exportado.")
        mensagem = "Resumo do plano exportado para PDF."
        if caminho:
            mensagem += f"\n\nFicheiro:\n{caminho}"
        QMessageBox.information(self, "Exportar Resumo (PDF)", mensagem)

    def _resumo_pdf_falhou(self, erro: str) -> None:
        if self._cutrite_dialog is not None:
            self._cutrite_dialog.add_step(f"ERRO: {erro}")
            self._cutrite_dialog.finish(success=False)
        self.status_label.setText("Falha ao exportar o resumo PDF.")
        QMessageBox.critical(
            self,
            "Exportar Resumo (PDF)",
            f"Nao foi possivel exportar o resumo em PDF.\n\n{erro}",
        )

    def _finalizar_resumo_pdf(self) -> None:
        self.exportar_resumo_pdf_button.setEnabled(True)
        self._cutrite_thread = None
        self._cutrite_worker = None

    def _eliminar_processo(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para eliminar.")
            return

        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
            self._set_dirty(False)

        escolha = self._escolher_modo_eliminacao(processo)
        if escolha is None:
            return
        apagar_registo, apagar_pasta = escolha

        caminho_texto = ""
        if apagar_pasta:
            try:
                with SessionLocal() as session:
                    processo_db = session.get(Producao, processo.id)
                    if processo_db is None:
                        raise ValueError("Processo de producao nao encontrado.")
                    caminho = caminho_versao_de_processo(session, processo_db)
                    caminho_texto = str(caminho)
                    preview = preview_conteudo_pasta(caminho)
            except (SQLAlchemyError, OSError, ValueError) as error:
                QMessageBox.warning(self, "Eliminar obra", str(error))
                return

            aviso_extra = ""
            if not apagar_registo:
                aviso_extra = (
                    "\n\nNota: o registo fica a apontar para uma pasta inexistente."
                )
            resposta = QMessageBox.question(
                self,
                "Confirmar eliminação da pasta",
                (
                    "A pasta abaixo será removida de forma permanente.\n\n"
                    f"{caminho_texto}\n\n"
                    "Conteúdo encontrado:\n"
                    f"{preview}"
                    f"{aviso_extra}"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return

        resposta = QMessageBox.question(
            self,
            "Confirmação final",
            self._mensagem_confirmacao_eliminacao(
                processo,
                apagar_registo=apagar_registo,
                apagar_pasta=apagar_pasta,
                caminho_pasta=caminho_texto,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                eliminar_processo_completo(
                    session,
                    processo_id=processo.id,
                    apagar_registo=apagar_registo,
                    apagar_pasta=apagar_pasta,
                )
        except (PermissionError, OSError, ValueError) as error:
            if apagar_pasta:
                QMessageBox.warning(
                    self,
                    "Eliminar obra",
                    f"Pasta não apagada; registo mantido.\n\n{error}",
                )
            else:
                QMessageBox.warning(self, "Eliminar obra", str(error))
            return
        except SQLAlchemyError as error:
            QMessageBox.warning(
                self,
                "Eliminar obra",
                f"Não foi possível eliminar o registo na BD.\n\n{error}",
            )
            return

        selecionar_id = None if apagar_registo else processo.id
        self.carregar_processos(selecionar_id=selecionar_id)
        self.status_label.setText(
            self._mensagem_sucesso_eliminacao(
                apagar_registo=apagar_registo,
                apagar_pasta=apagar_pasta,
            )
        )

    def _escolher_modo_eliminacao(
        self,
        processo: Producao,
    ) -> tuple[bool, bool] | None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Eliminar obra")
        box.setText(
            f"Escolha o que eliminar para {self._format_value(processo.codigo_processo)}."
        )
        box.setInformativeText("Esta ação pode remover dados de forma permanente.")
        only_db_button = box.addButton(
            "Só registo (BD)",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        only_folder_button = box.addButton(
            "Só pasta (servidor)",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        both_button = box.addButton(
            "Pasta + registo",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = box.addButton(
            "Cancelar",
            QMessageBox.ButtonRole.RejectRole,
        )
        box.setDefaultButton(cancel_button)
        box.setEscapeButton(cancel_button)
        box.exec()

        clicked = box.clickedButton()
        if clicked == only_db_button:
            return True, False
        if clicked == only_folder_button:
            return False, True
        if clicked == both_button:
            return True, True
        return None

    def _mensagem_confirmacao_eliminacao(
        self,
        processo: Producao,
        *,
        apagar_registo: bool,
        apagar_pasta: bool,
        caminho_pasta: str,
    ) -> str:
        codigo = self._format_value(processo.codigo_processo)
        if apagar_registo and apagar_pasta:
            return (
                f"Eliminar permanentemente a pasta e o registo da obra {codigo}?\n\n"
                f"Pasta:\n{caminho_pasta}"
            )
        if apagar_pasta:
            return (
                f"Eliminar permanentemente só a pasta da obra {codigo}?\n\n"
                f"Pasta:\n{caminho_pasta}\n\n"
                "O registo na BD será mantido."
            )
        return (
            f"Eliminar só o registo na BD da obra {codigo}?\n\n"
            "A pasta no servidor será mantida."
        )

    @staticmethod
    def _mensagem_sucesso_eliminacao(
        *,
        apagar_registo: bool,
        apagar_pasta: bool,
    ) -> str:
        if apagar_registo and apagar_pasta:
            return "Pasta e registo eliminados."
        if apagar_pasta:
            return "Pasta eliminada. O registo foi mantido."
        return "Registo eliminado. A pasta foi mantida."

    def _nova_versao(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para criar nova versão.")
            return

        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
            self._set_dirty(False)

        self._executar_nova_versao(processo_id=processo.id)

    def _executar_nova_versao(self, *, processo_id: int) -> None:
        try:
            with SessionLocal() as session:
                preparado = preparar_nova_versao(session, processo_id=processo_id)
        except ValueError as error:
            QMessageBox.warning(self, "Nova Versão", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível preparar a nova versão.")
            return

        sug_cutrite = preparado["sug_cutrite"]
        sug_obra = preparado["sug_obra"]
        dialog = NovaVersaoProcessoDialog(
            versao_obra_sug_cutrite=sug_cutrite[0],
            versao_plano_sug_cutrite=sug_cutrite[1],
            versao_obra_sug_obra=sug_obra[0],
            versao_plano_sug_obra=sug_obra[1],
            existing_keys=preparado["existing_keys"],
            folder_root=preparado["folder_root"],
            folder_tree=preparado["folder_tree"],
            parent=self,
        )
        if not dialog.exec():
            return

        versao_obra, versao_plano = dialog.values()
        current_user_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )

        try:
            with SessionLocal() as session:
                novo = criar_nova_versao(
                    session,
                    processo_id=processo_id,
                    versao_obra=versao_obra,
                    versao_plano=versao_plano,
                    criar_pasta=True,
                    current_user_id=current_user_id,
                )
                novo_id = novo.id
                codigo = novo.codigo_processo
        except ValueError as error:
            QMessageBox.warning(self, "Nova Versão", str(error))
            return
        except OSError as error:
            QMessageBox.warning(self, "Nova Versão", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar a nova versão.")
            return

        self.carregar_processos(selecionar_id=novo_id)
        self.status_label.setText(f"Versão {codigo} criada (+ pasta).")

    def _processo_selecionado(self) -> Producao | None:
        processo = self._processo_na_linha_visivel(self.table.currentIndex().row())
        if processo is not None:
            return processo
        if self._selected_processo_id is not None:
            return self._processo_visivel_por_id(self._selected_processo_id)
        return None

    def _fill_form(self, proc: Producao) -> None:
        """Fill detail widgets from one production process without marking dirty."""
        self._a_preencher_form = True
        estados = self._bloquear_sinais_form()
        try:
            self._cliente_id = proc.cliente_id
            self.ano_input.setText(self._format_value(proc.ano))
            self.num_enc_phc_input.setText(self._format_value(proc.num_enc_phc))
            self.versao_obra_input.setText(self._format_value(proc.versao_obra))
            self.versao_plano_input.setText(self._format_value(proc.versao_plano))
            self.cliente_input.setText(self._format_value(proc.nome_cliente))
            self.cliente_simplex_input.setText(
                self._format_value(proc.nome_cliente_simplex)
            )
            self.num_cliente_phc_input.setText(self._format_value(proc.num_cliente_phc))
            self.num_orcamento_input.setText(self._format_value(proc.num_orcamento))
            self.versao_orc_input.setText(self._format_value(proc.versao_orc))
            self.preco_total_input.setText(self._format_value(proc.preco_total))
            self.qt_artigos_input.setText(self._format_value(proc.qt_artigos))

            self._set_combo_text(self.estado_form_combo, proc.estado)
            self._set_combo_text(self.responsavel_form_combo, proc.responsavel)
            self.ref_cliente_input.setText(self._format_value(proc.ref_cliente))
            self.obra_input.setText(self._format_value(proc.obra))
            self.localizacao_input.setText(self._format_value(proc.localizacao))
            self._definir_data(self.data_inicio_input, proc.data_inicio)
            self._definir_data(self.data_entrega_input, proc.data_entrega)
            self._set_combo_text(self.tipo_pasta_combo, proc.tipo_pasta)
            self.descricao_artigos_text.setPlainText(
                self._format_value(proc.descricao_artigos)
            )
            self.materias_usados_text.setPlainText(
                self._format_value(proc.materias_usados)
            )
            self.descricao_producao_text.setPlainText(
                self._format_value(proc.descricao_producao)
            )
            self.notas1_text.setPlainText(self._format_value(proc.notas1))
            self.notas2_text.setPlainText(self._format_value(proc.notas2))
            self.notas3_text.setPlainText(self._format_value(proc.notas3))
            self._selected_processo_id = proc.id
            self._atualizar_campos_derivados()
            self._pedir_detalhe_obra(proc)
        finally:
            self._restaurar_sinais_form(estados)
            self._a_preencher_form = False
        self._set_dirty(False)

    def _clear_form(self) -> None:
        estados = self._bloquear_sinais_form()
        try:
            for line in self._readonly_widgets:
                line.clear()
            for widget in self._editable_widgets:
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QTextEdit):
                    widget.clear()
                elif isinstance(widget, QDateEdit):
                    widget.setDate(DATA_VAZIA)
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(-1)
            self._cliente_id = None
            self._imagem_path = None
            self._selected_processo_id = None
            self._mostrar_detalhe_vazio()
        finally:
            self._restaurar_sinais_form(estados)
        self._set_dirty(False)

    def _collect_form(self) -> dict:
        """Collect editable fields from the detail form."""
        return {
            "codigo_processo": self.processo_input.text().strip(),
            "ano": self.ano_input.text().strip(),
            "num_enc_phc": self.num_enc_phc_input.text().strip(),
            "versao_obra": self.versao_obra_input.text().strip(),
            "versao_plano": self.versao_plano_input.text().strip(),
            "cliente_id": self._cliente_id,
            "nome_cliente": self._none_if_empty(self.cliente_input.text()),
            "nome_cliente_simplex": self._none_if_empty(
                self.cliente_simplex_input.text()
            ),
            "num_cliente_phc": self._none_if_empty(self.num_cliente_phc_input.text()),
            "num_orcamento": self._none_if_empty(self.num_orcamento_input.text()),
            "versao_orc": self._none_if_empty(self.versao_orc_input.text()),
            "preco_total": self._decimal_or_none(self.preco_total_input.text()),
            "qt_artigos": self._int_or_none(self.qt_artigos_input.text()),
            "estado": self.estado_form_combo.currentText().strip(),
            "responsavel": self._none_if_empty(
                self.responsavel_form_combo.currentText()
            ),
            "ref_cliente": self._none_if_empty(self.ref_cliente_input.text()),
            "obra": self._none_if_empty(self.obra_input.text()),
            "localizacao": self._none_if_empty(self.localizacao_input.text()),
            "data_inicio": self._texto_data(self.data_inicio_input),
            "data_entrega": self._texto_data(self.data_entrega_input),
            "tipo_pasta": self.tipo_pasta_combo.currentText().strip(),
            "descricao_artigos": self._none_if_empty(
                self.descricao_artigos_text.toPlainText()
            ),
            "materias_usados": self._none_if_empty(
                self.materias_usados_text.toPlainText()
            ),
            "descricao_producao": self._none_if_empty(
                self.descricao_producao_text.toPlainText()
            ),
            "notas1": self._none_if_empty(self.notas1_text.toPlainText()),
            "notas2": self._none_if_empty(self.notas2_text.toPlainText()),
            "notas3": self._none_if_empty(self.notas3_text.toPlainText()),
        }

    def _validar_obrigatorios_para_gravar(self, data: dict) -> bool:
        obrigatorios = (
            ("ano", "Ano"),
            ("num_enc_phc", "Nº Enc PHC"),
            ("versao_obra", "V. Obra"),
            ("versao_plano", "V. CutRite"),
        )
        for campo, label in obrigatorios:
            if not str(data.get(campo) or "").strip():
                QMessageBox.warning(self, "Guardar produção", f"Preencha {label}.")
                return False

        if not data.get("data_inicio"):
            QMessageBox.warning(
                self,
                "Guardar produção",
                "Preencha a Data Início no formato dd-mm-aaaa.",
            )
            return False
        if not data.get("data_entrega"):
            QMessageBox.warning(
                self,
                "Guardar produção",
                "Preencha a Data Entrega no formato dd-mm-aaaa.",
            )
            return False
        return True

    def _save(self) -> None:
        """Persist the selected production process edits."""
        if self._selected_processo_id is None:
            self.status_label.setText("Selecione uma obra de produção.")
            return

        try:
            data = self._collect_form()
        except ValueError as error:
            QMessageBox.warning(self, "Guardar produção", str(error))
            return
        if not self._validar_obrigatorios_para_gravar(data):
            return
        if data["estado"] not in ESTADOS_PRODUCAO:
            self.status_label.setText("Estado de produção inválido.")
            return
        if data["tipo_pasta"] not in TIPOS_PASTA_PRODUCAO:
            self.status_label.setText("Tipo de pasta inválido.")
            return

        updated_by_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )
        proc_id = self._selected_processo_id

        try:
            with SessionLocal() as session:
                ProducaoService(session).atualizar_processo(
                    proc_id,
                    data,
                    updated_by_id=updated_by_id,
                )
        except ValueError as error:
            QMessageBox.warning(self, "Guardar produção", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível guardar a produção.")
            return

        self._set_dirty(False)
        self.carregar_processos(selecionar_id=proc_id)
        self.status_label.setText("Produção guardada.")

    def _converter_orcamento(self) -> None:
        """Open the conversion dialog and create the selected production process."""
        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
            self._set_dirty(False)

        dialog = ConverterOrcamentoDialog(self)
        if not dialog.exec():
            return
        if dialog.selected_orcamento_id is None or dialog.selected_versao_id is None:
            return

        created_by_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )

        try:
            with SessionLocal() as session:
                processo = converter_orcamento(
                    session,
                    orcamento_id=dialog.selected_orcamento_id,
                    versao_id=dialog.selected_versao_id,
                    created_by_id=created_by_id,
                    num_enc_phc=dialog.selected_num_enc_phc,
                )
                processo_id = processo.id
                codigo_processo = processo.codigo_processo
        except ValueError as error:
            QMessageBox.warning(self, "Converter Orçamento", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível converter o orçamento.")
            return

        self.carregar_processos(selecionar_id=processo_id)
        self.status_label.setText(f"Processo {codigo_processo} criado.")

    def _novo_processo(self) -> None:
        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
            self._set_dirty(False)

        dialog = NovoProcessoDialog(self)
        if not dialog.exec():
            return
        dados = dialog.result_data()
        if not dados:
            return

        try:
            with SessionLocal() as session:
                existentes = listar_processos_por_encomenda(
                    session,
                    ano=dados.get("ano"),
                    num_enc_phc=dados.get("num_enc_phc"),
                )
                existentes_info = [
                    {
                        "id": p.id,
                        "codigo": p.codigo_processo,
                        "estado": p.estado,
                        "versao_obra": p.versao_obra,
                        "versao_plano": p.versao_plano,
                        "data_inicio": p.data_inicio,
                        "data_entrega": p.data_entrega,
                    }
                    for p in existentes
                ]
        except SQLAlchemyError:
            existentes_info = []

        if existentes_info:
            self._tratar_encomenda_existente(dados, existentes_info)
            return

        current_user = app_session.current_user
        created_by_id = current_user.id if current_user is not None else None
        partes_nome = (current_user.nome or "").split() if current_user is not None else []
        responsavel = partes_nome[0] if partes_nome else None
        try:
            with SessionLocal() as session:
                processo = criar_processo_externo(
                    session,
                    dados=dados,
                    responsavel=responsavel,
                    created_by_id=created_by_id,
                )
                processo_id = processo.id
                codigo_processo = processo.codigo_processo
                pasta_servidor = processo.pasta_servidor or ""
        except ValueError as error:
            QMessageBox.warning(self, "Novo Processo", str(error))
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "Novo Processo",
                f"Processo não criado (falha ao criar a pasta no servidor):\n\n{error}",
            )
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar o processo.")
            return

        self.carregar_processos(selecionar_id=processo_id)
        mensagem = f"Processo {codigo_processo} criado."
        if pasta_servidor:
            mensagem += f"\n\nPasta criada no servidor:\n{pasta_servidor}"
        QMessageBox.information(self, "Novo Processo", mensagem)
        self.status_label.setText(f"Processo {codigo_processo} criado.")

    def _tratar_encomenda_existente(self, dados: dict, existentes: list[dict]) -> None:
        linhas = "\n".join(
            f"  • {e['codigo']} — {e['estado'] or 'sem estado'}"
            f" (Início {e['data_inicio'] or '—'}, Entrega {e['data_entrega'] or '—'})"
            for e in existentes
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Encomenda já existe")
        box.setText(
            f"Já existe obra para esta encomenda "
            f"(Ano {dados.get('ano')}, Nº Enc {dados.get('num_enc_phc')})."
        )
        box.setInformativeText(
            f"{linhas}\n\nQuer criar uma NOVA VERSÃO (da Obra ou de CUT-RITE) "
            "a partir da existente?"
        )
        nova_versao_btn = box.addButton("Nova Versão", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not nova_versao_btn:
            return

        base = max(
            existentes,
            key=lambda e: (str(e["versao_obra"] or ""), str(e["versao_plano"] or "")),
        )
        self._executar_nova_versao(processo_id=base["id"])

    def _on_user_edit(self, *_args) -> None:
        if self._a_preencher_form or self._selected_processo_id is None:
            return
        self._set_dirty(True)

    def _on_campo_derivado_editado(self, *_args) -> None:
        self._atualizar_campos_derivados()
        self._on_user_edit()

    def _atualizar_campos_derivados(self) -> None:
        ano = self.ano_input.text()
        num_enc_phc = self.num_enc_phc_input.text()
        versao_obra = self.versao_obra_input.text()
        versao_plano = self.versao_plano_input.text()
        nome_cliente = self.cliente_input.text()
        nome_simplex = self.cliente_simplex_input.text()
        ref_cliente = self.ref_cliente_input.text()

        self.processo_input.setText(
            codigo_processo_com_cliente(
                ano,
                num_enc_phc,
                versao_obra,
                versao_plano,
                nome_simplex=nome_simplex,
                nome_cliente=nome_cliente,
                ref_cliente=ref_cliente,
            )
        )
        self.nome_plano_corte_input.setText(
            gerar_nome_plano_cut_rite(
                ano,
                num_enc_phc,
                versao_obra,
                versao_plano,
                nome_cliente_simplex=nome_simplex,
                nome_cliente=nome_cliente,
                ref_cliente=ref_cliente,
            )
        )
        self.nome_enc_imos_ix_input.setText(
            gerar_nome_enc_imos_ix(
                ano,
                num_enc_phc,
                versao_obra,
                nome_cliente_simplex=nome_simplex,
                nome_cliente=nome_cliente,
                ref_cliente=ref_cliente,
            )
        )

    # ---- detalhe resolvido em background ---------------------------------
    def _iniciar_thread_detalhe(self) -> None:
        """Start the worker thread that reads the file server."""
        self._detalhe_thread = QThread(self)
        self._detalhe_worker = DetalheObraWorker()
        self._detalhe_worker.moveToThread(self._detalhe_thread)
        self.detalhe_pedido.connect(self._detalhe_worker.resolver)
        self._detalhe_worker.resolvido.connect(self._on_detalhe_resolvido)
        self._detalhe_thread.start()

        aplicacao = QApplication.instance()
        if aplicacao is not None:
            aplicacao.aboutToQuit.connect(self._parar_thread_detalhe)

    def _pedir_detalhe_obra(self, proc: Producao | None) -> None:
        """Ask the worker thread for everything that lives on the server."""
        if proc is None:
            self._mostrar_detalhe_vazio()
            return

        cacheado = self._cache_detalhe.get(proc.id)
        if cacheado is not None:
            self._aplicar_detalhe(cacheado)
            return

        self._pedido_detalhe += 1
        # Marca este como o pedido válido: o worker descarta os anteriores.
        self._detalhe_worker.ultimo_pedido = self._pedido_detalhe
        self._mostrar_detalhe_a_carregar()
        self.detalhe_pedido.emit(self._pedido_detalhe, proc.id)

    def _mostrar_detalhe_a_carregar(self) -> None:
        self._imagem_path = None
        self._imagem_preview_pixmap_original = None
        self.imagem_preview.setPixmap(QPixmap())
        self.imagem_preview.setText("A carregar do servidor…")
        self.imagem_stack.setCurrentWidget(self.imagem_preview)
        self.pasta_obra_input.setText("")
        self.pasta_obra_input.setToolTip("A carregar do servidor…")
        self._definir_link_pasta_orcamento(None)

    def _mostrar_detalhe_vazio(self) -> None:
        self._imagem_path = None
        self._imagem_preview_pixmap_original = None
        self.imagem_preview.setPixmap(QPixmap())
        self.imagem_preview.setText("Sem imagem")
        self.imagem_preview.setToolTip("")
        self.imagem_stack.setCurrentWidget(self.imagem_preview)
        self.pasta_obra_input.clear()
        self.pasta_obra_input.setToolTip("Sem obra selecionada")
        self._definir_link_pasta_orcamento(None)

    def _on_detalhe_resolvido(self, resultado) -> None:
        """Apply a worker result, ignoring answers to older selections."""
        if resultado.processo_id != self._selected_processo_id:
            return
        self._cache_detalhe[resultado.processo_id] = resultado
        self._aplicar_detalhe(resultado)

    def _aplicar_detalhe(self, resultado) -> None:
        self.pasta_obra_input.setText(resultado.pasta_obra)
        self.pasta_obra_input.setCursorPosition(0)
        self.pasta_obra_input.setToolTip(
            resultado.pasta_obra or "Pasta ainda não definida para esta obra"
        )

        self._definir_link_pasta_orcamento(
            Path(resultado.pasta_orcamento) if resultado.pasta_orcamento else None
        )

        self._imagem_path = resultado.imagem_path or None
        if resultado.tem_imagem:
            self._imagem_preview_pixmap_original = QPixmap.fromImage(resultado.imagem)
            self.imagem_preview.setToolTip(resultado.imagem_path)
            self.imagem_stack.setCurrentWidget(self.imagem_preview)
            self._ajustar_imagem_preview()
            return

        self._imagem_preview_pixmap_original = None
        self.imagem_preview.setPixmap(QPixmap())

        if not resultado.imagem_path and resultado.pasta_servidor_existe:
            pasta = resultado.pasta_servidor
            self.fs_model.setRootPath(pasta)
            self.arvore_pasta.setRootIndex(self.fs_model.index(pasta))
            self.arvore_pasta.setToolTip(pasta)
            self.imagem_stack.setCurrentWidget(self.arvore_pasta)
            return

        self.imagem_preview.setText(resultado.imagem_aviso or "Sem imagem")
        self.imagem_preview.setToolTip(resultado.imagem_path or resultado.pasta_servidor)
        self.imagem_stack.setCurrentWidget(self.imagem_preview)

    def _invalidar_cache_detalhe(self, processo_id: int | None = None) -> None:
        """Drop cached server data so the next selection reads it again."""
        if processo_id is None:
            self._cache_detalhe.clear()
        else:
            self._cache_detalhe.pop(processo_id, None)

    def _parar_thread_detalhe(self) -> None:
        thread = getattr(self, "_detalhe_thread", None)
        if thread is None or not thread.isRunning():
            return
        thread.quit()
        thread.wait(3000)

    def _abrir_item_arvore(self, index) -> None:
        caminho = self.fs_model.filePath(index)
        if caminho:
            QDesktopServices.openUrl(QUrl.fromLocalFile(caminho))

    def _atualizar_preview_imagem(self) -> None:
        """Redraw the preview from the pixmap the worker already produced."""
        if not hasattr(self, "imagem_preview"):
            return
        if self._imagem_preview_pixmap_original is None:
            self.imagem_preview.setPixmap(QPixmap())
            if not self.imagem_preview.text():
                self.imagem_preview.setText("Sem imagem")
            return
        self._ajustar_imagem_preview()

    def _ajustar_imagem_preview(self) -> None:
        if not hasattr(self, "imagem_preview"):
            return
        original = self._imagem_preview_pixmap_original
        if original is None or original.isNull():
            return

        tamanho = self.imagem_preview.size()
        scaled = original.scaled(
            max(tamanho.width() - 4, 1),
            max(tamanho.height() - 4, 1),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.imagem_preview.setText("")
        self.imagem_preview.setPixmap(scaled)

    def _abrir_imagem_pdf(self) -> None:
        if not self._imagem_path:
            return
        path = Path(self._imagem_path)
        if not path.is_file():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.save_button.setEnabled(dirty and self._selected_processo_id is not None)

    def _indice_visivel_do_processo(self, proc_id: int):
        """Proxy index of one process id, or None when it is filtered out."""
        linha_origem = self.modelo.linha_do_processo(proc_id)
        if linha_origem < 0:
            return None
        indice = self.proxy.mapFromSource(self.modelo.index(linha_origem, 0))
        return indice if indice.isValid() else None

    def _selecionar_processo_id(self, proc_id: int) -> bool:
        indice = self._indice_visivel_do_processo(proc_id)
        if indice is None:
            return False

        selecao = self.table.selectionModel()
        estado_sinais = selecao.blockSignals(True)
        self.table.selectRow(indice.row())
        self.table.setCurrentIndex(indice)
        selecao.blockSignals(estado_sinais)
        return True

    def _processo_visivel_por_id(self, proc_id: int) -> Producao | None:
        indice = self._indice_visivel_do_processo(proc_id)
        if indice is None:
            return None
        return indice.data(ProducaoTableModel.ROLE_PROCESSO)

    def _bloquear_sinais_form(self) -> list[tuple[QWidget, bool]]:
        widgets = [*self._readonly_widgets, *self._editable_widgets]
        return [(widget, widget.blockSignals(True)) for widget in widgets]

    @staticmethod
    def _restaurar_sinais_form(estados: list[tuple[QWidget, bool]]) -> None:
        for widget, estado_anterior in estados:
            widget.blockSignals(estado_anterior)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: object) -> None:
        text = "" if value is None else str(value).strip()
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif combo.isEditable():
            combo.setCurrentText(text)
        else:
            combo.setCurrentIndex(-1)

    @staticmethod
    def _none_if_empty(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None

    @staticmethod
    def _decimal_or_none(value: object) -> Decimal | None:
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        text = text.replace(" ", "").replace(" ", "").replace("€", "")
        if "," in text:
            # Formato pt: o ponto é separador de milhares.
            text = text.replace(".", "").replace(",", ".")
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError("Preço total inválido.") from exc

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError("Qt artigos inválida.") from exc

    @staticmethod
    def _format_value(value: object) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _format_date(value: object) -> str:
        if value is None:
            return ""
        try:
            return value.strftime("%d-%m-%Y")
        except AttributeError:
            return ""

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, coluna in enumerate(COLUNAS_PRODUCAO):
            largura = self.COLUMN_WIDTHS.get(coluna.key)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._ajustar_imagem_preview()
