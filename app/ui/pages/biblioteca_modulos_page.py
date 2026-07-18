"""Module library management page (phase 8U.3).

Manage the reusable modules saved from costings, shown as a tree grouped by
Categoria -> Subcategoria -> Módulo (own / global tabs). Search ('%'), filter by
category, edit the header, delete (module + lines) and view a module's lines.
Modules are NOT created here — they are saved from the costing screen.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    MODULO_AMBITO_LABELS,
    get_modulo_categoria_label,
    get_modulo_categoria_options,
    normalize_modulo_ambito,
    normalize_modulo_categoria,
    pode_gerir_modulo,
)
from app.domain.modulo_imagem import copiar_imagem_para_pasta
from app.domain.modulo_pesquisa import modulo_corresponde, termo_tokens
from app.services.def_modulo_categoria_service import DefModuloCategoriaService
from app.services.def_modulo_service import (
    DefModuloService,
    EditarDefModuloCabecalhoData,
)
from app.services.permission_service import is_admin
from app.services.system_setting_service import SystemSettingService
from app.ui.dialogs.editar_modulo_dialog import (
    EditarModuloDialog,
    EditarModuloDialogData,
)
from app.ui.dialogs.gerir_categorias_modulos_dialog import (
    GerirCategoriasModulosDialog,
)
from app.ui.dialogs.modulo_linhas_dialog import ModuloLinhasDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estilo_tabela_orcamentos import estilo_arvore
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class BibliotecaModulosPage(QWidget):
    """Settings page to manage the reusable module library."""

    # Kept for reference / backwards compatibility; the page now renders a tree.
    TABLE_HEADERS = [
        "Imagem",
        "Código",
        "Nome",
        "Categoria",
        "Âmbito",
        "Nº linhas",
        "Criado em",
    ]
    TREE_HEADERS = ["Categoria / Código", "Nome", "Âmbito", "Nº linhas", "Criado em"]
    _LARGURAS = (300, 240, 90, 70, 130)
    _TAMANHO_MINIATURA = 36

    def __init__(self, on_back=None) -> None:
        super().__init__()

        self.on_back = on_back
        self._modulos_utilizador: list = []
        self._modulos_globais: list = []
        # {codigo: nome} of the manageable categories (incl. subcategories).
        self._categoria_labels: dict[str, str] = {}

        self.cabecalho = BarraCabecalho(
            "Biblioteca de Módulos",
            [
                "Gestão dos módulos reutilizáveis guardados a partir do custeio "
                "(roupeiros, cozinhas, móveis...), organizados por categoria e "
                "subcategoria. Aqui pode pesquisar, editar o cabeçalho, eliminar "
                "e ver as linhas de cada módulo. Os módulos criam-se no custeio "
                "(botão Guardar como Módulo) e importam-se para os itens (botão "
                "Importar Módulo) — não se criam aqui."
            ],
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("bibliotecaModulosStatus")

        self.pesquisa_input = CampoPesquisa(
            placeholder="Pesquisar (use % para separar palavras)"
        )
        self.pesquisa_input.pesquisa_mudou.connect(self._refill)

        self.categoria_filtro = QComboBox()
        self.categoria_filtro.setToolTip("Filtrar os módulos por categoria")
        self.categoria_filtro.addItem("Todas", None)
        for code, label in get_modulo_categoria_options():
            self.categoria_filtro.addItem(label, code)
        self.categoria_filtro.currentIndexChanged.connect(self._refill)

        self.gerir_categorias_button = QPushButton("Gerir Categorias…")
        self.gerir_categorias_button.setToolTip(
            "Criar, renomear, arquivar e eliminar categorias e subcategorias de "
            "módulos (pode usar o nome de um cliente)"
        )
        self.gerir_categorias_button.clicked.connect(self.gerir_categorias)

        filtro_row = QHBoxLayout()
        filtro_row.addWidget(self.pesquisa_input, stretch=1)
        filtro_row.addWidget(QLabel("Categoria"))
        filtro_row.addWidget(self.categoria_filtro)
        filtro_row.addWidget(self.gerir_categorias_button)

        self.arvore_utilizador = self._criar_arvore("biblioteca_modulos_utilizador")
        self.arvore_globais = self._criar_arvore("biblioteca_modulos_globais")
        self.tabs = QTabWidget()
        self.tabs.addTab(self.arvore_utilizador, "Utilizador")
        self.tabs.addTab(self.arvore_globais, "Global")

        self.editar_button = QPushButton("Editar")
        self.editar_button.setToolTip("Editar o cabeçalho do módulo selecionado")
        self.editar_button.clicked.connect(self.editar_modulo)
        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setToolTip("Eliminar o módulo selecionado")
        self.eliminar_button.clicked.connect(self.eliminar_modulo)
        self.converter_button = QPushButton("Converter Âmbito")
        self.converter_button.setToolTip(
            "Converter o módulo entre Utilizador e Global (reversível; "
            "módulos globais são geridos pelo administrador)"
        )
        self.converter_button.clicked.connect(self.converter_ambito)
        self.ver_linhas_button = QPushButton("Ver linhas")
        self.ver_linhas_button.setToolTip("Ver as linhas do módulo (só leitura)")
        self.ver_linhas_button.clicked.connect(self.ver_linhas)
        self.expandir_button = QPushButton("Expandir tudo")
        self.expandir_button.setToolTip("Expandir todas as categorias")
        self.expandir_button.clicked.connect(lambda: self._expandir(True))
        self.colapsar_button = QPushButton("Colapsar tudo")
        self.colapsar_button.setToolTip("Colapsar todas as categorias")
        self.colapsar_button.clicked.connect(lambda: self._expandir(False))
        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip("Recarregar a biblioteca")
        self.atualizar_button.clicked.connect(self.carregar)
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.editar_button)
        buttons_layout.addWidget(self.eliminar_button)
        buttons_layout.addWidget(self.converter_button)
        buttons_layout.addWidget(self.ver_linhas_button)
        buttons_layout.addWidget(self.expandir_button)
        buttons_layout.addWidget(self.colapsar_button)
        buttons_layout.addWidget(self.atualizar_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.voltar_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(filtro_row)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs, stretch=1)
        self.setLayout(layout)

        self.carregar()

    # ----- Data -----

    @staticmethod
    def _user_id() -> int | None:
        utilizador = app_session.current_user
        return utilizador.id if utilizador is not None else None

    def _copiar_imagem_modulo(
        self, origem: str | None, codigo: str
    ) -> tuple[str | None, str | None]:
        """Copy the chosen image into the configured module-images folder.

        Returns (caminho_final, aviso); keeps the original path on any problem.
        """
        if not origem:
            return None, None
        try:
            with SessionLocal() as session:
                pasta = SystemSettingService(session).obter_valor(
                    "pasta_imagens_modulos"
                )
        except SQLAlchemyError:
            pasta = None
        resultado = copiar_imagem_para_pasta(origem, pasta, codigo)
        return resultado.caminho, resultado.aviso

    def carregar(self) -> None:
        """Load the modules and the manageable categories into the page."""
        try:
            with SessionLocal() as session:
                utilizador, globais = DefModuloService(
                    session
                ).listar_modulos_para_dialogo(self._user_id())
                categorias_service = DefModuloCategoriaService(session)
                opcoes = categorias_service.listar_opcoes()
                self._categoria_labels = categorias_service.labels()
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar os módulos.")
            return

        self._modulos_utilizador = utilizador
        self._modulos_globais = globais
        self._recarregar_filtro_categorias(opcoes)
        self._refill()

    def _recarregar_filtro_categorias(self, opcoes) -> None:
        """Rebuild the category filter with the manageable top-level categories."""
        selecionada = self.categoria_filtro.currentData()
        self.categoria_filtro.blockSignals(True)
        self.categoria_filtro.clear()
        self.categoria_filtro.addItem("Todas", None)
        for code, label in opcoes:
            self.categoria_filtro.addItem(label, code)
        indice = self.categoria_filtro.findData(selecionada)
        self.categoria_filtro.setCurrentIndex(indice if indice >= 0 else 0)
        self.categoria_filtro.blockSignals(False)

    def _refill(self) -> None:
        self._preencher_arvore(self.arvore_utilizador, self._modulos_utilizador)
        self._preencher_arvore(self.arvore_globais, self._modulos_globais)

        total = len(self._modulos_utilizador) + len(self._modulos_globais)
        if total == 0:
            self.status_label.setText("Sem módulos guardados.")
        else:
            self.status_label.setText(f"{total} módulo(s) na biblioteca.")

    def _filtrar(self, itens: Sequence) -> list:
        categoria = self.categoria_filtro.currentData()
        tokens = termo_tokens(self.pesquisa_input.texto())
        resultado = []
        for item in itens:
            modulo = item.modulo
            if categoria and normalize_modulo_categoria(modulo.categoria) != categoria:
                continue
            if not modulo_corresponde(modulo, tokens):
                continue
            resultado.append(item)
        return resultado

    # ----- Tree -----

    def _criar_arvore(self, chave_larguras: str) -> QTreeWidget:
        arvore = QTreeWidget()
        arvore.setColumnCount(len(self.TREE_HEADERS))
        arvore.setHeaderLabels(self.TREE_HEADERS)
        arvore.setAlternatingRowColors(True)
        arvore.setRootIsDecorated(True)
        arvore.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        arvore.setUniformRowHeights(False)
        arvore.setIconSize(QSize(self._TAMANHO_MINIATURA, self._TAMANHO_MINIATURA))
        arvore.setStyleSheet(estilo_arvore())
        header = arvore.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        for indice, largura in enumerate(self._LARGURAS):
            arvore.setColumnWidth(indice, largura)
        ligar_persistencia_larguras(arvore, chave_larguras)
        arvore.itemDoubleClicked.connect(self._on_duplo_clique)
        return arvore

    def _label(self, codigo: str | None) -> str:
        return get_modulo_categoria_label(codigo, self._categoria_labels)

    def _preencher_arvore(self, arvore: QTreeWidget, itens: Sequence) -> None:
        filtrados = self._filtrar(itens)
        arvore.clear()

        # Group modules by top-level category, then optional subcategory.
        grupos: dict[str, dict] = {}
        for item in filtrados:
            modulo = item.modulo
            cat = normalize_modulo_categoria(modulo.categoria)
            grupo = grupos.setdefault(cat, {"diretos": [], "subs": {}})
            if modulo.subcategoria:
                sub = normalize_modulo_categoria(modulo.subcategoria)
                grupo["subs"].setdefault(sub, []).append(item)
            else:
                grupo["diretos"].append(item)

        for cat in sorted(grupos, key=lambda c: self._label(c).lower()):
            grupo = grupos[cat]
            total = len(grupo["diretos"]) + sum(
                len(v) for v in grupo["subs"].values()
            )
            no_categoria = self._criar_no_grupo(f"{self._label(cat)}  ({total})")
            arvore.addTopLevelItem(no_categoria)
            for item in grupo["diretos"]:
                no_categoria.addChild(self._criar_no_modulo(item))
            for sub in sorted(grupo["subs"], key=lambda c: self._label(c).lower()):
                sub_itens = grupo["subs"][sub]
                no_sub = self._criar_no_grupo(
                    f"{self._label(sub)}  ({len(sub_itens)})"
                )
                no_categoria.addChild(no_sub)
                for item in sub_itens:
                    no_sub.addChild(self._criar_no_modulo(item))
            no_categoria.setExpanded(True)

    def _criar_no_grupo(self, texto: str) -> QTreeWidgetItem:
        no = QTreeWidgetItem([texto, "", "", "", ""])
        fonte = QFont(no.font(0))
        fonte.setBold(True)
        no.setFont(0, fonte)
        # Group nodes are not selectable module rows.
        no.setData(0, Qt.ItemDataRole.UserRole, None)
        return no

    def _criar_no_modulo(self, item) -> QTreeWidgetItem:
        modulo = item.modulo
        no = QTreeWidgetItem(
            [
                modulo.codigo or "",
                modulo.nome or "",
                MODULO_AMBITO_LABELS.get(
                    normalize_modulo_ambito(modulo.ambito), modulo.ambito
                ),
                str(item.num_linhas),
                self._formatar_data(modulo.created_at),
            ]
        )
        pixmap = self._miniatura(modulo.imagem_path)
        if pixmap is not None:
            no.setIcon(0, QIcon(pixmap))
        no.setData(0, Qt.ItemDataRole.UserRole, item)
        return no

    def _expandir(self, expandir: bool) -> None:
        arvore = self.tabs.currentWidget()
        if isinstance(arvore, QTreeWidget):
            if expandir:
                arvore.expandAll()
            else:
                arvore.collapseAll()

    def _on_duplo_clique(self, item, _column) -> None:
        if item is not None and item.data(0, Qt.ItemDataRole.UserRole) is not None:
            self.editar_modulo()

    @staticmethod
    def _formatar_data(valor) -> str:
        if valor is None:
            return ""
        try:
            return valor.strftime("%Y-%m-%d %H:%M")
        except (AttributeError, ValueError):
            return str(valor)

    def _miniatura(self, caminho: str | None) -> QPixmap | None:
        if not caminho:
            return None
        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            return None
        return pixmap.scaled(
            self._TAMANHO_MINIATURA,
            self._TAMANHO_MINIATURA,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _modulo_selecionado(self):
        """Return the selected ModuloComContagem of the active tab, or None."""
        arvore = self.tabs.currentWidget()
        if not isinstance(arvore, QTreeWidget):
            return None
        item = arvore.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def selecionar_modulo_por_id(self, modulo_id: int) -> None:
        """Reload and select one saved module from the audit page."""
        self.carregar()
        for tab_index in range(self.tabs.count()):
            arvore = self.tabs.widget(tab_index)
            if not isinstance(arvore, QTreeWidget):
                continue
            iterador = QTreeWidgetItemIterator(arvore)
            while iterador.value():
                no = iterador.value()
                item = no.data(0, Qt.ItemDataRole.UserRole)
                if item is not None and item.modulo.id == modulo_id:
                    self.tabs.setCurrentIndex(tab_index)
                    arvore.setCurrentItem(no)
                    arvore.scrollToItem(no)
                    return
                iterador += 1
        self.status_label.setText("O módulo indicado já não existe.")

    # ----- Actions -----

    def _pode_gerir(self, modulo) -> bool:
        """Phase 6 permission gate for edit/delete/convert on one module."""
        utilizador = app_session.current_user
        return pode_gerir_modulo(
            modulo.ambito,
            modulo.user_id,
            user_id=utilizador.id if utilizador is not None else None,
            is_admin=is_admin(utilizador),
        )

    def _avisar_sem_permissao(self) -> None:
        QMessageBox.information(
            self,
            "Biblioteca de Módulos",
            "Sem permissão para gerir este módulo.\n\n"
            "Módulos globais são geridos pelo administrador; módulos de "
            "utilizador apenas pelo próprio (ou pelo administrador).",
        )

    def gerir_categorias(self) -> None:
        """Open the category management dialog (phase 6)."""
        dialog = GerirCategoriasModulosDialog(self)
        dialog.exec()
        if dialog.alterado:
            self.carregar()

    def converter_ambito(self) -> None:
        """Convert the selected module between Utilizador and Global."""
        item = self._modulo_selecionado()
        if item is None:
            self.status_label.setText("Selecione um módulo para converter.")
            return

        modulo = item.modulo
        if not self._pode_gerir(modulo):
            self._avisar_sem_permissao()
            return

        atual = normalize_modulo_ambito(modulo.ambito)
        novo = AMBITO_UTILIZADOR if atual == AMBITO_GLOBAL else AMBITO_GLOBAL
        rotulo_novo = MODULO_AMBITO_LABELS[novo]
        resposta = QMessageBox.question(
            self,
            "Converter Âmbito",
            f"Converter o módulo {modulo.codigo} de "
            f"{MODULO_AMBITO_LABELS[atual]} para {rotulo_novo}?\n\n"
            "A conversão é reversível.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        utilizador = app_session.current_user
        try:
            with SessionLocal() as session:
                DefModuloService(session).converter_ambito(
                    modulo.id,
                    novo,
                    acting_user_id=(
                        utilizador.id if utilizador is not None else None
                    ),
                    is_admin=is_admin(utilizador),
                )
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível converter o módulo.")
            return

        self.carregar()
        self.status_label.setText(
            f"Módulo {modulo.codigo} convertido para {rotulo_novo}."
        )

    def editar_modulo(self) -> None:
        """Edit the selected module's header."""
        item = self._modulo_selecionado()
        if item is None:
            self.status_label.setText("Selecione um módulo para editar.")
            return

        modulo = item.modulo
        if not self._pode_gerir(modulo):
            self._avisar_sem_permissao()
            return
        guardado: dict = {}

        def handle_save(dados: EditarModuloDialogData) -> bool:
            imagem_path, aviso_imagem = self._copiar_imagem_modulo(
                dados.imagem_path, modulo.codigo
            )
            try:
                with SessionLocal() as session:
                    DefModuloService(session).editar_cabecalho(
                        modulo.id,
                        EditarDefModuloCabecalhoData(
                            nome=dados.nome,
                            descricao=dados.descricao,
                            ambito=dados.ambito,
                            user_id=modulo.user_id or self._user_id(),
                            categoria=dados.categoria,
                            subcategoria=dados.subcategoria,
                            imagem_path=imagem_path,
                        ),
                    )
            except ValueError as error:
                dialog.set_error(str(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar as alterações.")
                return False
            guardado["aviso_imagem"] = aviso_imagem
            return True

        dialog = EditarModuloDialog(
            self,
            codigo=modulo.codigo,
            dados=EditarModuloDialogData(
                nome=modulo.nome,
                descricao=modulo.descricao,
                ambito=modulo.ambito,
                categoria=modulo.categoria,
                imagem_path=modulo.imagem_path,
                subcategoria=modulo.subcategoria,
            ),
            on_save=handle_save,
        )
        if dialog.exec():
            self.carregar()
            mensagem = f"Módulo {modulo.codigo} atualizado."
            if guardado.get("aviso_imagem"):
                mensagem += " " + guardado["aviso_imagem"]
            self.status_label.setText(mensagem)

    def eliminar_modulo(self) -> None:
        """Delete the selected module and its lines (cascade), after confirming."""
        item = self._modulo_selecionado()
        if item is None:
            self.status_label.setText("Selecione um módulo para eliminar.")
            return

        modulo = item.modulo
        if not self._pode_gerir(modulo):
            self._avisar_sem_permissao()
            return
        resposta = QMessageBox.question(
            self,
            "Eliminar módulo",
            f"Eliminar o módulo {modulo.codigo}?\n\nEsta ação é definitiva e "
            "não afeta os orçamentos onde já foi importado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                DefModuloService(session).eliminar(modulo.id)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível eliminar o módulo.")
            return

        self.carregar()
        self.status_label.setText(f"Módulo {modulo.codigo} eliminado.")

    def ver_linhas(self) -> None:
        """Show the selected module's structural lines (read-only)."""
        item = self._modulo_selecionado()
        if item is None:
            self.status_label.setText("Selecione um módulo para ver as linhas.")
            return

        modulo = item.modulo
        try:
            with SessionLocal() as session:
                com_linhas = DefModuloService(session).obter_com_linhas(modulo.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as linhas.")
            return

        if com_linhas is None:
            self.status_label.setText("Módulo não encontrado.")
            return

        dialog = ModuloLinhasDialog(
            self, modulo=com_linhas.modulo, linhas=com_linhas.linhas
        )
        dialog.exec()
