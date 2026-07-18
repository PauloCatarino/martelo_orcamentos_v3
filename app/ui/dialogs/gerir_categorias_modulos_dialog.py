"""Dialog to manage the module-library categories and subcategories.

Two levels only: top-level categories and their subcategories (a customer name
or a project inside a zone, for example). Create, rename, archive / reactivate
and safe-delete; a category with subcategories or modules cannot be deleted and
OUTROS (the fallback) is protected. The tree shows categoria -> subcategoria.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.def_modulo_categoria_service import (
    DefModuloCategoriaService,
    ModuloCategoriaResumo,
)
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


def _estilo_arvore() -> str:
    """Same visual language as the app tables, applied to a tree."""
    return (
        f"QTreeWidget {{ background: #FFFFFF; alternate-background-color: {tema.BEGE_CLARO};"
        f" border: 1px solid {tema.CINZA_CASTANHO}; border-radius: 6px;"
        " selection-background-color: #D6C2A5; selection-color: #2E2A26;"
        " font-size: 11px; outline: 0; }\n"
        "QTreeWidget::item { padding: 3px 7px; border-bottom: 1px solid #E8E1D7; }\n"
        f"QTreeWidget::item:selected {{ background: #D6C2A5; color: {tema.TEXTO_NORMAL}; }}\n"
        f"QHeaderView::section {{ background: {tema.CASTANHO_MEDIO}; color: #FFFFFF;"
        " padding: 6px 7px; border: none; border-right: 1px solid #A99175;"
        " font-weight: bold; }}\n"
        f"QHeaderView::section:hover {{ background: {tema.CASTANHO_ESCURO}; }}"
    )


class GerirCategoriasModulosDialog(QDialog):
    """Modal dialog to manage the module categories and subcategories."""

    TREE_HEADERS = ["Nome", "Código", "Módulos", "Estado"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.alterado = False
        # (topo, [subcategorias...]) as returned by the service.
        self._arvore: list[tuple[ModuloCategoriaResumo, list[ModuloCategoriaResumo]]] = []

        self.setWindowTitle("Gerir Categorias de Módulos")
        self.setModal(True)
        self.setMinimumSize(560, 460)

        self.nova_input = QLineEdit()
        self.nova_input.setPlaceholderText(
            "Nome da nova categoria ou subcategoria (ex.: Roupeiros, ou o nome de um cliente)"
        )
        self.nova_input.setToolTip("Nome da nova categoria/subcategoria de módulos")
        self.nova_input.returnPressed.connect(self._criar)

        self.pai_combo = QComboBox()
        self.pai_combo.setToolTip(
            "Escolha a categoria-pai para criar uma subcategoria, ou "
            "'— Categoria de topo —' para criar uma categoria principal."
        )

        self.criar_button = QPushButton("Criar")
        self.criar_button.setToolTip("Criar a categoria ou subcategoria")
        self.criar_button.clicked.connect(self._criar)

        nova_layout = QHBoxLayout()
        nova_layout.addWidget(self.nova_input, stretch=1)
        nova_layout.addWidget(QLabel("Dentro de"))
        nova_layout.addWidget(self.pai_combo)
        nova_layout.addWidget(self.criar_button)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(len(self.TREE_HEADERS))
        self.tree.setHeaderLabels(self.TREE_HEADERS)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setRootIsDecorated(True)
        self.tree.setStyleSheet(_estilo_arvore())
        # Resizable columns with per-user persisted widths, like the app tables.
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        for coluna, largura in enumerate((240, 200, 80, 90)):
            self.tree.setColumnWidth(coluna, largura)
        ligar_persistencia_larguras(self.tree, "dialog_gerir_categorias_arvore")
        self.tree.itemSelectionChanged.connect(self._atualizar_botoes)

        self.renomear_button = QPushButton("Renomear")
        self.renomear_button.setToolTip("Renomear a categoria/subcategoria selecionada")
        self.renomear_button.clicked.connect(self._renomear)
        self.arquivar_button = QPushButton("Arquivar")
        self.arquivar_button.setToolTip(
            "Arquivar/reativar: uma categoria arquivada sai das escolhas, "
            "mas os módulos antigos mantêm-na"
        )
        self.arquivar_button.clicked.connect(self._arquivar_ou_reativar)
        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setToolTip(
            "Eliminar (apenas quando não tem subcategorias nem módulos a usá-la)"
        )
        self.eliminar_button.clicked.connect(self._eliminar)

        acoes_layout = QHBoxLayout()
        acoes_layout.addWidget(self.renomear_button)
        acoes_layout.addWidget(self.arquivar_button)
        acoes_layout.addWidget(self.eliminar_button)
        acoes_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar a gestão de categorias")
        self.fechar_button.clicked.connect(self.accept)

        fechar_layout = QHBoxLayout()
        fechar_layout.addStretch()
        fechar_layout.addWidget(self.fechar_button)

        layout = QVBoxLayout()
        layout.addLayout(nova_layout)
        layout.addWidget(self.tree, stretch=1)
        layout.addLayout(acoes_layout)
        layout.addWidget(self.status_label)
        layout.addLayout(fechar_layout)
        self.setLayout(layout)

        self._carregar()

    # ----- data -----

    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                self._arvore = DefModuloCategoriaService(session).listar_arvore()
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as categorias.")
            return
        self._render()

    def _render(self) -> None:
        self.tree.clear()
        self._recarregar_pai_combo()
        for topo, subcategorias in self._arvore:
            item_topo = self._criar_item(topo)
            self.tree.addTopLevelItem(item_topo)
            for sub in subcategorias:
                item_topo.addChild(self._criar_item(sub))
            item_topo.setExpanded(True)
        self._atualizar_botoes()

    def _criar_item(self, categoria: ModuloCategoriaResumo) -> QTreeWidgetItem:
        item = QTreeWidgetItem(
            [
                categoria.nome,
                categoria.codigo,
                str(categoria.modulos_em_uso),
                "Ativa" if categoria.ativo else "Arquivada",
            ]
        )
        item.setData(0, Qt.ItemDataRole.UserRole, categoria)
        return item

    def _recarregar_pai_combo(self) -> None:
        """Rebuild the parent picker with the current top-level categories."""
        selecionado = self.pai_combo.currentData()
        self.pai_combo.blockSignals(True)
        self.pai_combo.clear()
        self.pai_combo.addItem("— Categoria de topo —", None)
        for topo, _subs in self._arvore:
            self.pai_combo.addItem(topo.nome, topo.id)
        indice = self.pai_combo.findData(selecionado)
        self.pai_combo.setCurrentIndex(indice if indice >= 0 else 0)
        self.pai_combo.blockSignals(False)

    def _selecionada(self) -> ModuloCategoriaResumo | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _atualizar_botoes(self) -> None:
        categoria = self._selecionada()
        tem = categoria is not None
        self.renomear_button.setEnabled(tem)
        self.arquivar_button.setEnabled(tem)
        self.eliminar_button.setEnabled(tem)
        if categoria is not None:
            self.arquivar_button.setText(
                "Reativar" if not categoria.ativo else "Arquivar"
            )

    # ----- actions -----

    def _criar(self) -> None:
        nome = self.nova_input.text().strip()
        if not nome:
            self.status_label.setText("Escreva o nome da nova categoria.")
            return
        parent_id = self.pai_combo.currentData()
        try:
            with SessionLocal() as session:
                DefModuloCategoriaService(session).criar(nome, parent_id=parent_id)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar a categoria.")
            return
        self.alterado = True
        self.nova_input.clear()
        destino = "subcategoria" if parent_id is not None else "categoria"
        self.status_label.setText(f"{destino.capitalize()} {nome} criada.")
        self._carregar()

    def _renomear(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        nome, ok = QInputDialog.getText(
            self,
            "Renomear categoria",
            "Novo nome:",
            text=categoria.nome,
        )
        if not ok or not nome.strip():
            return
        try:
            with SessionLocal() as session:
                DefModuloCategoriaService(session).renomear(categoria.id, nome)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível renomear a categoria.")
            return
        self.alterado = True
        self.status_label.setText(f"Renomeada para {nome.strip()}.")
        self._carregar()

    def _arquivar_ou_reativar(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        try:
            with SessionLocal() as session:
                service = DefModuloCategoriaService(session)
                if categoria.ativo:
                    service.arquivar(categoria.id)
                    mensagem = f"Categoria {categoria.nome} arquivada."
                else:
                    service.reativar(categoria.id)
                    mensagem = f"Categoria {categoria.nome} reativada."
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível alterar a categoria.")
            return
        self.alterado = True
        self.status_label.setText(mensagem)
        self._carregar()

    def _eliminar(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        resposta = QMessageBox.question(
            self,
            "Eliminar categoria",
            f"Eliminar {categoria.nome}?\n\n"
            "Só é possível quando não tem subcategorias nem módulos a usá-la.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            with SessionLocal() as session:
                DefModuloCategoriaService(session).eliminar(categoria.id)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível eliminar a categoria.")
            return
        self.alterado = True
        self.status_label.setText(f"{categoria.nome} eliminada.")
        self._carregar()
