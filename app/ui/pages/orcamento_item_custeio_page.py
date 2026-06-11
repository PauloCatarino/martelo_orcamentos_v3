"""Budget item costing page."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemDelegate,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
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
from app.domain.custos import fator_desperdicio
from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    OPERACAO_MANUAL,
    PECA,
    PECA_COMPOSTA,
    get_custeio_linha_type_label,
)
from app.domain.item_types import get_item_type_label
from app.domain.numeros import formatar_percentagem
from app.domain.peca_types import COMPOSTA
from app.repositories.def_peca_repository import DefPecaResumo
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.def_maquina_service import DefMaquinaService
from app.services.def_peca_service import DefPecaService
from app.services.orcamento_item_service import OrcamentoItemService
from app.ui.dialogs.custeio_linha_acabamento_dialog import CusteioLinhaAcabamentoDialog
from app.ui.dialogs.custeio_linha_material_dialog import CusteioLinhaMaterialDialog
from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog
from app.ui.dialogs.operacao_manual_dialog import OperacaoManualDialog
from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage
from app.ui.widgets.breadcrumb import Breadcrumb
from app.ui.widgets.table_item import criar_item_tabela
from app.utils.formatters import format_currency, format_mm, format_quantity


class CusteioLinhasTable(QTableWidget):
    """Costing table with Excel-like editing.

    Pressing Enter while editing commits and moves to the NEXT EDITABLE cell to
    the right in the same row (skipping read-only columns), wrapping to the first
    editable cell of the next row, and opens its editor. Tab keeps the standard
    behaviour and Esc cancels (Qt default). Read-only cells stay non-editable.
    """

    def closeEditor(self, editor, hint) -> None:
        """Move to the next editable cell on Enter (NoHint); keep Tab/Esc default."""
        avancar = hint == QAbstractItemDelegate.EndEditHint.NoHint
        row = self.currentRow()
        col = self.currentColumn()

        super().closeEditor(editor, hint)

        if avancar:
            proxima = self._proxima_celula_editavel(row, col)
            if proxima is not None:
                QTimer.singleShot(0, lambda rc=proxima: self._editar_celula(*rc))

    def _celula_editavel(self, row: int, col: int) -> bool:
        item = self.item(row, col)
        return item is not None and bool(item.flags() & Qt.ItemFlag.ItemIsEditable)

    def _proxima_celula_editavel(self, row: int, col: int):
        """Return (row, col) of the next editable cell (right, then next rows)."""
        if row < 0 or col < 0:
            return None

        for c in range(col + 1, self.columnCount()):
            if self._celula_editavel(row, c):
                return row, c

        for r in range(row + 1, self.rowCount()):
            for c in range(self.columnCount()):
                if self._celula_editavel(r, c):
                    return r, c

        return None

    def _editar_celula(self, row: int, col: int) -> None:
        """Select a cell and open its editor when it is editable."""
        if not (0 <= row < self.rowCount() and 0 <= col < self.columnCount()):
            return

        self.setCurrentCell(row, col)
        item = self.item(row, col)
        if item is not None and bool(item.flags() & Qt.ItemFlag.ItemIsEditable):
            self.editItem(item)


class OrcamentoItemCusteioPage(QWidget):
    """Page for the costing workspace of one budget item."""

    TABLE_HEADERS = [
        # Identificacao
        "Ordem",
        "Tipo linha",
        "C\u00f3digo",
        "Descri\u00e7\u00e3o livre",
        "Def. Pe\u00e7a",
        "Descri\u00e7\u00e3o",
        "M\u00f3dulo",
        "Linha pai",
        "N\u00edvel",
        # Quantidades e medidas
        "QT mod",
        "QT und",
        "QT total",
        "Comp",
        "Larg",
        "Esp",
        "Comp real",
        "Larg real",
        "Esp real",
        "\u00c1rea m\u00b2",
        "Per\u00edmetro ML",
        # ValueSet / materia-prima
        "Chave ValueSet",
        "Mat. default",
        "Ref LE",
        "Descri\u00e7\u00e3o no or\u00e7amento",
        "Unidade",
        "Pre\u00e7o l\u00edquido",
        "Desp %",
        "Tipo MP",
        "Fam\u00edlia",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "SPP ML und",
        "SPP ML total",
        # Orlas
        "C\u00f3digo orlas",
        "Orla 0.4",
        "Orla 1.0",
        "ML orla fina",
        "ML orla grossa",
        "Custo orla fina",
        "Custo orla grossa",
        # Acabamentos
        "Acab. face sup",
        "Acab. face inf",
        "\u00c1rea acab. sup",
        "\u00c1rea acab. inf",
        "Custo acabamento",
        # Operacoes / producao
        "M\u00e1quina",
        "Opera\u00e7\u00f5es",
        "Tempo corte",
        "Tempo orlagem",
        "Tempo CNC",
        "Tempo montagem",
        "Tempo manual",
        "Tempo setup",
        "Custo corte",
        "Custo orlagem",
        "Custo CNC",
        "Custo mont./manual",
        "Custo produ\u00e7\u00e3o",
        # Flags de inclusao
        "Excluir MP",
        "Excluir Orla",
        "Excluir Ferragem",
        "Excluir Produ\u00e7\u00e3o",
        "Excluir Acabamento",
        "Excluir MO",
        # Serie / STD
        "Tipo produ\u00e7\u00e3o",
        "Fator s\u00e9rie",
        "Observa\u00e7\u00f5es produ\u00e7\u00e3o",
        # Custos
        "Custo MP",
        "Custo ferragem",
        "Custo orlas",
        "Custo acabamento",
        "Custo opera\u00e7\u00f5es",
        "Custo total",
        "Margem %",
        "Pre\u00e7o total",
        # Controlo
        "Origem",
        "Editado localmente",
        "Ativo",
    ]

    # Editable columns mapped to the cost line field they update.
    EDITABLE_COLUMNS = {
        "QT mod": "qt_mod",
        "QT und": "qt_und",
        "Comp": "comp",
        "Larg": "larg",
        "Esp": "esp",
    }

    # Cost-exclusion checkbox columns mapped to the line flag they toggle.
    # Checked = exclude that cost from custo_total; unchecked = include it.
    EXCLUSAO_COLUMNS = {
        "Excluir MP": "excluir_mp",
        "Excluir Orla": "excluir_orla",
        "Excluir Ferragem": "excluir_ferragem",
        "Excluir Produção": "excluir_producao",
        "Excluir Acabamento": "excluir_acabamento",
        "Excluir MO": "excluir_mo",
    }
    EXCLUSAO_TOOLTIP = (
        "Visto ativo = excluir este custo do cálculo. Sem visto = incluir no cálculo."
    )

    # Header tooltips explaining each column (the formula tooltips are per cell).
    HEADER_TOOLTIPS = {
        "Comp": "Comprimento da peça (editável; aceita expressões).",
        "Larg": "Largura da peça (editável; aceita expressões).",
        "Esp": "Espessura da peça (normalmente vem do material).",
        "QT mod": "Quantidade por módulo (editável).",
        "QT und": "Quantidade de unidades (editável).",
        "Área m²": "Área por unidade da peça (Comp × Larg).",
        "Perímetro ML": "Perímetro por unidade, em metros lineares.",
        "ML orla fina": "Metros lineares de orla fina (total da linha).",
        "ML orla grossa": "Metros lineares de orla grossa (total da linha).",
        "SPP ML und": "Consumo em metro linear por unidade.",
        "SPP ML total": "Consumo em metro linear total (× QT total).",
        "Custo MP": "Custo da matéria-prima (M2): área × qt × preço × (1+desp).",
        "Custo ferragem": "Custo de ferragens (UND) ou de materiais ML.",
        "Custo orla fina": "Custo da orla fina: ML × preço/ml.",
        "Custo orla grossa": "Custo da orla grossa: ML × preço/ml.",
        "Custo orlas": "Soma do custo das orlas (fina + grossa).",
        "Custo acabamento": "Custo de acabamento: área acab. × preço × (1+desp), por face.",
        "Custo corte": "Custo de corte: perímetro × qt × €/ML + qt × setup.",
        "Custo orlagem": "Custo de orlagem: ML de orla × €/ML + qt × setup.",
        "Custo CNC": "Custo de CNC pelo escalão de área da máquina × qt.",
        "Custo mont./manual": "Montagem/manual: (tempo / 60) × custo/hora da máquina.",
        "Custo produção": "Soma da produção (corte + orlagem + CNC + mont./manual).",
        "Custo total": "Soma dos custos da linha, respeitando os checks Excluir.",
        "Editado localmente": "Sim quando o material/acabamento foi editado na linha.",
    }

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
        self._custeio_by_row: dict[int, OrcamentoItemCusteioLinhaResumo] = {}
        self._carregando_tabela = False

        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())
        self.title_label = QLabel(self._build_title())
        self.title_label.setObjectName("orcamentoItemCusteioTitle")

        self.back_button = QPushButton("Voltar aos Items")
        self.back_button.clicked.connect(self._handle_back)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.atualizar_geral)

        self.recalc_measures_button = QPushButton("Recalcular Medidas")
        self.recalc_measures_button.clicked.connect(self.recalcular_medidas)

        self.insert_division_button = QPushButton("Inserir Divis\u00e3o")
        self.insert_division_button.clicked.connect(self.inserir_divisao)

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
        actions_layout.addWidget(self.recalc_measures_button)
        actions_layout.addWidget(self.insert_division_button)
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

        self.table = CusteioLinhasTable(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        for column_index, header in enumerate(self.TABLE_HEADERS):
            header_item = self.table.horizontalHeaderItem(column_index)
            if header_item is None:
                continue
            if header in self.EXCLUSAO_COLUMNS:
                header_item.setToolTip(self.EXCLUSAO_TOOLTIP)
            elif header in self.HEADER_TOOLTIPS:
                header_item.setToolTip(self.HEADER_TOOLTIPS[header])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        # Fast (Excel-like) editing: one click / typing enters edit; read-only
        # cells stay blocked (they have no ItemIsEditable flag).
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.CurrentChanged
            | QTableWidget.EditTrigger.SelectedClicked
            | QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.AnyKeyPressed
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_contexto_material)

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

    def recalcular_medidas(self) -> None:
        """Recompute quantities, real measures, area and perimeter of the item."""
        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).recalcular_medidas_do_item(
                    self.item_id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível recalcular as medidas.")
            return

        self.carregar()
        self.status_label.setText("Medidas recalculadas.")

    def atualizar_geral(self) -> None:
        """Main refresh: recompute measures and orlas, then reload the table."""
        try:
            with SessionLocal() as session:
                service = OrcamentoItemCusteioLinhaService(session)
                service.recalcular_medidas_do_item(self.item_id)
                service.aplicar_acabamentos_do_item(self.item_id)
                service.recalcular_areas_acabamento_do_item(self.item_id)
                service.recalcular_orlas_do_item(self.item_id)
                service.recalcular_custo_materia_prima_do_item(self.item_id)
                service.recalcular_custos_ferragens_do_item(self.item_id)
                service.recalcular_custos_ml_do_item(self.item_id)
                service.recalcular_custo_acabamento_do_item(self.item_id)
                service.aplicar_operacoes_do_item(self.item_id)
                service.recalcular_custos_producao_do_item(self.item_id)
                service.recalcular_custo_total_do_item(self.item_id)
        except (SQLAlchemyError, ValueError):
            self.carregar()
            self.status_label.setText("Não foi possível atualizar o item.")
            return

        self.carregar()
        self.status_label.setText(
            "Item atualizado (medidas, orlas, custos parciais e custo total "
            "recalculados)."
        )

    def inserir_divisao(self) -> None:
        """Insert an independent-division line (local HM/LM/PM measure context)."""
        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).inserir_divisao_independente(
                    self.item_id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível inserir a divisão.")
            return

        self.carregar()
        self.status_label.setText("Divisão independente inserida.")

    def _coluna_editavel(
        self, header: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> bool:
        """Return True when the given column is editable for the given line."""
        if header in self.EDITABLE_COLUMNS:
            if linha.tipo_linha == OPERACAO_MANUAL:
                # Manual-operation lines have no measures: only the quantity is
                # editable (editing it recomputes the time and cost).
                return header in ("QT mod", "QT und")
            return True

        if header == "Descrição livre" and linha.tipo_linha == DIVISAO_INDEPENDENTE:
            return True

        return False

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
        """Create cost lines for the selected simple library pieces."""
        if not self._selecionados:
            self.status_label.setText("Selecione pelo menos uma peça.")
            return

        def_peca_ids = list(self._selecionados)
        try:
            with SessionLocal() as session:
                result = OrcamentoItemCusteioLinhaService(
                    session
                ).adicionar_pecas_da_biblioteca(self.item_id, def_peca_ids)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível adicionar as peças ao custeio.")
            return

        self._selecionados.clear()
        self.carregar()
        self.status_label.setText(
            f"Peças adicionadas: {result.criadas}. "
            f"Componentes adicionados: {result.componentes}. "
            f"Ignoradas: {result.ignoradas}."
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
        """Fill the costing lines table, mapping known fields to columns."""
        self._carregando_tabela = True
        try:
            self._custeio_by_row = {}
            self.table.setRowCount(len(linhas))

            for row_index, linha in enumerate(linhas):
                self._custeio_by_row[row_index] = linha
                self._preencher_linha(row_index, linha)
        finally:
            self._carregando_tabela = False

    def _preencher_linha(
        self, row_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Fill one table row from a line resumo (caller guards _carregando_tabela)."""
        valores = self._linha_para_valores(linha)
        for column_index, header in enumerate(self.TABLE_HEADERS):
            if header in self.EXCLUSAO_COLUMNS:
                item = self._criar_item_exclusao(header, linha)
            else:
                # Formula tooltip on result columns; otherwise the full content
                # (helps narrow text columns).
                tooltip = self._tooltip_formula(header, linha)
                item = criar_item_tabela(valores.get(header, ""), tooltip=tooltip)
                if self._coluna_editavel(header, linha):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_index, column_index, item)

    def _atualizar_linha_visivel(
        self, row_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Refresh a single row in place (no full reload) after an inline edit."""
        self._carregando_tabela = True
        try:
            self._custeio_by_row[row_index] = linha
            self._preencher_linha(row_index, linha)
        finally:
            self._carregando_tabela = False

    def _linha_calcula_total(self, linha: OrcamentoItemCusteioLinhaResumo) -> bool:
        """Return True when the line computes a total (not division/composite)."""
        return linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA)

    def _criar_item_exclusao(
        self, header: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> QTableWidgetItem:
        """Build a checkbox cell for a cost-exclusion column."""
        item = QTableWidgetItem()
        item.setToolTip(self.EXCLUSAO_TOOLTIP)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if self._linha_calcula_total(linha):
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            excluido = bool(getattr(linha, self.EXCLUSAO_COLUMNS[header], False))
            item.setCheckState(
                Qt.CheckState.Checked if excluido else Qt.CheckState.Unchecked
            )
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        return item

    def _tooltip_formula(
        self, header: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> str | None:
        """Return a 3-block per-cell tooltip with the line's real numbers, or None.

        Every calculated column is documented with: (1) a plain-language rule,
        (2) the generic formula, and (3) the substitution with the line's real
        values and the result. Machine €/hour is back-derived from the stored
        cost and time so the substitution stays exact without a DB lookup; when a
        value is missing the substitution is omitted but the rule/formula remain.
        """
        qt = linha.quantidade
        ml_orla_total = (linha.ml_orla_fina or Decimal("0")) + (
            linha.ml_orla_grossa or Decimal("0")
        )
        fator = fator_desperdicio(linha.desperdicio_percentagem)

        # Measure expressions: rule + formula + evaluated value.
        if header == "Comp":
            return self._tooltip_medida("Comprimento", linha.comp, linha.comp_real)
        if header == "Larg":
            return self._tooltip_medida("Largura", linha.larg, linha.larg_real)
        if header == "Esp":
            return self._tooltip_medida("Espessura", linha.esp, linha.esp_real)

        if header == "Área m²" and linha.area_m2 is not None:
            return self._tooltip_3(
                "Área da peça: superfície de uma unidade, base do custo de MP e CNC.",
                "Área = Comp × Larg / 1.000.000 (mm² → m²)",
                f"= {format_quantity(linha.comp_real)} × "
                f"{format_quantity(linha.larg_real)} / 1.000.000 = "
                f"{format_quantity(linha.area_m2)} m²",
            )
        if header == "Perímetro ML" and linha.perimetro_ml is not None:
            return self._tooltip_3(
                "Perímetro da peça: contorno de uma unidade, base do custo de corte.",
                "Perímetro = 2 × (Comp + Larg) / 1000 (mm → m)",
                f"= 2 × ({format_quantity(linha.comp_real)} + "
                f"{format_quantity(linha.larg_real)}) / 1000 = "
                f"{format_quantity(linha.perimetro_ml)} ml",
            )

        if header == "Área acab. sup" and linha.area_acabamento_sup is not None:
            return self._tooltip_3(
                "Área de acabamento da face superior: só conta se a face tiver "
                "acabamento.",
                "Área acab. sup = Área × QT (se houver acabamento)",
                f"acabamento {linha.acabamento_face_sup or '—'}: "
                f"{format_quantity(linha.area_m2)} × {format_quantity(qt)} = "
                f"{format_quantity(linha.area_acabamento_sup)} m²",
            )
        if header == "Área acab. inf" and linha.area_acabamento_inf is not None:
            return self._tooltip_3(
                "Área de acabamento da face inferior: só conta se a face tiver "
                "acabamento.",
                "Área acab. inf = Área × QT (se houver acabamento)",
                f"acabamento {linha.acabamento_face_inf or '—'}: "
                f"{format_quantity(linha.area_m2)} × {format_quantity(qt)} = "
                f"{format_quantity(linha.area_acabamento_inf)} m²",
            )

        if header == "ML orla fina" and linha.ml_orla_fina is not None:
            return self._tooltip_3(
                "Metros de orla fina (0.4): lados orlados pelo código de orlas, "
                "multiplicados pela QT, mais a margem da orladora.",
                "ML orla fina = lados orlados × QT + margem",
                f"→ {format_quantity(linha.ml_orla_fina)} ml (QT {format_quantity(qt)})",
            )
        if header == "ML orla grossa" and linha.ml_orla_grossa is not None:
            return self._tooltip_3(
                "Metros de orla grossa (1.0): lados orlados pelo código de orlas, "
                "multiplicados pela QT, mais a margem da orladora.",
                "ML orla grossa = lados orlados × QT + margem",
                f"→ {format_quantity(linha.ml_orla_grossa)} ml (QT {format_quantity(qt)})",
            )

        if header == "Custo MP" and linha.custo_mp is not None:
            return self._tooltip_3(
                "Custo da matéria-prima (placa M2): área da peça pela quantidade, "
                "ao preço do material, acrescido do desperdício.",
                "Custo MP = Área × QT × preço × (1 + desp)",
                f"= {format_quantity(linha.area_m2)} m² × {format_quantity(qt)} × "
                f"{format_currency(linha.preco_liquido)} × {format_quantity(fator)} = "
                f"{format_currency(linha.custo_mp)}",
            )
        if header == "Custo ferragem" and linha.custo_ferragem is not None:
            return self._tooltip_3(
                "Custo de ferragens/acessórios (à unidade ou a metro linear): "
                "quantidade ao preço do material, acrescido do desperdício.",
                "Custo ferragem = QT × preço × (1 + desp)",
                f"= {format_quantity(qt)} × {format_currency(linha.preco_liquido)} × "
                f"{format_quantity(fator)} = {format_currency(linha.custo_ferragem)}",
            )
        if header == "Custo orla fina" and linha.custo_orla_fina is not None:
            return self._tooltip_3(
                "Custo da orla fina: metros de orla ao preço por metro (convertido "
                "de m² pela largura da fita).",
                "Custo orla fina = ML orla fina × preço/ml",
                f"= {format_quantity(linha.ml_orla_fina)} ml → "
                f"{format_currency(linha.custo_orla_fina)}",
            )
        if header == "Custo orla grossa" and linha.custo_orla_grossa is not None:
            return self._tooltip_3(
                "Custo da orla grossa: metros de orla ao preço por metro "
                "(convertido de m² pela largura da fita).",
                "Custo orla grossa = ML orla grossa × preço/ml",
                f"= {format_quantity(linha.ml_orla_grossa)} ml → "
                f"{format_currency(linha.custo_orla_grossa)}",
            )
        if header == "Custo orlas" and linha.custo_orlas is not None:
            return self._tooltip_3(
                "Custo total de orlas: soma das orlas fina e grossa da peça.",
                "Custo orlas = orla fina + orla grossa",
                f"= {format_currency(linha.custo_orla_fina)} + "
                f"{format_currency(linha.custo_orla_grossa)} = "
                f"{format_currency(linha.custo_orlas)}",
            )
        if header == "Custo acabamento" and linha.custo_acabamento is not None:
            return self._tooltip_3(
                "Custo de acabamento: área acabada de cada face ao preço do "
                "acabamento, acrescido do desperdício.",
                "Custo acabamento = Σ faces (área acab. × preço × (1 + desp))",
                f"= sup {format_quantity(linha.area_acabamento_sup)} m² + "
                f"inf {format_quantity(linha.area_acabamento_inf)} m² → "
                f"{format_currency(linha.custo_acabamento)}",
            )
        if header == "Custo corte" and linha.custo_corte is not None:
            return self._tooltip_3(
                "Custo de corte: perímetro da peça cortado na seccionadora, "
                "cobrado ao metro linear, mais movimentação por peça.",
                "Custo corte = perímetro × QT × tarifa €/ML + QT × setup €/peça",
                f"= {format_quantity(linha.perimetro_ml)} ml × {format_quantity(qt)} → "
                f"{format_currency(linha.custo_corte)}",
            )
        if header == "Custo orlagem" and linha.custo_orlagem is not None:
            return self._tooltip_3(
                "Custo de orlagem: metros de orla colados na orladora, cobrados ao "
                "metro linear, mais movimentação por peça.",
                "Custo orlagem = ML orla total × tarifa €/ML + QT × setup €/peça",
                f"= {format_quantity(ml_orla_total)} ml × {format_quantity(qt)} → "
                f"{format_currency(linha.custo_orlagem)}",
            )
        if header == "Custo CNC" and linha.custo_cnc is not None:
            return self._tooltip_3(
                "Custo de CNC: maquinação cobrada pelo escalão de área da peça, "
                "multiplicada pela quantidade.",
                "Custo CNC = preço do escalão (por área) × QT",
                f"= área {format_quantity(linha.area_m2)} m² × QT "
                f"{format_quantity(qt)} → {format_currency(linha.custo_cnc)}",
            )
        if header == "Custo mont./manual" and linha.custo_montagem_manual is not None:
            return self._tooltip_montagem_manual(linha, qt)
        if header == "Custo produção" and linha.custo_producao is not None:
            return self._tooltip_3(
                "Custo de produção da peça: soma dos custos de corte, orlagem, CNC "
                "e montagem/manual.",
                "Custo produção = corte + orlagem + CNC + mont./manual",
                f"= {format_currency(linha.custo_corte)} + "
                f"{format_currency(linha.custo_orlagem)} + "
                f"{format_currency(linha.custo_cnc)} + "
                f"{format_currency(linha.custo_montagem_manual)} = "
                f"{format_currency(linha.custo_producao)}",
            )
        if header == "Custo total" and linha.custo_total is not None:
            return self._tooltip_3(
                "Custo total da linha: soma de matéria-prima, ferragens, orlas, "
                "acabamento e produção, descontando os custos marcados em Excluir.",
                "Custo total = MP + ferragem + orlas + acabamento + produção "
                "(− excluídos)",
                f"= MP {format_currency(linha.custo_mp)} + "
                f"ferragem {format_currency(linha.custo_ferragem)} + "
                f"orlas {format_currency(linha.custo_orlas)} + "
                f"acab {format_currency(linha.custo_acabamento)} + "
                f"prod {format_currency(linha.custo_producao)} = "
                f"{format_currency(linha.custo_total)}",
            )

        return None

    def _tooltip_3(
        self, descricao: str, formula: str, substituicao: str | None
    ) -> str:
        """Join the three tooltip blocks (rule, formula, substitution)."""
        blocos = [descricao, formula]
        if substituicao:
            blocos.append(substituicao)
        return "\n".join(blocos)

    def _custo_hora_derivado(self, custo, tempo_min):
        """Back-derive a machine €/hour from a stored cost and time (or None)."""
        custo_v = custo if isinstance(custo, Decimal) else None
        tempo_v = tempo_min if isinstance(tempo_min, Decimal) else None
        if custo_v is None or not tempo_v:
            return None
        return custo_v * Decimal("60") / tempo_v

    def _tooltip_montagem_manual(
        self, linha: OrcamentoItemCusteioLinhaResumo, qt
    ) -> str:
        """3-block tooltip for the assembly/manual cost (piece or manual line)."""
        custo = linha.custo_montagem_manual
        if linha.tipo_linha == OPERACAO_MANUAL:
            minutos = linha.minutos_unitarios
            if minutos is None and linha.tempo_manual is not None and qt:
                minutos = linha.tempo_manual / qt
            custo_hora = self._custo_hora_derivado(custo, linha.tempo_manual)
            maquina = linha.maquina or "—"
            return self._tooltip_3(
                f"Trabalho avulso cobrado ao tempo na máquina {maquina}.",
                "Custo = minutos × QT / 60 × custo/hora",
                f"= {format_quantity(minutos)} × {format_quantity(qt)} / 60 × "
                f"{format_currency(custo_hora)} = {format_currency(custo)}",
            )

        tempo_total = (
            (linha.tempo_montagem or Decimal("0"))
            + (linha.tempo_manual or Decimal("0"))
            + (linha.tempo_setup or Decimal("0"))
        )
        custo_hora = self._custo_hora_derivado(custo, tempo_total)
        return self._tooltip_3(
            "Custo de montagem/trabalho manual: tempo das operações de montagem e "
            "manual da peça, ao custo/hora da máquina.",
            "Custo mont./manual = (tempo / 60) × custo/hora da máquina",
            f"= {format_quantity(tempo_total)} min / 60 × "
            f"{format_currency(custo_hora)} = {format_currency(custo)}",
        )

    def _tooltip_medida(self, label, raw, real) -> str | None:
        """3-block tooltip for a measure cell that holds an expression."""
        if real is None:
            return None

        texto = (raw or "").strip()
        if not (texto and any(c.isalpha() or c in "+-*/()" for c in texto)):
            return None

        return self._tooltip_3(
            f"{label} da peça: medida avaliada no contexto do item "
            "(H=altura, L=largura, P=profundidade).",
            f"{label} = expressão escrita pelo utilizador",
            f"= {texto} → {format_mm(real)}",
        )

    def _on_cell_changed(self, row: int, column: int) -> None:
        """Save an edited quantity/measure cell and recompute the line."""
        if self._carregando_tabela:
            return

        header = self.TABLE_HEADERS[column]
        linha = self._custeio_by_row.get(row)
        if linha is None:
            return

        if header in self.EXCLUSAO_COLUMNS:
            self._on_exclusao_changed(row, column, header, linha)
            return

        if not self._coluna_editavel(header, linha):
            return

        # On a normal piece/material line, Esp normally comes from the material:
        # confirm before accepting a manual edit.
        if header == "Esp" and linha.tipo_linha not in (
            DIVISAO_INDEPENDENTE,
            PECA_COMPOSTA,
        ):
            if not self._confirmar_edicao_espessura():
                self.carregar()  # discard the manual edit
                return

        item = self.table.item(row, column)
        novo_valor = item.text().strip() if item is not None else ""

        valores = {
            "qt_mod": linha.qt_mod,
            "qt_und": linha.qt_und,
            "comp": linha.comp,
            "larg": linha.larg,
            "esp": linha.esp,
        }
        descricao = None
        if header == "Descrição livre":
            descricao = novo_valor
        else:
            valores[self.EDITABLE_COLUMNS[header]] = novo_valor

        try:
            with SessionLocal() as session:
                # Fast inline edit: save only this line; the general recompute of
                # costs (and division propagation) stays on the Atualizar button.
                resumo = OrcamentoItemCusteioLinhaService(
                    session
                ).atualizar_medidas_linha(
                    linha.id,
                    qt_mod=valores["qt_mod"],
                    qt_und=valores["qt_und"],
                    comp=valores["comp"],
                    larg=valores["larg"],
                    esp=valores["esp"],
                    descricao=descricao,
                    propagar_item=False,
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar a linha de custeio.")
            return

        if resumo is not None:
            self._atualizar_linha_visivel(row, resumo)
        self.status_label.setText(
            "Linha atualizada (medidas). Use Atualizar para recalcular custos."
        )

    def _on_exclusao_changed(
        self, row: int, column: int, header: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Save a cost-exclusion checkbox change and recompute the total."""
        if not self._linha_calcula_total(linha):
            return

        item = self.table.item(row, column)
        excluir = item is not None and item.checkState() == Qt.CheckState.Checked

        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).atualizar_exclusao_linha(
                    linha.id, self.EXCLUSAO_COLUMNS[header], excluir
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar a exclusão de custo.")
            return

        self.carregar()
        self.status_label.setText("Custo total recalculado.")

    def _confirmar_edicao_espessura(self) -> bool:
        """Ask before letting the user override the material-derived Esp."""
        box = QMessageBox(self)
        box.setWindowTitle("Editar espessura")
        box.setText(
            "A espessura desta linha vem normalmente da matéria-prima. "
            "Deseja mesmo editar manualmente?"
        )
        sim = box.addButton("Sim, editar manualmente", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is sim

    def _get_linha_selecionada(self) -> OrcamentoItemCusteioLinhaResumo | None:
        """Return the cost line of the selected table row."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._custeio_by_row.get(row)

    def _linha_aceita_material(self, linha: OrcamentoItemCusteioLinhaResumo) -> bool:
        """Return True when the line type can carry material (not division/composite)."""
        return linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA)

    def _menu_contexto_material(self, pos) -> None:
        """Show a right-click menu with the line material and delete actions."""
        item = self.table.itemAt(pos)
        if item is not None:
            selecionadas = {idx.row() for idx in self.table.selectionModel().selectedRows()}
            if item.row() not in selecionadas:
                self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.addAction("Selecionar Matéria-Prima", self.selecionar_materia_prima_linha)
        menu.addAction("Editar Dados do Material", self.editar_dados_material_linha)
        menu.addAction("Limpar Dados do Material", self.limpar_dados_material_linha)
        menu.addSeparator()
        menu.addAction("Editar Dados do Acabamento", self.editar_dados_acabamento_linha)
        menu.addSeparator()
        menu.addAction("Inserir operação manual...", self.inserir_operacao_manual_linha)
        linha_sel = self._get_linha_selecionada()
        if linha_sel is not None and linha_sel.tipo_linha == OPERACAO_MANUAL:
            menu.addAction(
                "Editar operação manual...", self.editar_operacao_manual_linha
            )
        menu.addSeparator()
        self._preencher_menu_exclusoes(menu.addMenu("Exclusões"))
        menu.addSeparator()
        menu.addAction("Eliminar linha(s)", self.eliminar_linhas_selecionadas)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _preencher_menu_exclusoes(self, submenu) -> None:
        """Add the bulk mark/unmark actions for each exclusion column."""
        for header, campo in self.EXCLUSAO_COLUMNS.items():
            submenu.addAction(
                f"Marcar todos {header}",
                lambda _checked=False, c=campo: self._aplicar_exclusao_em_lote(c, True),
            )
            submenu.addAction(
                f"Desmarcar todos {header}",
                lambda _checked=False, c=campo: self._aplicar_exclusao_em_lote(c, False),
            )
            submenu.addSeparator()

    def _aplicar_exclusao_em_lote(self, campo: str, valor: bool) -> None:
        """Set one exclusion flag on all active lines and recompute totals."""
        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).atualizar_exclusao_em_lote(
                    self.item_id, campo, valor
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar as exclusões de custo.")
            return

        self.carregar()
        acao = "marcadas" if valor else "desmarcadas"
        self.status_label.setText(f"Exclusões {acao} e custo total recalculado.")

    def eliminar_linhas_selecionadas(self) -> None:
        """Physically delete the selected cost lines after confirmation."""
        linhas = sorted(idx.row() for idx in self.table.selectionModel().selectedRows())
        ids = [
            self._custeio_by_row[row].id
            for row in linhas
            if row in self._custeio_by_row
        ]
        if not ids:
            self.status_label.setText("Selecione pelo menos uma linha.")
            return

        if len(ids) == 1:
            mensagem = "Deseja eliminar definitivamente esta linha de custeio?"
        else:
            mensagem = (
                f"Deseja eliminar definitivamente as {len(ids)} linhas de custeio "
                "selecionadas?"
            )

        confirm = QMessageBox.question(
            self,
            "Eliminar linhas",
            mensagem,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).eliminar_linhas(ids)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível eliminar as linhas de custeio.")
            return

        self.carregar()
        self.status_label.setText(f"{len(ids)} linha(s) eliminada(s).")

    def selecionar_materia_prima_linha(self) -> None:
        """Pick a raw material and copy its snapshot into the selected line."""
        linha = self._get_linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return
        if not self._linha_aceita_material(linha):
            self.status_label.setText("Linhas de divisão não usam material.")
            return

        picker = MateriaPrimaPickerDialog(
            parent=self,
            initial_tipo=linha.tipo_materia_prima,
            initial_familia=linha.familia_materia_prima,
        )
        if not picker.exec() or picker.selected_materia is None:
            return

        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).aplicar_materia_prima_na_linha(
                    linha.id, picker.selected_materia.id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar o material da linha.")
            return

        self.carregar()
        self.status_label.setText("Material da linha atualizado.")

    def editar_dados_material_linha(self) -> None:
        """Open the dialog to manually edit the selected line's material."""
        linha = self._get_linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return
        if not self._linha_aceita_material(linha):
            self.status_label.setText("Linhas de divisão não usam material.")
            return

        saved = False

        def handle_save(dados) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoItemCusteioLinhaService(session).atualizar_material_local_linha(
                        linha.id, dados
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível atualizar o material da linha.")
                return False

            saved = True
            return True

        dialog = CusteioLinhaMaterialDialog(linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Material da linha atualizado.")

    def limpar_dados_material_linha(self) -> None:
        """Clear the material fields of the selected line after confirmation."""
        linha = self._get_linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return
        if not self._linha_aceita_material(linha):
            self.status_label.setText("Linhas de divisão não usam material.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "Tem a certeza que pretende limpar os dados de material desta linha?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).limpar_material_linha(linha.id)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar o material da linha.")
            return

        self.carregar()
        self.status_label.setText("Material da linha limpo.")

    def editar_dados_acabamento_linha(self) -> None:
        """Open the dialog to edit the selected line's finishing data locally."""
        linha = self._get_linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione uma linha.")
            return
        if linha.tipo_linha != PECA:
            self.status_label.setText("Esta linha não suporta acabamento.")
            return

        saved = False

        def handle_save(dados) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoItemCusteioLinhaService(
                        session
                    ).atualizar_acabamento_local_linha(linha.id, dados)
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível atualizar o acabamento da linha.")
                return False

            saved = True
            return True

        dialog = CusteioLinhaAcabamentoDialog(linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Acabamento da linha atualizado.")

    def _maquinas_montagem_manual(self):
        """Active machines of type MANUAL/MONTAGEM/CNC for the manual-operation dialog."""
        try:
            with SessionLocal() as session:
                maquinas = DefMaquinaService(session).listar_maquinas_ativas()
        except SQLAlchemyError:
            return []
        return [
            m for m in maquinas if (m.tipo or "").upper() in ("MANUAL", "MONTAGEM", "CNC")
        ]

    def inserir_operacao_manual_linha(self) -> None:
        """Open the dialog to add a user-defined manual-operation line."""
        maquinas = self._maquinas_montagem_manual()
        if not maquinas:
            self.status_label.setText(
                "Crie uma máquina MANUAL, MONTAGEM ou CNC (Configurações → Máquinas)."
            )
            return

        saved = False

        def handle_save(dados) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoItemCusteioLinhaService(session).inserir_operacao_manual(
                        self.item_id,
                        descricao=dados.descricao,
                        def_maquina_id=dados.def_maquina_id,
                        tempo_minutos=dados.tempo_minutos,
                        quantidade=dados.quantidade,
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível inserir a operação manual.")
                return False

            saved = True
            return True

        dialog = OperacaoManualDialog(maquinas, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Operação manual inserida.")

    def editar_operacao_manual_linha(self) -> None:
        """Open the dialog to edit the selected manual-operation line."""
        linha = self._get_linha_selecionada()
        if linha is None or linha.tipo_linha != OPERACAO_MANUAL:
            self.status_label.setText("Selecione uma linha de operação manual.")
            return

        maquinas = self._maquinas_montagem_manual()
        saved = False

        def handle_save(dados) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoItemCusteioLinhaService(session).editar_operacao_manual(
                        linha.id,
                        descricao=dados.descricao,
                        def_maquina_id=dados.def_maquina_id,
                        tempo_minutos=dados.tempo_minutos,
                        quantidade=dados.quantidade,
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível atualizar a operação manual.")
                return False

            saved = True
            return True

        dialog = OperacaoManualDialog(
            maquinas,
            descricao=linha.descricao or "",
            def_maquina_id=linha.def_maquina_id,
            tempo_minutos=linha.tempo_manual,
            quantidade=linha.quantidade,
            parent=self,
            on_save=handle_save,
        )
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Operação manual atualizada.")

    def _linha_para_valores(
        self, linha: OrcamentoItemCusteioLinhaResumo
    ) -> dict[str, str]:
        """Map a costing line to the known columns; unknown columns stay empty."""
        eh_divisao = linha.tipo_linha == DIVISAO_INDEPENDENTE
        nivel = linha.nivel or 0
        if eh_divisao:
            descricao_col = ""
            descricao_livre = linha.descricao or ""
        else:
            descricao_col = ("  - " + linha.descricao) if nivel else linha.descricao
            descricao_livre = ""
        return {
            "Ordem": "" if linha.ordem is None else str(linha.ordem),
            "Tipo linha": get_custeio_linha_type_label(linha.tipo_linha),
            "Código": linha.codigo or "",
            "Descrição livre": descricao_livre,
            "Def. Peça": linha.def_peca_codigo
            or ("" if linha.def_peca_id is None else str(linha.def_peca_id)),
            "Descrição": descricao_col,
            "Linha pai": "" if linha.linha_pai_id is None else str(linha.linha_pai_id),
            "Nível": str(nivel),
            "Módulo": "" if linha.orcamento_item_modulo_id is None
            else str(linha.orcamento_item_modulo_id),
            "QT mod": format_quantity(linha.qt_mod),
            "QT und": format_quantity(linha.qt_und),
            "QT total": format_quantity(linha.quantidade),
            "Comp": "" if linha.comp is None else str(linha.comp),
            "Larg": "" if linha.larg is None else str(linha.larg),
            "Esp": "" if linha.esp is None else str(linha.esp),
            "Comp real": format_quantity(linha.comp_real),
            "Larg real": format_quantity(linha.larg_real),
            "Esp real": format_quantity(linha.esp_real),
            "Área m²": self._format_medida3(linha.area_m2),
            "Perímetro ML": self._format_medida3(linha.perimetro_ml),
            "Chave ValueSet": linha.chave_valueset or "",
            "Mat. default": linha.mat_default or "",
            "Ref LE": linha.ref_le or "",
            "Descrição no orçamento": linha.descricao_no_orcamento or "",
            "Unidade": linha.unidade or "",
            "Preço líquido": format_currency(linha.preco_liquido),
            "Desp %": formatar_percentagem(linha.desperdicio_percentagem),
            "Tipo MP": linha.tipo_materia_prima or "",
            "Família": linha.familia_materia_prima or "",
            "Comp MP": format_quantity(linha.comp_mp),
            "Larg MP": format_quantity(linha.larg_mp),
            "Esp MP": format_quantity(linha.esp_mp),
            "SPP ML und": self._format_medida3(linha.consumo_ml_unitario),
            "SPP ML total": self._format_medida3(linha.consumo_ml_total),
            "Código orlas": linha.codigo_orlas or "",
            "Orla 0.4": linha.coresp_orla_0_4 or "",
            "Orla 1.0": linha.coresp_orla_1_0 or "",
            "ML orla fina": self._format_medida3(linha.ml_orla_fina),
            "ML orla grossa": self._format_medida3(linha.ml_orla_grossa),
            "Custo orla fina": format_currency(linha.custo_orla_fina),
            "Custo orla grossa": format_currency(linha.custo_orla_grossa),
            "Custo orlas": format_currency(linha.custo_orlas),
            "Acab. face sup": linha.acabamento_face_sup or "",
            "Acab. face inf": linha.acabamento_face_inf or "",
            "Área acab. sup": self._format_medida3(linha.area_acabamento_sup),
            "Área acab. inf": self._format_medida3(linha.area_acabamento_inf),
            "Custo MP": format_currency(linha.custo_mp),
            "Custo ferragem": format_currency(linha.custo_ferragem),
            "Custo acabamento": format_currency(linha.custo_acabamento),
            "Máquina": linha.maquina or "",
            "Operações": linha.operacoes or "",
            "Tipo produção": linha.tipo_producao or "",
            "Tempo corte": format_quantity(linha.tempo_corte),
            "Tempo orlagem": format_quantity(linha.tempo_orlagem),
            "Tempo CNC": format_quantity(linha.tempo_cnc),
            "Tempo montagem": format_quantity(linha.tempo_montagem),
            "Tempo manual": format_quantity(linha.tempo_manual),
            "Tempo setup": format_quantity(linha.tempo_setup),
            "Custo corte": format_currency(linha.custo_corte),
            "Custo orlagem": format_currency(linha.custo_orlagem),
            "Custo CNC": format_currency(linha.custo_cnc),
            "Custo mont./manual": format_currency(linha.custo_montagem_manual),
            "Custo produção": format_currency(linha.custo_producao),
            "Observações produção": linha.observacoes or "",
            "Custo total": format_currency(linha.custo_total),
            "Margem %": formatar_percentagem(linha.margem_percentagem),
            "Preço total": format_currency(linha.preco_total),
            "Origem": linha.origem_tipo or "",
            "Editado localmente": self._format_bool(linha.editado_localmente),
            "Ativo": self._format_bool(linha.ativo),
        }

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

    def _format_medida3(self, value) -> str:
        """Format an area/perimeter value with three decimals."""
        if value is None:
            return ""

        try:
            numero = Decimal(str(value)).quantize(Decimal("0.001"))
        except (InvalidOperation, ValueError):
            return ""

        return format(numero, "f").replace(".", ",")

    @staticmethod
    def _format_bool(value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "N\u00e3o"
