"""Dialog to import a saved module into the current item's costing (phase 8U.2).

Lists the saved modules (own / global) with a thumbnail, search ('%'), category
filter, and a preview panel (bigger image + name + description + the module's
structural lines). The actual insertion + recompute is done by the page using
``OrcamentoItemCusteioLinhaService.inserir_modulo_no_item``; this dialog only
picks the module (``modulo_id_selecionado`` after accept).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.domain.modulo_categorias import (
    get_modulo_categoria_label,
    normalize_modulo_categoria,
)
from app.domain.modulo_pesquisa import modulo_corresponde, termo_tokens
from app.ui.helpers.modulo_categoria_opcoes import (
    carregar_labels_categorias,
    carregar_opcoes_categorias,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class ImportarModuloDialog(QDialog):
    """Modal dialog to pick a saved module to import into the item costing."""

    _COLUNAS_LISTA = ("Imagem", "Código", "Nome", "Nº linhas")
    _COLUNAS_PREVIEW = (
        "Tipo",
        "Código/Def. peça",
        "Descrição",
        "Prioridade",
        "QT",
        "Comp",
        "Larg",
        "Esp",
    )
    _TAMANHO_MINIATURA = 48
    # Initial column widths (the user can drag the borders afterwards).
    _LARGURAS_LISTA = (64, 150, 240, 80)
    _LARGURAS_PREVIEW = (130, 140, 200, 75, 50, 60, 60, 60)

    def __init__(
        self,
        parent=None,
        *,
        modulos_utilizador: Sequence | None = None,
        modulos_globais: Sequence | None = None,
        obter_linhas: Callable[[int], Sequence] | None = None,
    ) -> None:
        super().__init__(parent)

        self._modulos_utilizador = list(modulos_utilizador or [])
        self._modulos_globais = list(modulos_globais or [])
        self._obter_linhas = obter_linhas
        # Manageable categories (phase 6): options for the filter + labels.
        self._opcoes_categorias = carregar_opcoes_categorias()
        self._categoria_labels = carregar_labels_categorias()
        self._modulo_selecionado = None
        self.modulo_id_selecionado: int | None = None
        self._preview_pixmap_original: QPixmap | None = None

        self.setWindowTitle("Importar Módulo Guardado")
        self.setModal(True)
        self.setMinimumSize(820, 520)
        self.resize(1100, 680)
        self.setSizeGripEnabled(True)

        # Left (modules list) vs right (preview): draggable horizontal split.
        self.split_principal = QSplitter(Qt.Orientation.Horizontal)
        self.split_principal.addWidget(self._criar_painel_lista())
        self.split_principal.addWidget(self._criar_painel_preview())
        self.split_principal.setStretchFactor(0, 3)
        self.split_principal.setStretchFactor(1, 2)
        self.split_principal.setSizes([620, 420])

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.import_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.import_button.setText("Importar Módulo")
        self.import_button.setEnabled(False)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Cancelar"
        )
        self.button_box.accepted.connect(self._accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.split_principal, stretch=1)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._recarregar_tabelas()

    # ----- Layout builders -----

    def _criar_painel_lista(self) -> QWidget:
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

        self.tabela_utilizador = self._criar_tabela_lista()
        self.tabela_globais = self._criar_tabela_lista()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.tabela_utilizador, "Utilizador")
        self.tabs.addTab(self.tabela_globais, "Global")
        self.tabs.currentChanged.connect(self._on_tab_mudou)

        painel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Módulos guardados"))
        layout.addLayout(filtro_row)
        layout.addWidget(self.tabs)
        painel.setLayout(layout)
        return painel

    def _criar_tabela_lista(self) -> QTableWidget:
        tabela = QTableWidget(0, len(self._COLUNAS_LISTA))
        tabela.setHorizontalHeaderLabels(self._COLUNAS_LISTA)
        tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.verticalHeader().setVisible(False)
        tabela.setIconSize(QSize(self._TAMANHO_MINIATURA, self._TAMANHO_MINIATURA))
        self._configurar_colunas(tabela, self._LARGURAS_LISTA)
        tabela.cellClicked.connect(self._on_tabela_clicada)
        tabela.cellDoubleClicked.connect(self._on_tabela_duplo_clique)
        ligar_persistencia_larguras(tabela, "dialog_importar_modulo_lista")
        return tabela

    @staticmethod
    def _configurar_colunas(tabela: QTableWidget, larguras) -> None:
        """Make every column drag-resizable (Interactive) with initial widths."""
        header = tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Last section must NOT stretch, otherwise its border cannot be dragged.
        header.setStretchLastSection(False)
        for indice, largura in enumerate(larguras):
            tabela.setColumnWidth(indice, largura)

    def _criar_painel_preview(self) -> QWidget:
        # Top sub-panel: image + name + description.
        self.preview_imagem = QLabel("Sem imagem")
        self.preview_imagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_imagem.setMinimumHeight(120)
        self.preview_imagem.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.preview_imagem.setStyleSheet(
            "QLabel { border: 1px solid #c0c0c0; background: #f5f5f5; }"
        )

        self.preview_nome = QLabel("")
        self.preview_nome.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.preview_nome.setWordWrap(True)

        self.preview_descricao = QPlainTextEdit()
        self.preview_descricao.setReadOnly(True)
        self.preview_descricao.setMaximumHeight(70)

        form = QFormLayout()
        form.addRow("Nome", self.preview_nome)
        form.addRow("Descrição", self.preview_descricao)

        topo = QWidget()
        topo_layout = QVBoxLayout()
        topo_layout.setContentsMargins(0, 0, 0, 0)
        topo_layout.addWidget(QLabel("Pré-visualização"))
        topo_layout.addWidget(self.preview_imagem, stretch=1)
        topo_layout.addLayout(form)
        topo.setLayout(topo_layout)

        # Bottom sub-panel: the module's structural lines.
        self.preview_linhas = QTableWidget(0, len(self._COLUNAS_PREVIEW))
        self.preview_linhas.setHorizontalHeaderLabels(self._COLUNAS_PREVIEW)
        self.preview_linhas.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.preview_linhas.verticalHeader().setVisible(False)
        self._configurar_colunas(self.preview_linhas, self._LARGURAS_PREVIEW)
        ligar_persistencia_larguras(
            self.preview_linhas, "dialog_importar_modulo_preview"
        )

        baixo = QWidget()
        baixo_layout = QVBoxLayout()
        baixo_layout.setContentsMargins(0, 0, 0, 0)
        baixo_layout.addWidget(QLabel("Linhas do módulo"))
        baixo_layout.addWidget(self.preview_linhas, stretch=1)
        baixo.setLayout(baixo_layout)

        # Draggable vertical split: image area (top) vs lines table (bottom).
        self.split_preview = QSplitter(Qt.Orientation.Vertical)
        self.split_preview.addWidget(topo)
        self.split_preview.addWidget(baixo)
        self.split_preview.setStretchFactor(0, 3)
        self.split_preview.setStretchFactor(1, 2)
        self.split_preview.setSizes([360, 240])
        self.split_preview.splitterMoved.connect(
            lambda *_: self._ajustar_imagem_preview()
        )

        painel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.split_preview)
        painel.setLayout(layout)
        return painel

    # ----- Listing / filtering -----

    def _recarregar_tabelas(self) -> None:
        self._preencher_tabela(self.tabela_utilizador, self._modulos_utilizador)
        self._preencher_tabela(self.tabela_globais, self._modulos_globais)

    def _preencher_tabela(self, tabela: QTableWidget, itens: Sequence) -> None:
        filtrados = self._filtrar(itens)
        tabela.setRowCount(0)
        for item in filtrados:
            modulo = item.modulo
            row = tabela.rowCount()
            tabela.insertRow(row)

            celula_img = QTableWidgetItem()
            pixmap = self._pixmap(modulo.imagem_path, self._TAMANHO_MINIATURA)
            if pixmap is not None:
                celula_img.setIcon(QIcon(pixmap))
            else:
                celula_img.setText("—")
            celula_img.setData(Qt.ItemDataRole.UserRole, modulo.id)
            tabela.setItem(row, 0, celula_img)

            tabela.setItem(row, 1, QTableWidgetItem(modulo.codigo or ""))
            tabela.setItem(row, 2, QTableWidgetItem(modulo.nome or ""))
            tabela.setItem(row, 3, QTableWidgetItem(str(item.num_linhas)))

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

    # ----- Selection / preview -----

    def _on_tab_mudou(self, _index: int) -> None:
        """Switching tabs clears the current selection/preview."""
        self.tabela_utilizador.clearSelection()
        self.tabela_globais.clearSelection()
        self._selecionar_modulo(None)

    def _on_tabela_clicada(self, row: int, _col: int) -> None:
        tabela = self.sender()
        item = tabela.item(row, 0)
        if item is None:
            return
        modulo_id = item.data(Qt.ItemDataRole.UserRole)
        self._selecionar_modulo(self._por_id(modulo_id))

    def _on_tabela_duplo_clique(self, row: int, col: int) -> None:
        self._on_tabela_clicada(row, col)
        if self._modulo_selecionado is not None:
            self._accept()

    def _por_id(self, modulo_id):
        for item in (*self._modulos_utilizador, *self._modulos_globais):
            if item.modulo.id == modulo_id:
                return item
        return None

    def _selecionar_modulo(self, item) -> None:
        self._modulo_selecionado = item
        self.import_button.setEnabled(item is not None)
        self._atualizar_preview(item)

    def _atualizar_preview(self, item) -> None:
        if item is None:
            self._preview_pixmap_original = None
            self._ajustar_imagem_preview()
            self.preview_nome.setText("")
            self.preview_descricao.setPlainText("")
            self.preview_linhas.setRowCount(0)
            return

        modulo = item.modulo
        # Keep the ORIGINAL pixmap so it can rescale as the panes/window resize.
        self._preview_pixmap_original = self._carregar_pixmap(modulo.imagem_path)
        self._ajustar_imagem_preview()

        nome = modulo.nome or modulo.codigo or ""
        categoria = get_modulo_categoria_label(
            modulo.categoria, self._categoria_labels
        )
        self.preview_nome.setText(f"{modulo.codigo} — {nome}  ({categoria})")
        self.preview_descricao.setPlainText(modulo.descricao or "")

        self._preencher_preview_linhas(modulo.id)

    def _ajustar_imagem_preview(self) -> None:
        """Scale the preview image to the current label size (aspect kept)."""
        # resizeEvent may fire before the preview widgets are built.
        if not hasattr(self, "preview_imagem"):
            return

        original = self._preview_pixmap_original
        if original is None or original.isNull():
            self.preview_imagem.setPixmap(QPixmap())
            self.preview_imagem.setText("Sem imagem")
            return

        alvo = self.preview_imagem.size()
        largura = max(alvo.width() - 4, self._TAMANHO_MINIATURA)
        altura = max(alvo.height() - 4, self._TAMANHO_MINIATURA)
        self.preview_imagem.setText("")
        self.preview_imagem.setPixmap(
            original.scaled(
                largura,
                altura,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._ajustar_imagem_preview()

    def _preencher_preview_linhas(self, modulo_id: int) -> None:
        self.preview_linhas.setRowCount(0)
        if self._obter_linhas is None:
            return
        linhas = self._obter_linhas(modulo_id) or []
        for linha in linhas:
            row = self.preview_linhas.rowCount()
            self.preview_linhas.insertRow(row)
            qt = linha.qt_und or linha.qt_mod or ""
            valores = (
                linha.tipo_linha or "",
                linha.def_peca_codigo or linha.codigo or "",
                linha.descricao or linha.descricao_livre or "",
                str(linha.prioridade_valueset or ""),
                str(qt),
                linha.comp or "",
                linha.larg or "",
                linha.esp or "",
            )
            for col, texto in enumerate(valores):
                self.preview_linhas.setItem(row, col, QTableWidgetItem(texto))

    # ----- Helpers -----

    def _pixmap(self, caminho: str | None, tamanho: int) -> QPixmap | None:
        """Load and scale an image, or None when missing/unreadable."""
        if not caminho:
            return None
        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            return None
        return pixmap.scaled(
            tamanho,
            tamanho,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    @staticmethod
    def _carregar_pixmap(caminho: str | None) -> QPixmap | None:
        """Load the original (unscaled) image, or None when missing/unreadable."""
        if not caminho:
            return None
        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            return None
        return pixmap

    def _accept(self) -> None:
        if self._modulo_selecionado is None:
            return
        self.modulo_id_selecionado = self._modulo_selecionado.modulo.id
        self.accept()
