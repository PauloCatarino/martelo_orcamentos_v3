"""Budget item costing page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.custeio_linha_types import get_custeio_linha_type_label
from app.domain.item_types import get_item_type_label
from app.domain.peca_types import COMPOSTA
from app.repositories.def_peca_repository import DefPecaResumo
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.def_peca_service import DefPecaService
from app.services.orcamento_item_service import OrcamentoItemService
from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage
from app.ui.widgets.breadcrumb import Breadcrumb
from app.utils.formatters import format_currency, format_mm, format_quantity


class OrcamentoItemCusteioPage(QWidget):
    """Page for the costing workspace of one budget item."""

    TABLE_HEADERS = [
        "Tipo",
        "C\u00f3digo",
        "Descri\u00e7\u00e3o",
        "Unidade",
        "Quantidade",
        "Comp",
        "Larg",
        "Esp",
        "Custo total",
        "Pre\u00e7o total",
        "Editado localmente",
        "Ativo",
    ]

    def __init__(
        self,
        item: OrcamentoItemResumo,
        orcamento_codigo: str | None = None,
        orcamento_versao_id: int | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.item_id = item.id
        self.item = item
        self.orcamento_codigo = orcamento_codigo
        self.orcamento_versao_id = orcamento_versao_id
        self.on_back = on_back
        self._item_info_labels: dict[str, QLabel] = {}
        self._biblioteca_pecas: list[DefPecaResumo] = []
        self._selecionados: set[int] = set()

        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())
        self.title_label = QLabel(self._build_title())
        self.title_label.setObjectName("orcamentoItemCusteioTitle")

        self.back_button = QPushButton("Voltar aos Items")
        self.back_button.clicked.connect(self._handle_back)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        self.import_module_button = QPushButton("Importar M\u00f3dulo")
        self.import_module_button.setEnabled(False)

        self.insert_piece_button = QPushButton("Inserir Pe\u00e7a")
        self.insert_piece_button.setEnabled(False)

        self.insert_operation_button = QPushButton("Inserir Opera\u00e7\u00e3o")
        self.insert_operation_button.setEnabled(False)

        self.save_button = QPushButton("Guardar Custeio")
        self.save_button.setEnabled(False)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.back_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(self.import_module_button)
        actions_layout.addWidget(self.insert_piece_button)
        actions_layout.addWidget(self.insert_operation_button)
        actions_layout.addWidget(self.save_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemCusteioStatus")

        item_info_widget = self._create_item_info_widget()

        self.library_panel = self._create_library_panel()

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        lines_layout = QVBoxLayout()
        lines_title = QLabel("Linhas de custeio do item")
        lines_title.setObjectName("orcamentoItemCusteioLinesTitle")
        lines_layout.addWidget(lines_title)
        lines_layout.addWidget(self.table, stretch=1)

        center_widget = QWidget()
        center_widget.setLayout(lines_layout)

        workspace_layout = QHBoxLayout()
        workspace_layout.addWidget(self.library_panel)
        workspace_layout.addWidget(center_widget, stretch=1)

        custeio_tab = QWidget()
        custeio_tab.setLayout(workspace_layout)

        self.tabs = QTabWidget()
        self.tabs.addTab(custeio_tab, "Custeio")
        self.tabs.addTab(OrcamentoItemValuesetPage(item.id), "ValueSet")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.breadcrumb)
        layout.addWidget(self.title_label)
        layout.addLayout(actions_layout)
        layout.addWidget(item_info_widget)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs, stretch=1)

        self.setLayout(layout)
        self._update_item_info()
        self.carregar()

    def carregar(self) -> None:
        """Reload the item data, its costing lines and the parts library."""
        self.status_label.clear()
        self._carregar_biblioteca()

        try:
            with SessionLocal() as session:
                item = OrcamentoItemService(session).get_item_by_id(self.item_id)
                if item is None:
                    self.status_label.setText("Item selecionado nao foi encontrado.")
                    self.table.setRowCount(0)
                    return

                linhas = OrcamentoItemCusteioLinhaService(session).listar_linhas_do_item(
                    self.item_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar o custeio do item.")
            return

        self.item = item
        self._update_item_info()
        self._preencher_tabela(linhas)

        if not linhas:
            self.status_label.setText("Sem linhas de custeio para este item.")

    def _create_library_panel(self) -> QWidget:
        """Build the parts library panel (search + tree + selection tools)."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Biblioteca de peças")
        title.setObjectName("orcamentoItemCusteioLibraryTitle")

        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Pesquisar peça...")
        self.library_search.textChanged.connect(self._aplicar_filtro_biblioteca)

        self.tree_biblioteca_pecas = QTreeWidget()
        self.tree_biblioteca_pecas.setHeaderLabel("Peças")
        self.tree_biblioteca_pecas.setAlternatingRowColors(True)
        self.tree_biblioteca_pecas.itemChanged.connect(self._on_biblioteca_item_changed)

        self.so_selecionados_check = QCheckBox("Só selecionados")
        self.so_selecionados_check.stateChanged.connect(self._aplicar_filtro_biblioteca)

        self.selecionados_label = QLabel("Selecionados: 0")
        self.selecionados_label.setObjectName("orcamentoItemCusteioSelecionados")

        self.add_selections_button = QPushButton("Adicionar Seleções")
        self.add_selections_button.clicked.connect(self.adicionar_selecoes)

        layout.addWidget(title)
        layout.addWidget(self.library_search)
        layout.addWidget(self.tree_biblioteca_pecas, stretch=1)
        layout.addWidget(self.so_selecionados_check)
        layout.addWidget(self.selecionados_label)
        layout.addWidget(self.add_selections_button)

        panel.setLayout(layout)
        panel.setMinimumWidth(300)
        return panel

    def _carregar_biblioteca(self) -> None:
        """Load active piece definitions for the library tree."""
        try:
            with SessionLocal() as session:
                self._biblioteca_pecas = DefPecaService(
                    session
                ).listar_ativas_para_biblioteca()
        except SQLAlchemyError:
            self._biblioteca_pecas = []

        self._preencher_biblioteca()

    def _preencher_biblioteca(self) -> None:
        """Fill the library tree, grouped by piece group and filtered."""
        termo = self.library_search.text().strip().lower()
        so_selecionados = self.so_selecionados_check.isChecked()

        self.tree_biblioteca_pecas.blockSignals(True)
        self.tree_biblioteca_pecas.clear()

        grupos: dict[str, QTreeWidgetItem] = {}
        for peca in self._biblioteca_pecas:
            codigo_orlas = self._format_codigo_orlas(peca)

            if termo and not self._peca_matches(peca, codigo_orlas, termo):
                continue
            if so_selecionados and peca.id not in self._selecionados:
                continue

            grupo = (peca.grupo or "").strip().upper() or "SEM GRUPO"
            parent = grupos.get(grupo)
            if parent is None:
                parent = QTreeWidgetItem([grupo])
                self.tree_biblioteca_pecas.addTopLevelItem(parent)
                grupos[grupo] = parent

            texto = f"{peca.codigo} - {peca.nome} [{codigo_orlas}]"
            if peca.tipo_peca == COMPOSTA:
                texto += " (composta)"

            leaf = QTreeWidgetItem([texto])
            leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            leaf.setCheckState(
                0,
                Qt.CheckState.Checked
                if peca.id in self._selecionados
                else Qt.CheckState.Unchecked,
            )
            leaf.setData(
                0, Qt.ItemDataRole.UserRole, self._peca_para_dados(peca, codigo_orlas)
            )
            parent.addChild(leaf)

        self.tree_biblioteca_pecas.expandAll()
        self.tree_biblioteca_pecas.blockSignals(False)
        self._atualizar_contador()

    def _peca_para_dados(self, peca: DefPecaResumo, codigo_orlas: str) -> dict:
        """Build the data stored on a leaf tree item."""
        return {
            "def_peca_id": peca.id,
            "codigo": peca.codigo,
            "nome": peca.nome,
            "tipo": peca.tipo_peca,
            "grupo": peca.grupo,
            "codigo_orlas": codigo_orlas,
            "chave_valueset_material": peca.chave_valueset_material,
            "permite_acabamento": peca.permite_acabamento,
        }

    def _format_codigo_orlas(self, peca: DefPecaResumo) -> str:
        """Build the orla code (e.g. 2200) from the four orla sides."""
        return f"{peca.orla_c1}{peca.orla_c2}{peca.orla_l1}{peca.orla_l2}"

    def _peca_matches(self, peca: DefPecaResumo, codigo_orlas: str, termo: str) -> bool:
        """Return True when a piece matches the search term."""
        campos = [
            peca.codigo,
            peca.nome,
            peca.grupo or "",
            peca.tipo_peca,
            codigo_orlas,
        ]
        return any(termo in (campo or "").lower() for campo in campos)

    def _aplicar_filtro_biblioteca(self, *_args) -> None:
        """Re-fill the library tree applying the search and selection filter."""
        self._preencher_biblioteca()

    def _on_biblioteca_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        """Track the selected pieces when a leaf checkbox changes."""
        dados = item.data(0, Qt.ItemDataRole.UserRole)
        if dados is None:
            return

        peca_id = dados["def_peca_id"]
        if item.checkState(0) == Qt.CheckState.Checked:
            self._selecionados.add(peca_id)
        else:
            self._selecionados.discard(peca_id)

        self._atualizar_contador()

    def _atualizar_contador(self) -> None:
        """Update the selected pieces counter label."""
        self.selecionados_label.setText(f"Selecionados: {len(self._selecionados)}")

    def adicionar_selecoes(self) -> None:
        """Placeholder action: inserting pieces into costing is a future phase."""
        if not self._selecionados:
            self.status_label.setText("Selecione pelo menos uma peça.")
            return

        self.status_label.setText(
            f"Peças selecionadas: {len(self._selecionados)}. "
            "Inserção de peças no custeio será implementada na próxima fase."
        )

    def _create_item_info_widget(self) -> QWidget:
        """Create the item base data form."""
        widget = QWidget()
        form_layout = QFormLayout()

        for key, label in [
            ("codigo", "C\u00f3digo"),
            ("item", "Item"),
            ("tipo", "Tipo"),
            ("descricao", "Descri\u00e7\u00e3o"),
            ("altura", "Altura/Comp"),
            ("largura", "Largura"),
            ("profundidade", "Profundidade"),
            ("quantidade", "Quantidade"),
            ("unidade", "Unidade"),
        ]:
            value_label = QLabel("")
            self._item_info_labels[key] = value_label
            form_layout.addRow(label, value_label)

        widget.setLayout(form_layout)
        return widget

    def _update_item_info(self) -> None:
        """Update title, breadcrumb and item base labels."""
        self.title_label.setText(self._build_title())
        self.breadcrumb.set_items(self._build_breadcrumb_items())

        values = {
            "codigo": self.item.codigo or "",
            "item": self.item.item,
            "tipo": get_item_type_label(self.item.tipo_item),
            "descricao": self.item.descricao or "",
            "altura": format_mm(self.item.altura),
            "largura": format_mm(self.item.largura),
            "profundidade": format_mm(self.item.profundidade),
            "quantidade": format_quantity(self.item.quantidade),
            "unidade": self.item.unidade or "",
        }

        for key, value in values.items():
            label = self._item_info_labels.get(key)
            if label is not None:
                label.setText(value)

    def _preencher_tabela(self, linhas: list[OrcamentoItemCusteioLinhaResumo]) -> None:
        """Fill the costing lines table."""
        self.table.setRowCount(len(linhas))

        for row_index, linha in enumerate(linhas):
            values = [
                get_custeio_linha_type_label(linha.tipo_linha),
                linha.codigo or "",
                linha.descricao,
                linha.unidade or "",
                format_quantity(linha.quantidade),
                format_quantity(linha.comp),
                format_quantity(linha.larg),
                format_quantity(linha.esp),
                format_currency(linha.custo_total),
                format_currency(linha.preco_total),
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _handle_back(self) -> None:
        """Return to the items page through the optional callback."""
        if self.on_back is not None:
            self.on_back()

    def _build_title(self) -> str:
        """Return the page title for the active item."""
        return f"Custeio do Item: {self._format_item_label(self.item)}"

    def _build_breadcrumb_items(self) -> list[str]:
        """Return breadcrumb items for the active item costing page."""
        items: list[str] = []
        if self.orcamento_codigo:
            items.append(f"Or\u00e7amento {self.orcamento_codigo}")

        items.append(f"Item: {self._format_item_label(self.item)}")
        items.append("Custeio")
        return items

    @staticmethod
    def _format_item_label(item: OrcamentoItemResumo) -> str:
        """Return a display label for one item."""
        if item.codigo:
            return f"{item.codigo} - {item.item}"

        return item.item

    @staticmethod
    def _format_bool(value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "N\u00e3o"
