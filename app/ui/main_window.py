"""Main application window for Martelo Orcamentos V3."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models import User
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import OrcamentoService
from app.services.permission_service import (
    DEFAULT_USER_PERMISSIONS,
    MENU_PERMISSIONS,
    is_admin,
    permissions_for_user,
)
from app.ui import tema
from app.ui.pages import (
    BibliotecaModulosPage,
    ArquivoV2Page,
    CatalogoAuditoriaPage,
    CaminhosSistemaPage,
    ClientesPage,
    CusteioAuditoriaPage,
    ConfiguracoesPage,
    CusteioSimplificadoTarifasPage,
    DefPecasPage,
    DefValuesetChavesPage,
    DefValuesetModelosPage,
    EncomendasPage,
    InicioPage,
    ImosLigacaoPage,
    MargensPadraoPage,
    MateriasPrimasPage,
    OperacoesMaquinasPage,
    OrcamentoDetailPage,
    OrcamentosPage,
    PesquisaIAPage,
    PontoSituacaoPage,
    ProducaoPage,
    RegrasQuantidadePage,
    UserManagementPage,
)


class MainWindow(QMainWindow):
    """Application shell window."""

    # Mapeia o nome da página ao botão da sidebar a destacar.
    _NAV_POR_PAGINA = {
        "inicio": "inicio",
        "orcamentos": "orcamentos",
        "orcamentos_dashboard": "orcamentos",
        "custeio_auditoria": "orcamentos",
        "arquivo_v2": "orcamentos",
        "orcamento_detail": "orcamentos",
        "materias_primas": "materias_primas",
        "clientes": "clientes",
        "producao": "producao",
        "encomendas_phc": "producao",
        "ponto_situacao": "producao",
    }

    _PAGE_PERMISSION = {
        "orcamentos": "menu.orcamentos",
        "orcamentos_dashboard": "menu.orcamentos",
        "custeio_auditoria": "menu.orcamentos",
        "arquivo_v2": "menu.orcamentos",
        "orcamento_detail": "menu.orcamentos",
        "materias_primas": "menu.materias_primas",
        "pesquisa_ia": "menu.pesquisa_ia",
        "clientes": "menu.clientes",
        "producao": "menu.producao",
        "encomendas_phc": "menu.encomendas_phc",
        "ponto_situacao": "menu.ponto_situacao",
        "configuracoes": "menu.configuracoes",
        "pecas": "menu.configuracoes",
        "caminhos_sistema": "menu.configuracoes",
        "imos_ligacao": "menu.configuracoes",
        "operacoes_maquinas": "menu.configuracoes",
        "valueset_chaves": "menu.configuracoes",
        "valueset_modelos": "menu.configuracoes",
        "margens_padrao": "menu.configuracoes",
        "regras_quantidade": "menu.configuracoes",
        "biblioteca_modulos": "menu.configuracoes",
        "catalogo_auditoria": "menu.configuracoes",
        "custeio_simplificado_tarifas": "menu.configuracoes",
        "user_management": "menu.configuracoes",
    }

    logout_requested = Signal()

    def __init__(self, authenticated_user: User | None = None) -> None:
        super().__init__()

        self.authenticated_user = authenticated_user
        self._permissions = self._load_permissions()

        self.setWindowTitle("Martelo Or\u00e7amentos V3")
        self.resize(1100, 720)

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()

        # Toggle to hide/show the left navigation menu (phase 8V.2): purely
        # visual; the page stack (and the current selection) is untouched.
        self.toggle_sidebar_button = QPushButton()
        self.toggle_sidebar_button.setObjectName("toggleSidebarButton")
        self.toggle_sidebar_button.setFixedSize(36, 32)
        self.toggle_sidebar_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft)
        )
        self.toggle_sidebar_button.setAccessibleName("Ocultar menu principal")
        self.toggle_sidebar_button.setToolTip("Ocultar menu")
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)

        title = QLabel("Martelo Or\u00e7amentos V3")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        user_label = QLabel(self._format_user_info())
        user_label.setObjectName("authenticatedUserInfo")
        user_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        logout_button = QPushButton("Sair")
        logout_button.setObjectName("logoutButton")
        logout_button.clicked.connect(self.request_logout)

        header_layout.addWidget(self.toggle_sidebar_button)
        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(user_label, stretch=1)
        header_layout.addWidget(logout_button)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        self.sidebar.setFixedWidth(180)
        self._sidebar_visivel = True
        sidebar = self.sidebar

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        self.nav_tree = QTreeWidget()
        self.nav_tree.setObjectName("navTree")
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setIndentation(14)
        self.nav_tree.setStyleSheet(tema.ESTILO_ARVORE_NAV)
        self.nav_tree.itemClicked.connect(self._on_nav_item_clicked)

        self._nav_items: dict[str, QTreeWidgetItem] = {}

        def _criar_item(texto: str, page_name: str, parent=None) -> QTreeWidgetItem:
            item = QTreeWidgetItem([texto])
            item.setData(0, Qt.ItemDataRole.UserRole, page_name)
            if parent is None:
                self.nav_tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            self._nav_items[page_name] = item
            return item

        _criar_item("In\u00edcio", "inicio")
        item_orcamentos = _criar_item("Or\u00e7amentos", "orcamentos")
        _criar_item("Dashboard", "orcamentos_dashboard", parent=item_orcamentos)
        _criar_item("Auditoria de Custeio", "custeio_auditoria", parent=item_orcamentos)
        _criar_item("Arquivo V2", "arquivo_v2", parent=item_orcamentos)
        _criar_item("Mat\u00e9rias-Primas", "materias_primas", parent=item_orcamentos)
        _criar_item("Pesquisa IA", "pesquisa_ia", parent=item_orcamentos)
        _criar_item("Clientes", "clientes")
        item_producao = _criar_item("Produção", "producao")
        _criar_item("Encomendas PHC", "encomendas_phc", parent=item_producao)
        _criar_item("Ponto Situa\u00e7\u00e3o", "ponto_situacao", parent=item_producao)
        _criar_item("Configura\u00e7\u00f5es", "configuracoes")
        item_orcamentos.setExpanded(True)
        item_producao.setExpanded(True)
        self._apply_navigation_permissions()

        sidebar_layout.addWidget(self.nav_tree, stretch=1)
        sidebar.setLayout(sidebar_layout)

        self.pages = QStackedWidget()
        self._page_indexes: dict[str, int] = {}
        self._pages_by_name: dict[str, QWidget] = {}
        # Scroll area de cada página: páginas muito largas (ex.: items do
        # orçamento) ganham scrollbar em vez de forçarem a janela maximizada a
        # crescer para fora do ecrã.
        self._page_containers: dict[str, QScrollArea] = {}
        self.orcamentos_page = OrcamentosPage(on_open_orcamento=self.open_orcamento_detail)
        self.inicio_page = InicioPage(
            on_open_orcamentos=lambda: self.show_page("orcamentos"),
            on_open_producao=lambda: self.show_page("producao"),
            on_open_auditoria=self._open_catalogo_auditoria,
            on_open_orcamento=self.open_orcamento_detail,
        )
        self.orcamentos_dashboard_page = InicioPage(
            on_open_orcamentos=lambda: self.show_page("orcamentos"),
            on_open_auditoria=self._open_catalogo_auditoria,
            on_open_orcamento=self.open_orcamento_detail,
            titulo="Dashboard de Orçamentos",
            incluir_producao=False,
        )
        self.custeio_auditoria_page = CusteioAuditoriaPage(
            on_open_orcamento=self._open_custeio_auditoria_item,
            on_navegar_menu=self.navegar_para_resolver,
        )
        self.arquivo_v2_page = ArquivoV2Page()
        self.def_pecas_page = DefPecasPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.materias_primas_page = MateriasPrimasPage()
        self.pesquisa_ia_page = PesquisaIAPage()
        self.caminhos_sistema_page = CaminhosSistemaPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.imos_ligacao_page = ImosLigacaoPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.operacoes_maquinas_page = OperacoesMaquinasPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.valueset_chaves_page = DefValuesetChavesPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.valueset_modelos_page = DefValuesetModelosPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.margens_padrao_page = MargensPadraoPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.regras_quantidade_page = RegrasQuantidadePage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.biblioteca_modulos_page = BibliotecaModulosPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.catalogo_auditoria_page = CatalogoAuditoriaPage(
            on_open_configuracao=self._open_catalogo_auditoria_item,
            on_back=lambda: self.show_page("configuracoes"),
        )
        self.custeio_simplificado_tarifas_page = CusteioSimplificadoTarifasPage(
            on_back=lambda: self.show_page("configuracoes")
        )
        self.clientes_page = ClientesPage()
        self.producao_page = ProducaoPage()
        self.encomendas_page = EncomendasPage()
        self.ponto_situacao_page = PontoSituacaoPage()
        self.user_management_page = (
            UserManagementPage(on_back=lambda: self.show_page("configuracoes"))
            if is_admin(authenticated_user)
            else None
        )
        self.configuracoes_page = ConfiguracoesPage(
            on_open_def_pecas=lambda: self.show_page("pecas"),
            on_open_materias_primas=lambda: self.show_page("materias_primas"),
            on_open_caminhos_sistema=lambda: self.show_page("caminhos_sistema"),
            on_open_imos_ligacao=lambda: self.show_page("imos_ligacao"),
            on_open_operacoes_maquinas=lambda: self.show_page("operacoes_maquinas"),
            on_open_valueset_chaves=lambda: self.show_page("valueset_chaves"),
            on_open_valueset_modelos=lambda: self.show_page("valueset_modelos"),
            on_open_margens_padrao=self._open_margens_padrao,
            on_open_regras_quantidade=self._open_regras_quantidade,
            on_open_biblioteca_modulos=self._open_biblioteca_modulos,
            on_open_catalogo_auditoria=self._open_catalogo_auditoria,
            on_open_custeio_simplificado_tarifas=lambda: self.show_page("custeio_simplificado_tarifas"),
            on_open_user_management=(
                self._open_user_management if self.user_management_page is not None else None
            ),
        )
        self._add_page("inicio", self.inicio_page)
        self._add_page("orcamentos", self.orcamentos_page)
        self._add_page("orcamentos_dashboard", self.orcamentos_dashboard_page)
        self._add_page("custeio_auditoria", self.custeio_auditoria_page)
        self._add_page("arquivo_v2", self.arquivo_v2_page)
        self._add_page("pecas", self.def_pecas_page)
        self._add_page("materias_primas", self.materias_primas_page)
        self._add_page("pesquisa_ia", self.pesquisa_ia_page)
        self._add_page("caminhos_sistema", self.caminhos_sistema_page)
        self._add_page("imos_ligacao", self.imos_ligacao_page)
        self._add_page("operacoes_maquinas", self.operacoes_maquinas_page)
        self._add_page("valueset_chaves", self.valueset_chaves_page)
        self._add_page("valueset_modelos", self.valueset_modelos_page)
        self._add_page("margens_padrao", self.margens_padrao_page)
        self._add_page("regras_quantidade", self.regras_quantidade_page)
        self._add_page("biblioteca_modulos", self.biblioteca_modulos_page)
        self._add_page("catalogo_auditoria", self.catalogo_auditoria_page)
        self._add_page("custeio_simplificado_tarifas", self.custeio_simplificado_tarifas_page)
        self._add_page("clientes", self.clientes_page)
        self._add_page("producao", self.producao_page)
        self._add_page("encomendas_phc", self.encomendas_page)
        self._add_page("ponto_situacao", self.ponto_situacao_page)
        self._add_page("configuracoes", self.configuracoes_page)
        if self.user_management_page is not None:
            self._add_page("user_management", self.user_management_page)

        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.pages, stretch=1)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self._criar_banner_retorno())
        main_layout.addLayout(content_layout, stretch=1)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.show_page("inicio")

    def _format_user_info(self) -> str:
        """Return display text for the authenticated user."""
        if self.authenticated_user is None:
            return "Utilizador: n/a"

        return (
            f"{self.authenticated_user.nome}\n"
            f"@{self.authenticated_user.username} | {self.authenticated_user.role}"
        )

    def _load_permissions(self) -> dict[str, bool]:
        """Load the authenticated account's menu visibility rules."""
        if is_admin(self.authenticated_user):
            return {key: True for key in MENU_PERMISSIONS}
        try:
            with SessionLocal() as session:
                return permissions_for_user(session, self.authenticated_user)
        except Exception:
            # Keeps the app usable during a first migration while still denying
            # technical configuration to normal users.
            return dict(DEFAULT_USER_PERMISSIONS)

    def _apply_navigation_permissions(self) -> None:
        """Hide menu entries that the current account cannot access."""
        nav_permissions = {
            "orcamentos": "menu.orcamentos",
            "materias_primas": "menu.materias_primas",
            "pesquisa_ia": "menu.pesquisa_ia",
            "clientes": "menu.clientes",
            "producao": "menu.producao",
            "encomendas_phc": "menu.encomendas_phc",
            "ponto_situacao": "menu.ponto_situacao",
            "configuracoes": "menu.configuracoes",
        }
        for page_name, permission_key in nav_permissions.items():
            item = self._nav_items.get(page_name)
            if item is not None:
                item.setHidden(not self._permissions.get(permission_key, False))

    def request_logout(self) -> None:
        """Emit a logout request."""
        self.logout_requested.emit()

    def toggle_sidebar(self) -> None:
        """Hide/show the left navigation menu (phase 8V.2).

        Purely visual: the page stack and the current page stay as they are, so
        navigation state is preserved when the menu is shown again. A tracked
        flag (not isVisible) drives the toggle so it works regardless of whether
        the window is currently shown.
        """
        self._sidebar_visivel = not self._sidebar_visivel
        self.sidebar.setVisible(self._sidebar_visivel)
        self.toggle_sidebar_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_ArrowLeft
                if self._sidebar_visivel
                else QStyle.StandardPixmap.SP_ArrowRight
            )
        )
        self.toggle_sidebar_button.setAccessibleName(
            "Ocultar menu principal"
            if self._sidebar_visivel
            else "Mostrar menu principal"
        )
        self.toggle_sidebar_button.setToolTip(
            "Ocultar menu" if self._sidebar_visivel else "Mostrar menu"
        )

    def _open_margens_padrao(self) -> None:
        """Open the default margins page with fresh data."""
        self.margens_padrao_page.carregar()
        self.show_page("margens_padrao")

    def _open_regras_quantidade(self) -> None:
        """Open the quantity rules page with fresh data."""
        self.regras_quantidade_page.carregar()
        self.show_page("regras_quantidade")

    def _open_biblioteca_modulos(self) -> None:
        """Open the module library page with fresh data."""
        self.biblioteca_modulos_page.carregar()
        self.show_page("biblioteca_modulos")

    def _open_catalogo_auditoria(self) -> None:
        """Open the read-only catalog audit with fresh results."""
        self.catalogo_auditoria_page.carregar()
        self.show_page("catalogo_auditoria")

    def _open_user_management(self) -> None:
        """Open and refresh administrator-only account management."""
        if self.user_management_page is None:
            return
        self.user_management_page.carregar()
        self.show_page("user_management")

    def _open_catalogo_auditoria_item(self, item) -> None:
        """Navigate from an audit finding to its responsible configuration."""
        tipo = item.navegacao_tipo
        alvo_id = item.navegacao_id
        if tipo == "PECA":
            self.show_page("pecas")
            self.def_pecas_page.abrir_peca_por_id(alvo_id)
        elif tipo == "OPERACAO":
            self.show_page("operacoes_maquinas")
            self.operacoes_maquinas_page.abrir_operacao_por_id(alvo_id)
        elif tipo == "REGRA":
            self.show_page("regras_quantidade")
            self.regras_quantidade_page.selecionar_regra_por_id(alvo_id)
        elif tipo == "VALUESET_MODELO":
            self.show_page("valueset_modelos")
            self.valueset_modelos_page.abrir_modelo_por_id(alvo_id)
        elif tipo == "MODULO":
            self.show_page("biblioteca_modulos")
            self.biblioteca_modulos_page.selecionar_modulo_por_id(alvo_id)

    def _embrulhar_pagina(self, page: QWidget) -> QScrollArea:
        """Wrap one page in a scroll area so its minimum size never forces the
        (maximized) window to grow beyond the screen; oversized content gets a
        scrollbar instead of ending up unreachable off-screen."""
        container = QScrollArea()
        container.setWidgetResizable(True)
        container.setFrameShape(QFrame.Shape.NoFrame)
        container.setWidget(page)
        return container

    def _add_page(self, name: str, page: QWidget) -> None:
        """Add a page to the central workspace."""
        container = self._embrulhar_pagina(page)
        self._pages_by_name[name] = page
        self._page_containers[name] = container
        self._page_indexes[name] = self.pages.addWidget(container)

    # Texto do banner de retorno, por página de origem.
    _ROTULO_RETORNO = {
        "orcamento_detail": "A resolver um problema do custeio — podes voltar quando terminares.",
        "custeio_auditoria": "A resolver um problema da Auditoria de Custeio — podes voltar quando terminares.",
    }

    def _criar_banner_retorno(self) -> QWidget:
        """Barra de "voltar" mostrada quando o assistente envia para outro menu.

        Sem isto, ao saltar para Matérias-Primas/Máquinas o utilizador ficava
        sem forma de regressar ao custeio onde estava.
        """
        self._retorno_resolver: str | None = None
        self._retorno_banner = QFrame()
        self._retorno_banner.setStyleSheet(
            f"QFrame {{ background: {tema.OCRE_SUAVE};"
            f" border: 1px solid {tema.CASTANHO_MEDIO}; border-radius: 6px; }}"
        )
        lay = QHBoxLayout(self._retorno_banner)
        lay.setContentsMargins(12, 6, 12, 6)
        self._retorno_label = QLabel("")
        self._retorno_label.setStyleSheet(
            f"color: {tema.OCRE_ESCURO}; font-weight: bold; background: transparent; border: none;"
        )
        voltar = QPushButton("← Voltar")
        voltar.setToolTip("Voltar ao ecrã onde estavas antes de vir resolver o problema.")
        voltar.clicked.connect(self._voltar_resolver)
        lay.addWidget(self._retorno_label, stretch=1)
        lay.addWidget(voltar)
        self._retorno_banner.setVisible(False)
        return self._retorno_banner

    def _pagina_atual_nome(self) -> str | None:
        indice = self.pages.currentIndex()
        for nome, idx in self._page_indexes.items():
            if idx == indice:
                return nome
        return None

    def navegar_para_resolver(self, pagina_destino: str, alvo: str | None = None) -> None:
        """Vai para um menu de resolução guardando de onde veio (para poder voltar).

        ``alvo`` (Fase 3B) permite destacar o campo/linha exato no destino — ex.:
        a Ref LE da matéria-prima na página Matérias-Primas.
        """
        origem = self._pagina_atual_nome()
        if origem is not None and origem != pagina_destino:
            self._retorno_resolver = origem
            self._retorno_label.setText(
                self._ROTULO_RETORNO.get(
                    origem, "A resolver um problema do orçamento — podes voltar quando terminares."
                )
            )
            self._retorno_banner.setVisible(True)
        self.show_page(pagina_destino)
        # Destacar o alvo exato no menu de destino (quando suportado).
        if alvo and pagina_destino == "materias_primas" and hasattr(self, "materias_primas_page"):
            self.materias_primas_page.focar_materia_prima(alvo)

    def _voltar_resolver(self) -> None:
        destino = self._retorno_resolver
        self._retorno_resolver = None
        self._retorno_banner.setVisible(False)
        if destino is not None:
            self.show_page(destino)

    def _esconder_banner_retorno(self) -> None:
        """Esconde o banner quando o utilizador navega manualmente para outro lado."""
        self._retorno_resolver = None
        if getattr(self, "_retorno_banner", None) is not None:
            self._retorno_banner.setVisible(False)

    def show_page(self, name: str) -> None:
        """Show one central workspace page."""
        permission_key = self._PAGE_PERMISSION.get(name)
        if permission_key is not None and not self._permissions.get(permission_key, False):
            return
        if name == "inicio" and hasattr(self, "inicio_page"):
            self.inicio_page.carregar()
        elif name == "orcamentos_dashboard" and hasattr(self, "orcamentos_dashboard_page"):
            self.orcamentos_dashboard_page.carregar()
        elif name == "custeio_auditoria" and hasattr(self, "custeio_auditoria_page"):
            self.custeio_auditoria_page.carregar()
        elif name == "arquivo_v2" and hasattr(self, "arquivo_v2_page"):
            self.arquivo_v2_page.carregar()
        page_index = self._page_indexes[name]
        self.pages.setCurrentIndex(page_index)
        self._destacar_nav(name)

    def _destacar_nav(self, name: str) -> None:
        """Realça o botão da sidebar correspondente à página atual."""
        item = self._nav_items.get(name)
        if item is None:
            grupo = self._NAV_POR_PAGINA.get(name, "configuracoes")
            item = self._nav_items.get(grupo)
        if item is not None:
            self.nav_tree.setCurrentItem(item)

    def _on_nav_item_clicked(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        page_name = item.data(0, Qt.ItemDataRole.UserRole)
        if page_name:
            # Navegação manual pela sidebar cancela o "voltar" pendente.
            self._esconder_banner_retorno()
            self.show_page(page_name)

    def open_orcamento_detail(self, orcamento: OrcamentoResumo) -> None:
        """Open the detail page for a selected budget."""
        detail_page = OrcamentoDetailPage(
            orcamento,
            on_back=lambda: self.show_page("orcamentos"),
            on_open_custeio_auditoria=self._open_custeio_auditoria_contexto,
            on_navegar_menu=self.navegar_para_resolver,
        )
        self._replace_page("orcamento_detail", detail_page)
        self.show_page("orcamento_detail")

    def _open_custeio_auditoria_contexto(self, ocorrencia=None) -> None:
        """Open the global costing audit focused on the supervisor finding."""
        self.show_page("custeio_auditoria")
        self.custeio_auditoria_page.focar_ocorrencia(ocorrencia)

    def _open_custeio_auditoria_item(self, ocorrencia) -> None:
        """Open the budget version referenced by a financial audit finding."""
        try:
            with SessionLocal() as session:
                orcamentos = OrcamentoService(session).list_orcamentos()
        except SQLAlchemyError:
            return
        orcamento = next(
            (item for item in orcamentos
             if item.orcamento_versao_id == ocorrencia.orcamento_versao_id),
            None,
        )
        if orcamento is not None:
            self.open_orcamento_detail(orcamento)
            detail = self._pages_by_name.get("orcamento_detail")
            if isinstance(detail, OrcamentoDetailPage):
                detail.abrir_item_custeio_por_id(
                    ocorrencia.orcamento_item_id,
                    getattr(ocorrencia, "linha_id", None),
                )

    def _replace_page(self, name: str, page: QWidget) -> None:
        """Replace a named page in the central workspace."""
        old_container = self._page_containers.get(name)
        if old_container is not None:
            self.pages.removeWidget(old_container)
            old_container.deleteLater()

        container = self._embrulhar_pagina(page)
        self._pages_by_name[name] = page
        self._page_containers[name] = container
        self.pages.addWidget(container)
        self._rebuild_page_indexes()

    def _rebuild_page_indexes(self) -> None:
        """Rebuild page indexes after adding or removing widgets."""
        self._page_indexes = {
            name: self.pages.indexOf(container)
            for name, container in self._page_containers.items()
        }

    def _create_text_page(self, text: str) -> QWidget:
        """Create a simple placeholder page."""
        page = QFrame()
        page.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        page.setLayout(layout)

        return page
