"""Module library management page (phase 8U.3).

Manage the reusable modules saved from costings: list (own / global), search
('%'), filter by category, edit the header, delete (module + lines) and view a
module's lines (read-only). Modules are NOT created here — they are saved from
the costing screen.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.modulo_categorias import (
    MODULO_AMBITO_LABELS,
    get_modulo_categoria_label,
    get_modulo_categoria_options,
    normalize_modulo_ambito,
    normalize_modulo_categoria,
)
from app.domain.modulo_imagem import copiar_imagem_para_pasta
from app.domain.modulo_pesquisa import modulo_corresponde, termo_tokens
from app.services.def_modulo_service import (
    DefModuloService,
    EditarDefModuloCabecalhoData,
)
from app.services.system_setting_service import SystemSettingService
from app.ui.dialogs.editar_modulo_dialog import (
    EditarModuloDialog,
    EditarModuloDialogData,
)
from app.ui.dialogs.modulo_linhas_dialog import ModuloLinhasDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estilo_tabela_orcamentos import configurar_tabela_orcamentos
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class BibliotecaModulosPage(QWidget):
    """Settings page to manage the reusable module library."""

    TABLE_HEADERS = [
        "Imagem",
        "Código",
        "Nome",
        "Categoria",
        "Âmbito",
        "Nº linhas",
        "Criado em",
    ]
    _LARGURAS = (60, 150, 220, 110, 90, 70, 130)
    _TAMANHO_MINIATURA = 36

    def __init__(self) -> None:
        super().__init__()

        self._modulos_utilizador: list = []
        self._modulos_globais: list = []
        self._por_linha: dict[QTableWidget, dict[int, object]] = {}

        self.cabecalho = BarraCabecalho(
            "Biblioteca de Módulos",
            [
                "Gestão dos módulos reutilizáveis guardados a partir do custeio "
                "(roupeiros, cozinhas, móveis...). Aqui pode pesquisar, editar o "
                "cabeçalho, eliminar e ver as linhas de cada módulo. Os módulos "
                "criam-se no custeio (botão Guardar como Módulo) e importam-se para "
                "os itens (botão Importar Módulo) — não se criam aqui."
            ],
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("bibliotecaModulosStatus")

        self.pesquisa_input = CampoPesquisa(
            placeholder="Pesquisar (use % para separar palavras)"
        )
        self.pesquisa_input.pesquisa_mudou.connect(self._refill)

        self.categoria_filtro = QComboBox()
        self.categoria_filtro.addItem("Todas", None)
        for code, label in get_modulo_categoria_options():
            self.categoria_filtro.addItem(label, code)
        self.categoria_filtro.currentIndexChanged.connect(self._refill)

        filtro_row = QHBoxLayout()
        filtro_row.addWidget(self.pesquisa_input, stretch=1)
        filtro_row.addWidget(QLabel("Categoria"))
        filtro_row.addWidget(self.categoria_filtro)

        self.tabela_utilizador = self._criar_tabela()
        self.tabela_globais = self._criar_tabela()
        ligar_persistencia_larguras(self.tabela_utilizador, "biblioteca_modulos_utilizador")
        ligar_persistencia_larguras(self.tabela_globais, "biblioteca_modulos_globais")
        self.tabs = QTabWidget()
        self.tabs.addTab(self.tabela_utilizador, "Utilizador")
        self.tabs.addTab(self.tabela_globais, "Global")

        self.editar_button = QPushButton("Editar")
        self.editar_button.clicked.connect(self.editar_modulo)
        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.clicked.connect(self.eliminar_modulo)
        self.ver_linhas_button = QPushButton("Ver linhas")
        self.ver_linhas_button.clicked.connect(self.ver_linhas)
        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.clicked.connect(self.carregar)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.editar_button)
        buttons_layout.addWidget(self.eliminar_button)
        buttons_layout.addWidget(self.ver_linhas_button)
        buttons_layout.addWidget(self.atualizar_button)
        buttons_layout.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(filtro_row)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.tabs, stretch=1)
        layout.addWidget(self.status_label)
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
        """Load the user's own and the global modules into the tables."""
        try:
            with SessionLocal() as session:
                utilizador, globais = DefModuloService(
                    session
                ).listar_modulos_para_dialogo(self._user_id())
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar os módulos.")
            return

        self._modulos_utilizador = utilizador
        self._modulos_globais = globais
        self._refill()

    def _refill(self) -> None:
        self._preencher_tabela(self.tabela_utilizador, self._modulos_utilizador)
        self._preencher_tabela(self.tabela_globais, self._modulos_globais)

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

    # ----- Tables -----

    def _criar_tabela(self) -> QTableWidget:
        tabela = QTableWidget(0, len(self.TABLE_HEADERS))
        tabela.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        tabela.verticalHeader().setVisible(False)
        tabela.setAlternatingRowColors(True)
        tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.setIconSize(QSize(self._TAMANHO_MINIATURA, self._TAMANHO_MINIATURA))
        configurar_tabela_orcamentos(tabela, compacta=True)
        # Preserve the thumbnail size while keeping the remaining rows compact.
        tabela.verticalHeader().setDefaultSectionSize(self._TAMANHO_MINIATURA + 4)
        header = tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        for indice, largura in enumerate(self._LARGURAS):
            tabela.setColumnWidth(indice, largura)
        tabela.cellDoubleClicked.connect(
            lambda *_: self.editar_modulo()
        )
        return tabela

    def _preencher_tabela(self, tabela: QTableWidget, itens: Sequence) -> None:
        filtrados = self._filtrar(itens)
        por_linha: dict[int, object] = {}
        tabela.setRowCount(0)
        for item in filtrados:
            modulo = item.modulo
            row = tabela.rowCount()
            tabela.insertRow(row)
            por_linha[row] = item

            celula_img = QTableWidgetItem()
            pixmap = self._miniatura(modulo.imagem_path)
            if pixmap is not None:
                celula_img.setIcon(QIcon(pixmap))
            else:
                celula_img.setText("—")
            celula_img.setData(Qt.ItemDataRole.UserRole, modulo.id)
            tabela.setItem(row, 0, celula_img)

            valores = (
                modulo.codigo or "",
                modulo.nome or "",
                get_modulo_categoria_label(modulo.categoria),
                MODULO_AMBITO_LABELS.get(
                    normalize_modulo_ambito(modulo.ambito), modulo.ambito
                ),
                str(item.num_linhas),
                self._formatar_data(modulo.created_at),
            )
            for col, texto in enumerate(valores, start=1):
                tabela.setItem(row, col, QTableWidgetItem(texto))

        self._por_linha[tabela] = por_linha

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
        tabela = self.tabs.currentWidget()
        if not isinstance(tabela, QTableWidget):
            return None
        row = tabela.currentRow()
        if row < 0:
            return None
        return self._por_linha.get(tabela, {}).get(row)

    def selecionar_modulo_por_id(self, modulo_id: int) -> None:
        """Reload and select one saved module from the audit page."""
        self.carregar()
        for tab_index in range(self.tabs.count()):
            tabela = self.tabs.widget(tab_index)
            if not isinstance(tabela, QTableWidget):
                continue
            for row, item in self._por_linha.get(tabela, {}).items():
                if item.modulo.id == modulo_id:
                    self.tabs.setCurrentIndex(tab_index)
                    tabela.selectRow(row)
                    tabela.scrollToItem(tabela.item(row, 0))
                    return
        self.status_label.setText("O módulo indicado já não existe.")

    # ----- Actions -----

    def editar_modulo(self) -> None:
        """Edit the selected module's header."""
        item = self._modulo_selecionado()
        if item is None:
            self.status_label.setText("Selecione um módulo para editar.")
            return

        modulo = item.modulo
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
