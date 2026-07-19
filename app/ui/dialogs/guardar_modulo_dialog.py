"""Dialog to save selected costing lines as a reusable module (phase 8U.1).

Named GuardarModuloDialog to avoid clashing with the unrelated legacy
NovoModuloDialog (the per-item modules page).

Phase 8U.1.1 adds a panel listing the already-saved modules (own / global) so
the user can see the naming convention and overwrite (GRAVAR POR CIMA) an
existing module. Two modes:
- MODO NOVO (default): creates a new module (validates duplicate code).
- MODO SUBSTITUIR: pick a module to replace; its header pre-fills the form, the
  code becomes fixed, and the main button becomes "Substituir".
"""

from __future__ import annotations
from app.ui import tema

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    MODULO_AMBITO_LABELS,
    OUTROS,
    get_modulo_categoria_label,
    normalize_modulo_ambito,
    normalize_modulo_categoria,
)
from app.domain.modulo_pesquisa import modulo_corresponde, termo_tokens
from app.ui.helpers.modulo_categoria_opcoes import (
    carregar_arvore_categorias,
    carregar_labels_categorias,
    carregar_opcoes_categorias,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


@dataclass(frozen=True)
class GuardarModuloDialogData:
    """Data collected by the save-as-module dialog.

    ``modulo_id`` is None in MODO NOVO (create) and the selected module's id in
    MODO SUBSTITUIR (overwrite).
    """

    codigo: str
    nome: str
    descricao: str | None
    ambito: str
    categoria: str
    imagem_path: str | None
    subcategoria: str | None = None
    modulo_id: int | None = None


class GuardarModuloDialog(QDialog):
    """Modal dialog to create or overwrite a reusable module from costing lines.

    Validation runs on save via ``on_save`` (returns False to keep the dialog
    open with the data preserved, e.g. duplicate code / missing fields).
    """

    _COLUNAS = ("Código", "Nome", "Categoria", "Âmbito", "Nº linhas")

    _COLUNAS = ("Imagem",) + _COLUNAS
    _TAMANHO_MINIATURA = 54
    _LARGURAS_COLUNAS = (72, 150, 230, 135, 100, 75)
    _ESTILO_SELECAO_TABELA = """
        QTableWidget::item:selected { background-color: #5A3B27; color: white; }
        QTableWidget::item:selected:!active { background-color: #76523A; color: white; }
    """

    def __init__(
        self,
        parent=None,
        *,
        on_save: Callable[[GuardarModuloDialogData], bool] | None = None,
        num_linhas: int = 0,
        modulos_utilizador: Sequence | None = None,
        modulos_globais: Sequence | None = None,
        pasta_imagens_modulos: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save
        # Manageable categories (phase 6): options for pickers + name labels.
        self._opcoes_categorias = carregar_opcoes_categorias()
        self._categoria_labels = carregar_labels_categorias()
        # Subcategories available per top-level category.
        self._arvore_subcategorias = carregar_arvore_categorias()
        self._modulos_utilizador = list(modulos_utilizador or [])
        self._modulos_globais = list(modulos_globais or [])
        self._modulos_por_id = {
            item.modulo.id: item
            for item in (*self._modulos_utilizador, *self._modulos_globais)
        }
        # None = MODO NOVO; an id = MODO SUBSTITUIR.
        self._modulo_id: int | None = None
        self._pasta_imagens_modulos = (pasta_imagens_modulos or "").strip()

        self.setWindowTitle("Guardar como Módulo")
        self.setModal(True)
        self.setMinimumSize(1080, 680)
        self.resize(1280, 780)
        self.setSizeGripEnabled(True)

        info = QLabel(
            f"Vai guardar {num_linhas} linha(s) de topo como um módulo "
            "reutilizável (só a estrutura — sem material/preço)."
        )
        info.setWordWrap(True)

        corpo = QHBoxLayout()
        corpo.addWidget(self._criar_painel_lista(), stretch=5)
        corpo.addWidget(self._criar_painel_formulario(), stretch=2)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Cancelar"
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(corpo)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._recarregar_tabelas()
        self._aplicar_modo_novo()

    # ----- Layout builders -----

    def _criar_painel_lista(self) -> QWidget:
        """Build the left panel: search + category filter + own/global tables."""
        self.pesquisa_input = QLineEdit()
        self.pesquisa_input.setPlaceholderText(
            "Pesquisar (use % para separar palavras)"
        )
        self.pesquisa_input.textChanged.connect(self._recarregar_tabelas)

        self.categoria_filtro = QComboBox()
        self.categoria_filtro.addItem("Todas", None)
        for code, label in self._opcoes_categorias:
            self.categoria_filtro.addItem(label, code)
        self.categoria_filtro.currentIndexChanged.connect(self._recarregar_tabelas)

        filtro_row = QHBoxLayout()
        filtro_row.setContentsMargins(0, 0, 0, 0)
        filtro_row.addWidget(self.pesquisa_input, stretch=1)
        filtro_row.addWidget(QLabel("Categoria"))
        filtro_row.addWidget(self.categoria_filtro)

        self.tabela_utilizador = self._criar_tabela()
        self.tabela_globais = self._criar_tabela()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.tabela_utilizador, "Utilizador")
        self.tabs.addTab(self.tabela_globais, "Global")

        painel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Módulos já gravados (clique para substituir)"))
        layout.addLayout(filtro_row)
        layout.addWidget(self.tabs)
        painel.setLayout(layout)
        return painel

    def _criar_tabela(self) -> QTableWidget:
        tabela = QTableWidget(0, len(self._COLUNAS))
        tabela.setHorizontalHeaderLabels(self._COLUNAS)
        tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.verticalHeader().setVisible(False)
        tabela.verticalHeader().setDefaultSectionSize(self._TAMANHO_MINIATURA + 12)
        tabela.setIconSize(QSize(self._TAMANHO_MINIATURA, self._TAMANHO_MINIATURA))
        header = tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for indice, largura in enumerate(self._LARGURAS_COLUNAS):
            tabela.setColumnWidth(indice, largura)
        ligar_persistencia_larguras(tabela, "dialog_guardar_modulo_lista")
        tabela.setStyleSheet(self._ESTILO_SELECAO_TABELA)
        tabela.cellClicked.connect(self._on_tabela_clicada)
        tabela.cellDoubleClicked.connect(self._on_tabela_clicada)
        return tabela

    def _criar_painel_formulario(self) -> QWidget:
        """Build the right panel: mode header + Novo button + the header form."""
        self.modo_label = QLabel("")
        self.modo_label.setStyleSheet("font-weight: bold;")

        self.novo_button = QPushButton("Novo")
        self.novo_button.setToolTip(
            "Voltar ao modo de criar um módulo novo (limpa a seleção)."
        )
        self.novo_button.clicked.connect(self._aplicar_modo_novo)

        topo_row = QHBoxLayout()
        topo_row.setContentsMargins(0, 0, 0, 0)
        topo_row.addWidget(self.modo_label, stretch=1)
        topo_row.addWidget(self.novo_button)

        self.codigo_input = QLineEdit()
        self.codigo_input.setToolTip("Código único do módulo (ex.: ROUPEIRO_2P).")
        self.nome_input = QLineEdit()

        self.descricao_input = QPlainTextEdit()
        self.descricao_input.setMinimumHeight(50)

        self.ambito_input = QComboBox()
        self.ambito_input.addItem("Utilizador (só meu)", AMBITO_UTILIZADOR)
        self.ambito_input.addItem("Global (todos)", AMBITO_GLOBAL)

        self.categoria_input = QComboBox()
        for code, label in self._opcoes_categorias:
            self.categoria_input.addItem(label, code)
        self._selecionar_categoria(OUTROS)

        self.subcategoria_input = QComboBox()
        self.subcategoria_input.setToolTip(
            "Subcategoria (opcional) dentro da categoria escolhida."
        )
        self._recarregar_subcategorias(self.categoria_input.currentData())
        self.categoria_input.currentIndexChanged.connect(
            lambda _=0: self._recarregar_subcategorias(
                self.categoria_input.currentData()
            )
        )

        self.categorias_info = QLabel(
            "As categorias e subcategorias criam-se e gerem-se na Biblioteca de "
            "Módulos › Gerir Categorias."
        )
        self.categorias_info.setWordWrap(True)
        self.categorias_info.setStyleSheet("color: #6b6b6b; font-style: italic;")

        self.imagem_input = QLineEdit()
        self.imagem_input.setPlaceholderText("(opcional) caminho da imagem")
        self.procurar_button = QPushButton("Procurar...")
        self.procurar_button.clicked.connect(self._procurar_imagem)
        self.ver_imagem_button = QPushButton("Ver imagem")
        self.ver_imagem_button.setToolTip(
            "Abrir uma janela com a imagem atualmente indicada para o mÃ³dulo."
        )
        self.ver_imagem_button.clicked.connect(self._ver_imagem)
        self.imagem_input.textChanged.connect(self._atualizar_botao_ver_imagem)
        imagem_row = QWidget()
        imagem_layout = QHBoxLayout()
        imagem_layout.setContentsMargins(0, 0, 0, 0)
        imagem_layout.addWidget(self.imagem_input, stretch=1)
        imagem_layout.addWidget(self.procurar_button)
        imagem_layout.addWidget(self.ver_imagem_button)
        imagem_row.setLayout(imagem_layout)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Âmbito", self.ambito_input)
        form.addRow("Categoria", self.categoria_input)
        form.addRow("Subcategoria", self.subcategoria_input)
        form.addRow("Imagem", imagem_row)

        painel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(topo_row)
        layout.addLayout(form)
        layout.addWidget(self.categorias_info)
        layout.addStretch(1)
        painel.setLayout(layout)
        self._atualizar_botao_ver_imagem()
        return painel

    # ----- Listing / filtering -----

    def _recarregar_tabelas(self) -> None:
        """Refill both tables applying the category + '%' search filters."""
        self._preencher_tabela(self.tabela_utilizador, self._modulos_utilizador)
        self._preencher_tabela(self.tabela_globais, self._modulos_globais)

    def _preencher_tabela(self, tabela: QTableWidget, itens: Sequence) -> None:
        filtrados = self._filtrar(itens)
        tabela.setRowCount(0)
        for item in filtrados:
            modulo = item.modulo
            row = tabela.rowCount()
            tabela.insertRow(row)
            imagem = QTableWidgetItem()
            pixmap = QPixmap(modulo.imagem_path or "")
            if not pixmap.isNull():
                imagem.setIcon(
                    QIcon(
                        pixmap.scaled(
                            self._TAMANHO_MINIATURA,
                            self._TAMANHO_MINIATURA,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                )
            else:
                imagem.setText("—")
            imagem.setData(Qt.ItemDataRole.UserRole, modulo.id)
            tabela.setItem(row, 0, imagem)

            valores = (
                modulo.codigo or "",
                modulo.nome or "",
                get_modulo_categoria_label(modulo.categoria, self._categoria_labels),
                MODULO_AMBITO_LABELS.get(
                    normalize_modulo_ambito(modulo.ambito), modulo.ambito
                ),
                str(item.num_linhas),
            )
            for col, texto in enumerate(valores, start=1):
                celula = QTableWidgetItem(texto)
                tabela.setItem(row, col, celula)

    def _filtrar(self, itens: Sequence) -> list:
        categoria = self.categoria_filtro.currentData()
        tokens = termo_tokens(self.pesquisa_input.text())
        resultado = []
        for item in itens:
            modulo = item.modulo
            if categoria and normalize_modulo_categoria(modulo.categoria) != categoria:
                continue
            if not modulo_corresponde(modulo, tokens):
                continue
            resultado.append(item)
        return resultado

    def _on_tabela_clicada(self, row: int, _col: int) -> None:
        tabela = self.sender()
        item = tabela.item(row, 0)
        if item is None:
            return
        modulo_id = item.data(Qt.ItemDataRole.UserRole)
        alvo = self._modulos_por_id.get(modulo_id)
        if alvo is not None:
            self._aplicar_modo_substituir(alvo)

    # ----- Modes -----

    def _aplicar_modo_novo(self) -> None:
        """Return to MODO NOVO: clear selection/fields, keep the lines to save."""
        self._modulo_id = None
        self.modo_label.setText("Modo: novo módulo")
        self.novo_button.setEnabled(False)
        self.save_button.setText("Guardar")

        self.codigo_input.setReadOnly(False)
        self.codigo_input.clear()
        self.nome_input.clear()
        self.descricao_input.clear()
        self.imagem_input.clear()
        self.ambito_input.setCurrentIndex(0)
        self._selecionar_categoria(OUTROS)
        self._recarregar_subcategorias(self.categoria_input.currentData())
        self.error_label.clear()

        self.tabela_utilizador.clearSelection()
        self.tabela_globais.clearSelection()

    def _aplicar_modo_substituir(self, item) -> None:
        """Enter MODO SUBSTITUIR: pre-fill the form from the selected module."""
        modulo = item.modulo
        self._modulo_id = modulo.id
        self.modo_label.setText(f"Modo: substituir {modulo.codigo}")
        self.novo_button.setEnabled(True)
        self.save_button.setText("Substituir")

        self.codigo_input.setText(modulo.codigo or "")
        self.codigo_input.setReadOnly(True)
        self.nome_input.setText(modulo.nome or "")
        self.descricao_input.setPlainText(modulo.descricao or "")
        self.imagem_input.setText(modulo.imagem_path or "")
        self._selecionar_ambito(normalize_modulo_ambito(modulo.ambito))
        self._selecionar_categoria(normalize_modulo_categoria(modulo.categoria))
        self._recarregar_subcategorias(
            self.categoria_input.currentData(),
            selecionar=(
                normalize_modulo_categoria(modulo.subcategoria)
                if getattr(modulo, "subcategoria", None)
                else None
            ),
        )
        self.error_label.clear()

    # ----- Helpers -----

    def _procurar_imagem(self) -> None:
        """Pick an image file path (only the path is stored in this phase)."""
        caminho, _filtro = QFileDialog.getOpenFileName(
            self,
            "Escolher imagem do módulo",
            self._pasta_imagens_modulos,
            "Imagens (*.png *.jpg *.jpeg *.bmp *.gif);;Todos os ficheiros (*)",
        )
        if caminho:
            self.imagem_input.setText(caminho)

    def _atualizar_botao_ver_imagem(self) -> None:
        """Enable the preview command only when an image path was provided."""
        self.ver_imagem_button.setEnabled(bool(self.imagem_input.text().strip()))

    def _ver_imagem(self) -> None:
        """Show the selected module image in its own scalable preview window."""
        caminho = self.imagem_input.text().strip()
        pixmap = QPixmap(caminho)
        if not caminho or pixmap.isNull():
            QMessageBox.information(
                self,
                "Imagem do mÃ³dulo",
                "NÃ£o foi possÃ­vel abrir a imagem indicada para este mÃ³dulo.",
            )
            return

        dialogo = QDialog(self)
        dialogo.setWindowTitle("Imagem do MÃ³dulo")
        dialogo.setMinimumSize(640, 480)
        dialogo.resize(900, 650)
        imagem = QLabel()
        imagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        imagem.setPixmap(
            pixmap.scaled(
                QSize(1200, 900),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(imagem)
        fechar = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        fechar.rejected.connect(dialogo.reject)
        fechar.accepted.connect(dialogo.accept)
        layout = QVBoxLayout(dialogo)
        layout.addWidget(area)
        layout.addWidget(fechar)
        dialogo.exec()

    def _selecionar_categoria(self, code: str) -> None:
        index = self.categoria_input.findData(code)
        if index < 0:
            # Archived/legacy category of an existing module: keep it selectable.
            self.categoria_input.addItem(
                get_modulo_categoria_label(code, self._categoria_labels), code
            )
            index = self.categoria_input.findData(code)
        self.categoria_input.setCurrentIndex(index)

    def _recarregar_subcategorias(
        self, categoria_codigo: str | None, selecionar: str | None = None
    ) -> None:
        """Rebuild the subcategory picker for the chosen top-level category."""
        self.subcategoria_input.blockSignals(True)
        self.subcategoria_input.clear()
        self.subcategoria_input.addItem("— Nenhuma —", None)
        for code, label in self._arvore_subcategorias.get(categoria_codigo or "", ()):
            self.subcategoria_input.addItem(label, code)
        indice = self.subcategoria_input.findData(selecionar)
        self.subcategoria_input.setCurrentIndex(indice if indice >= 0 else 0)
        self.subcategoria_input.blockSignals(False)

    def _selecionar_ambito(self, code: str) -> None:
        index = self.ambito_input.findData(code)
        if index >= 0:
            self.ambito_input.setCurrentIndex(index)

    def get_data(self) -> GuardarModuloDialogData:
        """Return the dialog data (modulo_id set only in MODO SUBSTITUIR)."""
        descricao = self.descricao_input.toPlainText().strip()
        imagem = self.imagem_input.text().strip()
        return GuardarModuloDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=descricao or None,
            ambito=self.ambito_input.currentData() or AMBITO_UTILIZADOR,
            categoria=self.categoria_input.currentData() or OUTROS,
            imagem_path=imagem or None,
            subcategoria=self.subcategoria_input.currentData(),
            modulo_id=self._modulo_id,
        )

    def set_error(self, message: str) -> None:
        """Show an error while keeping the dialog open and the data filled."""
        self.error_label.setText(message)

    def _validate_and_accept(self) -> None:
        """Require code/name, confirm overwrite, then delegate to on_save."""
        data = self.get_data()
        if not data.codigo:
            self.error_label.setText("O código é obrigatório.")
            return
        if not data.nome:
            self.error_label.setText("O nome é obrigatório.")
            return

        if data.modulo_id is not None and not self._confirmar_substituicao(data.codigo):
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def _confirmar_substituicao(self, codigo: str) -> bool:
        """Ask the user to confirm overwriting an existing module."""
        resposta = QMessageBox.question(
            self,
            "Substituir módulo",
            f"Substituir o módulo {codigo}?\n\nAs linhas guardadas serão "
            "substituídas pelas linhas selecionadas agora.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return resposta == QMessageBox.StandardButton.Yes
