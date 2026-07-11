"""Budget item costing page."""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemDelegate,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyledItemDelegate,
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
from app.domain.custos import eh_unidade_ml, fator_desperdicio
from app.domain.medidas import (
    construir_contexto_item,
    normalizar_numero,
    normalizar_variaveis_medida,
)
from app.domain.orla_types import ORLA_FINA, ORLA_GROSSA
from app.domain.orlas import digitos_orla
from app.domain.quantidades import (
    LinhaQuantidade,
    ResultadoQuantidade,
    calcular_quantidades,
    formatar_cadeia,
)
from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    OPERACAO_MANUAL,
    PECA,
    PECA_COMPOSTA,
    SEPARADOR,
    get_custeio_linha_type_label,
)
from app.domain.valueset_compat import opcoes_valueset_compativeis
from app.domain.custo_producao import (
    escolher_tarifa,
    preco_peca_escalao,
    selecionar_escalao_area,
)
from app.domain.producao_types import (
    TIPO_PRODUCAO_SERIE,
    TIPO_PRODUCAO_STD,
    normalize_tipo_producao,
    tipo_producao_efetivo,
)
from app.domain.numeros import formatar_percentagem
from app.domain.peca_types import COMPOSTA
from app.repositories.def_peca_repository import DefPecaResumo
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.orcamento_item_custeio_linha_service import (
    ClipboardCusteio,
    EntradasCusteioInvalidas,
    ErroEntradaCusteio,
    OrcamentoItemCusteioLinhaService,
)
from app.services.def_maquina_escalao_area_service import DefMaquinaEscalaoAreaService
from app.services.def_maquina_service import DefMaquinaService
from app.domain.modulo_imagem import (
    copiar_imagem_para_pasta,
    tooltip_imagem_html,
)
from app.services.def_modulo_service import DefModuloService
from app.services.system_setting_service import SystemSettingService
from app.services.def_peca_service import DefPecaService
from app.services.orcamento_item_service import OrcamentoItemService
from app.core.session import app_session
from app.ui.dialogs.custeio_linha_acabamento_dialog import CusteioLinhaAcabamentoDialog
from app.ui.dialogs.guardar_modulo_dialog import (
    GuardarModuloDialog,
    GuardarModuloDialogData,
)
from app.ui.dialogs.importar_modulo_dialog import ImportarModuloDialog
from app.ui.dialogs.custeio_linha_material_dialog import CusteioLinhaMaterialDialog
from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog
from app.ui.dialogs.operacao_manual_dialog import OperacaoManualDialog
from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage
from app.ui.tema import (
    BEGE_AREIA,
    COLUNAS_REALCE_COMPOSTA,
    PLACA_INTEIRA_FUNDO,
    PLACA_INTEIRA_TEXTO,
    cor_zebra,
    estilo_linha_custeio,
)
from app.ui.widgets.breadcrumb import Breadcrumb, BreadcrumbItem
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.colunas_visiveis import ligar_menu_colunas
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.ui.widgets.table_item import criar_item_tabela
from app.utils.formatters import format_currency, format_mm, format_quantity


class CusteioEnterDelegate(QStyledItemDelegate):
    """Delegate that makes Enter/Tab advance within the fast-edit flow while EDITING.

    The default Enter end-edit hint varies across Qt/PySide6 versions (and the
    view's default "move down" can win), so we intercept Enter/Tab in the
    editor's eventFilter, commit + close the editor, and ask the table to advance
    to the next fast-flow editable cell — independent of the close hint.
    """

    def eventFilter(self, editor, event) -> bool:  # noqa: N802 (Qt override)
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key()
            in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab)
            and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)
            tabela = self.parent()
            if isinstance(tabela, CusteioLinhasTable):
                tabela.avancar_celula_editavel()
            return True
        return super().eventFilter(editor, event)


class CusteioLinhasTable(QTableWidget):
    """Costing table with Excel-like editing restricted to a FAST-EDIT FLOW.

    Enter and Tab move only between the fast-flow columns (Descrição livre, QT
    mod, QT und, Comp, Larg, Esp): to the next of those that is EDITABLE on the
    row (skipping the ones read-only there — e.g. QT mod only on a division,
    Comp/Larg only on pieces), wrapping to the FIRST editable fast-flow column of
    the next row (typically "Descrição livre"), and opening its editor. Columns
    outside the flow (Fator série, Ajuste, Mat. default, Excluir*, ...) are never
    visited by Enter/Tab — they stay editable by click only. The flow is resolved
    from the header texts, so it survives a future column reordering. Driven by
    ``CusteioEnterDelegate`` while editing and by ``keyPressEvent`` when a cell is
    merely selected — both consume the event so Qt does not move down. Esc
    cancels and Shift+Tab keeps Qt's default (move left).
    """

    # Ordered set of fast-edit columns (by HEADER text, resolved to indices).
    FAST_FLOW_HEADERS = (
        "Descrição livre",
        "QT mod",
        "QT und",
        "Comp",
        "Larg",
        "Esp",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # The delegate drives the Enter/Tab-advance behaviour while editing.
        self.setItemDelegate(CusteioEnterDelegate(self))

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Enter/Tab on a selected (not editing) cell advances within the flow."""
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Tab,
        ) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.avancar_celula_editavel()
            event.accept()
            return
        super().keyPressEvent(event)

    def avancar_celula_editavel(self) -> None:
        """Open the editor of the next fast-flow editable cell."""
        proxima = self._proxima_celula_editavel(
            self.currentRow(), self.currentColumn()
        )
        if proxima is not None:
            QTimer.singleShot(0, lambda rc=proxima: self._editar_celula(*rc))

    def _colunas_fluxo_rapido(self) -> list[int]:
        """Column indices of the fast-edit flow, ordered left-to-right.

        Resolved from the header texts so it does not break if the columns are
        reordered in the future.
        """
        nomes = set(self.FAST_FLOW_HEADERS)
        indices: list[int] = []
        for col in range(self.columnCount()):
            header = self.horizontalHeaderItem(col)
            if header is not None and header.text() in nomes:
                indices.append(col)
        return indices

    def _celula_editavel(self, row: int, col: int) -> bool:
        item = self.item(row, col)
        return item is not None and bool(item.flags() & Qt.ItemFlag.ItemIsEditable)

    def _proxima_celula_editavel(self, row: int, col: int):
        """Return the next EDITABLE fast-flow cell (right in the row, then wrap).

        Only the fast-flow columns are visited; the search wraps to the first
        editable fast-flow column of the next rows.
        """
        if row < 0 or row >= self.rowCount():
            return None

        fluxo = self._colunas_fluxo_rapido()
        if not fluxo:
            return None

        # Same row: the next fast-flow column to the right that is editable here.
        for c in fluxo:
            if c > col and self._celula_editavel(row, c):
                return row, c

        # Next rows: the first editable fast-flow column.
        for r in range(row + 1, self.rowCount()):
            for c in fluxo:
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

    # Size of the module thumbnail shown in the "Módulo" column (phase 8U.4).
    _TAMANHO_MINIATURA_MODULO = 28
    # Slightly shorter row for the discreet separator line (phase 8V.4).
    _ALTURA_SEPARADOR = 16
    # Session-level clipboard for copy/cut of cost lines, shared across page
    # instances so lines can be pasted BETWEEN items (phase 8V.5).
    _clipboard_custeio: ClipboardCusteio | None = None

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
        "Comp",
        "Larg",
        "Esp",
        "QT total",
        "Comp real",
        "Larg real",
        "Esp real",
        "\u00c1rea m\u00b2",
        "Per\u00edmetro ML",
        # ValueSet / materia-prima
        "Chave ValueSet",
        "Prioridade",
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

    # Production times are estimates for planning only — they never enter the cost.
    TEMPO_INFORMATIVO = (
        "Minutos estimados de produção (informativo, não entra no custo)."
    )

    # Header tooltips explaining each column (the formula tooltips are per cell).
    HEADER_TOOLTIPS = {
        "Comp": "Comprimento da peça (editável; aceita expressões).",
        "Larg": "Largura da peça (editável; aceita expressões).",
        "Esp": "Espessura da peça (normalmente vem do material).",
        "QT mod": "Cadeia de quantidades (módulos × peça × componente), ex.: "
        "\"3 x 3 x 1\". Só editável na linha de divisão (nº de módulos do bloco); "
        "nas peças é read-only — a quantidade edita-se em QT und.",
        "QT und": "Quantidade por módulo/peça (editável nas peças). Na linha de "
        "divisão fica vazia (a divisão só comanda os módulos das linhas abaixo).",
        "QT total": "Quantidade total da linha = qt_mod efetivo × qt_und "
        "(× peça principal se for componente). Entra nas áreas, custos e tempos.",
        "Mat. default": "Material da linha, escolhível das opções do ValueSet do "
        "item (dropdown). Placas: troca entre materiais; Ferragens/sistemas: só a "
        "mesma família. ORLA/ACABAMENTO têm tratamento próprio.",
        "Prioridade": "Prioridade exata da opção ValueSet aplicada à linha. "
        "Atualiza ao escolher Mat. default e é preservada ao gravar módulos.",
        "Área m²": "Área por unidade da peça (Comp × Larg).",
        "Perímetro ML": "Perímetro por unidade, em metros lineares.",
        "ML orla fina": "Metros lineares de orla fina (total da linha).",
        "ML orla grossa": "Metros lineares de orla grossa (total da linha).",
        "SPP ML und": "Consumo em metro linear por unidade.",
        "SPP ML total": "Consumo em metro linear total (× QT total).",
        "Custo MP": "Custo da matéria-prima (M2): área × qt × preço × (1+desp).",
        "Custo ferragem": "Custo de ferragens à unidade (UND: Qt × preço × "
        "(1+desp)) ou de materiais ao metro linear (ML: SPP ML total × preço × "
        "(1+desp)). A fórmula no tooltip da célula adapta-se à unidade da linha.",
        "Tempo corte": "Minutos estimados de corte (informativo, não entra no custo).",
        "Tempo orlagem": "Minutos estimados de orlagem (informativo, não entra "
        "no custo).",
        "Tempo CNC": "Minutos estimados de CNC (informativo, não entra no custo).",
        "Tempo montagem": "Minutos estimados de montagem (informativo, não entra "
        "no custo). Os mesmos minutos que geram o Custo mont./manual.",
        "Tempo manual": "Minutos estimados de trabalho manual (informativo, não "
        "entra no custo). Os mesmos minutos que geram o Custo mont./manual.",
        "Tempo setup": "Minutos estimados de setup das operações (informativo, "
        "não entra no custo).",
        "Custo orla fina": "Custo da orla fina: ML × preço/ml.",
        "Custo orla grossa": "Custo da orla grossa: ML × preço/ml.",
        "Custo orlas": "Soma do custo das orlas (fina + grossa).",
        "Custo acabamento": "Custo de acabamento: área acab. × preço × (1+desp), por face.",
        "Custo corte": "Custo de corte: perímetro × qt × €/ML + qt × setup.",
        "Custo orlagem": "Custo de orlagem: preço por lado orlado (2 escalões "
        "pela medida do lado; ≤/> limite da máquina) × QT + QT × setup.",
        "Custo CNC": "Custo de CNC por escalão de área (painéis) ou por tempo (ferragens).",
        "Custo mont./manual": "Montagem/manual: (tempo / 60) × custo/hora da máquina.",
        "Custo produção": "Soma da produção (corte + orlagem + CNC + mont./manual) "
        "× fator série (quando definido).",
        "Custo total": "Soma dos custos da linha, respeitando os checks Excluir.",
        "Tipo produção": "Tipo de produção usado nos custos da linha (STD ou "
        "SERIE). Vem do padrão da versão ou da exceção do item — muda-se na "
        "página de Items.",
        "Fator série": "Fator manual que multiplica APENAS o custo de produção "
        "da linha (vazio = 1,00; ex.: 0,90).",
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
        self._biblioteca_pecas: list[DefPecaResumo] = []
        self._selecionados: set[int] = set()
        self._custeio_by_row: dict[int, OrcamentoItemCusteioLinhaResumo] = {}
        self._erros_entrada: list[ErroEntradaCusteio] = []
        self._quantidades_por_linha: dict[int, ResultadoQuantidade] = {}
        self._valueset_opcoes: list = []
        self._chave_tipos: dict[str, str | None] = {}
        self._carregando_tabela = False
        self._tipo_producao_default = TIPO_PRODUCAO_STD
        self._maquinas_por_codigo: dict = {}
        self._maquinas_por_id: dict = {}
        self._escaloes_por_maquina: dict = {}

        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())
        self.cabecalho = BarraCabecalho(self._titulo_cabecalho())

        self.back_button = QPushButton("Voltar aos Items")
        self.back_button.clicked.connect(self._handle_back)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.atualizar_geral)

        self.refresh_library_piece_button = QPushButton("Atualizar peça da biblioteca")
        self.refresh_library_piece_button.setToolTip(
            "Atualiza explicitamente a peça selecionada e os seus associados "
            "a partir do catálogo. As medidas e quantidades da peça no orçamento "
            "são mantidas."
        )
        self.refresh_library_piece_button.setEnabled(False)
        self.refresh_library_piece_button.clicked.connect(
            self.atualizar_peca_da_biblioteca
        )

        self.producao_label = QLabel("")
        self.producao_label.setObjectName("orcamentoItemCusteioProducao")
        self.producao_label.setToolTip(
            "Tipo de produção do item (padrão da versão ou exceção do item). "
            "A alteração faz-se na página de Items do orçamento."
        )

        self.recalc_measures_button = QPushButton("Recalcular Medidas")
        self.recalc_measures_button.clicked.connect(self.recalcular_medidas)

        self.insert_division_button = QPushButton("Inserir Divis\u00e3o")
        self.insert_division_button.clicked.connect(self.inserir_divisao)

        # Auto-hide toggle for the parts library: lives in the button bar (always
        # visible) so hiding the library leaves NO residual strip (phase 8V.2).
        self.toggle_biblioteca_button = QPushButton("Ocultar Biblioteca")
        self.toggle_biblioteca_button.setObjectName(
            "orcamentoItemCusteioToggleBiblioteca"
        )
        self.toggle_biblioteca_button.setToolTip(
            "Ocultar a biblioteca de pe\u00e7as para a tabela ocupar todo o espa\u00e7o."
        )
        self.toggle_biblioteca_button.clicked.connect(self.toggle_biblioteca)

        self.import_module_button = QPushButton("Importar M\u00f3dulo")
        self.import_module_button.setToolTip(
            "Importa um m\u00f3dulo guardado para o fim do custeio deste item "
            "(a estrutura re-avalia contra as vari\u00e1veis e o material do item)."
        )
        self.import_module_button.clicked.connect(self.importar_modulo)

        # Save the selected costing lines as a reusable module (phase 8U.1):
        # only the parametric structure (no material/price). Enabled on selection.
        self.guardar_modulo_button = QPushButton("Guardar como Módulo")
        self.guardar_modulo_button.setToolTip(
            "Guarda as linhas selecionadas como um módulo reutilizável (só a "
            "estrutura — peças, divisões, fórmulas, chave ValueSet e orlas; "
            "sem material nem preço)."
        )
        self.guardar_modulo_button.setEnabled(False)
        self.guardar_modulo_button.clicked.connect(self.guardar_como_modulo)

        # Highlighted, read-only reference price the item carries to the items
        # list (produced cost, unit price and total). Updated on load/Atualizar.
        self.preco_item_label = QLabel("")
        self.preco_item_label.setObjectName("orcamentoItemCusteioPrecoBox")
        self.preco_item_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.preco_item_label.setStyleSheet(
            "QLabel#orcamentoItemCusteioPrecoBox {"
            " border: 1px solid #6c7a89; border-radius: 4px;"
            " padding: 4px 10px; font-weight: bold;"
            " background: #eef3f8; }"
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.back_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.refresh_library_piece_button)
        actions_layout.addWidget(self.producao_label)
        actions_layout.addWidget(self.recalc_measures_button)
        actions_layout.addWidget(self.insert_division_button)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(self.toggle_biblioteca_button)
        actions_layout.addWidget(self.import_module_button)
        actions_layout.addWidget(self.guardar_modulo_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.preco_item_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemCusteioStatus")

        # Auto-hide state for the parts library panel (phase 8V.2).
        self._biblioteca_visivel = True
        self._biblioteca_sizes: list[int] | None = None
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
        # Excel-like resizable columns: the user can drag the column borders.
        # Initial widths are seeded once from the content (see _preencher_tabela).
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        # Small thumbnails in the "Módulo" column (phase 8U.4).
        self.table.setIconSize(QSize(self._TAMANHO_MINIATURA_MODULO, self._TAMANHO_MINIATURA_MODULO))
        self._larguras_iniciais_aplicadas = False
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.itemSelectionChanged.connect(self._atualizar_botao_modulo)
        self.table.itemSelectionChanged.connect(self._atualizar_botao_biblioteca)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_contexto_material)
        self._instalar_atalhos_clipboard()
        # Restaura larguras guardadas; se restaurou, salta o seed por conteúdo.
        if ligar_persistencia_larguras(self.table, "orcamento_item_custeio"):
            self._larguras_iniciais_aplicadas = True
        ligar_menu_colunas(
            self.table,
            "orcamento_item_custeio",
            ocultas_por_defeito=(
                "C\u00f3digo",
                "Descri\u00e7\u00e3o",
                "Chave ValueSet",
                "Prioridade",
            ),
        )

        lines_layout = QVBoxLayout()
        lines_title = QLabel("Linhas de custeio do item")
        lines_title.setObjectName("orcamentoItemCusteioLinesTitle")
        lines_layout.addWidget(lines_title)
        lines_layout.addWidget(self.table, stretch=1)

        center_widget = QWidget()
        center_widget.setLayout(lines_layout)

        # Resizable split between the parts library (left) and the lines table
        # (right): the user can drag the handle to widen the library.
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.addWidget(self.library_panel)
        self.workspace_splitter.addWidget(center_widget)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes([320, 1000])

        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.workspace_splitter)

        custeio_tab = QWidget()
        custeio_tab.setLayout(workspace_layout)

        self.tabs = QTabWidget()
        self.tabs.addTab(custeio_tab, "Custeio")
        self.tabs.addTab(OrcamentoItemValuesetPage(item.id), "ValueSet")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.addWidget(self.breadcrumb)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
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
                item_service = OrcamentoItemService(session)
                item = item_service.get_item_by_id(self.item_id)
                if item is None:
                    self.status_label.setText("Item selecionado nao foi encontrado.")
                    self.table.setRowCount(0)
                    return

                tipo_default = item_service.get_tipo_producao_default(
                    item.orcamento_versao_id
                )
                custeio_service = OrcamentoItemCusteioLinhaService(session)
                linhas = custeio_service.listar_linhas_do_item(self.item_id)
                erros_entrada = custeio_service.validar_entradas_do_item(self.item_id)
                # Cache the item ValueSet options + key types once, for the
                # per-row 'Mat. default' dropdown (filtered by compatibility).
                self._valueset_opcoes = custeio_service.opcoes_valueset_do_item(
                    self.item_id
                )
                self._chave_tipos = custeio_service.tipos_das_chaves()
                self._carregar_tarifas_maquinas(session)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar o custeio do item.")
            return

        self.item = item
        self._tipo_producao_default = tipo_default
        self._update_item_info()
        self._atualizar_producao_label()
        self._preencher_tabela(linhas)
        self._erros_entrada = erros_entrada
        self._aplicar_erros_entrada()

        if self._erros_entrada:
            self.preco_item_label.setText(
                "Preço bloqueado: corrija as entradas assinaladas no custeio."
            )
            self.preco_item_label.setToolTip(
                "O preço não é recalculado enquanto existirem medidas ou "
                "quantidades inválidas."
            )
            self.status_label.setText(self._resumo_erros_entrada())
        else:
            self._atualizar_caixa_preco()

        if not linhas:
            self.status_label.setText("Sem linhas de custeio para este item.")

    def _atualizar_caixa_preco(self) -> None:
        """Recompute and show the item's reference price (on load / Atualizar).

        Recalcula o preço a partir dos custos já gravados nas linhas (sem correr
        o pipeline de custeio) e grava-o — é o valor que o item leva para a lista
        de items. Items sem custeio mostram o preço manual e custo produzido 0.
        """
        versao_id = self.item.orcamento_versao_id
        try:
            with SessionLocal() as session:
                service = OrcamentoItemService(session)
                resultado = service.recalcular_preco_item(self.item_id)
                margens = service.get_margens_versao(versao_id)
                blocos = service.get_blocos_custo_por_item(versao_id).get(self.item_id)
        except (SQLAlchemyError, ValueError):
            self.preco_item_label.setText("Preço do item indisponível.")
            self.preco_item_label.setToolTip("")
            return

        self.preco_item_label.setText(
            f"Custo produzido: {format_currency(resultado.custo_produzido)}"
            f"   |   Preço unitário: {format_currency(resultado.preco_unitario)}"
            f"   |   Preço total (×qt): {format_currency(resultado.preco_total)}"
        )
        self.preco_item_label.setToolTip(
            self._tooltip_preco_item(resultado, margens, blocos)
        )

    def _tooltip_preco_item(self, resultado, margens, blocos) -> str:
        """3-block tooltip with the item price formula and the version margins."""
        if blocos is None:
            return (
                "Preço manual do item (sem linhas de custeio).\n"
                "O preço unitário e total vêm do valor introduzido no item; "
                "o custo produzido é 0."
            )

        def pct(valor) -> str:
            return (formatar_percentagem(valor) or "0%").replace(".", ",")

        substituicao = (
            f"= [{format_currency(blocos.bloco_mp)}×(1+{pct(margens.margem_mp_pct)}) + "
            f"{format_currency(blocos.bloco_producao)}×"
            f"(1+{pct(margens.margem_mao_obra_pct)}) + "
            f"{format_currency(blocos.bloco_acabamento)}×"
            f"(1+{pct(margens.margem_acabamentos_pct)})] "
            f"× (1+{pct(margens.custos_administrativos_pct)} admin) "
            f"× (1+{pct(margens.margem_lucro_pct)} lucro) "
            f"+ ajuste {format_currency(self.item.ajuste_eur)} "
            f"→ unitário {format_currency(resultado.preco_unitario)} × qt "
            f"{format_quantity(self.item.quantidade)} = "
            f"{format_currency(resultado.preco_total)}"
        )
        return self._tooltip_3(
            "Preço de referência do item, calculado dos blocos de custo com as "
            "margens da versão (o valor que o item leva para a lista de items).",
            "Preço = [MP×(1+m.MP) + Prod×(1+m.MO) + Acab×(1+m.Acab)] × (1+admin) "
            "× (1+lucro) + ajuste",
            substituicao,
        )

    def _carregar_tarifas_maquinas(self, session) -> None:
        """Cache the active machines (and CNC tiers) for the tariff tooltips."""
        maquinas = DefMaquinaService(session).listar_maquinas_ativas()
        self._maquinas_por_codigo = {m.codigo: m for m in maquinas}
        self._maquinas_por_id = {m.id: m for m in maquinas}
        escalao_service = DefMaquinaEscalaoAreaService(session)
        self._escaloes_por_maquina = {
            m.id: escalao_service.listar_escaloes_ativos_da_maquina(m.id)
            for m in maquinas
            if (m.tipo or "").upper() == "CNC"
        }

    def _atualizar_producao_label(self) -> None:
        """Refresh the read-only production type label next to Atualizar."""
        excecao = normalize_tipo_producao(self.item.tipo_producao) is not None
        efetivo = tipo_producao_efetivo(
            self.item.tipo_producao, self._tipo_producao_default
        )
        origem = "exceção" if excecao else "padrão"
        self.producao_label.setText(f"Produção: {efetivo} ({origem})")

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
                self._recalcular_item_completo(service)
        except EntradasCusteioInvalidas as error:
            self.carregar()
            self.status_label.setText(str(error))
            return
        except (SQLAlchemyError, ValueError):
            self.carregar()
            self.status_label.setText("Não foi possível atualizar o item.")
            return

        self.carregar()
        self.status_label.setText(
            "Item atualizado (medidas, orlas, custos parciais e custo total "
            "recalculados)."
        )

    def atualizar_peca_da_biblioteca(self) -> None:
        """Explicitly replace one frozen piece snapshot with the current catalog."""
        linha = self._get_linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione uma peça ou um associado.")
            return

        try:
            with SessionLocal() as session:
                analise = OrcamentoItemCusteioLinhaService(
                    session
                ).analisar_atualizacao_da_biblioteca(linha.id)
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(str(error) or "Não foi possível analisar a peça.")
            return

        mensagem = (
            f"Atualizar a peça {analise.peca_codigo} a partir da biblioteca?\n\n"
            f"Associados atuais: {analise.associados_atuais}\n"
            f"Associados configurados agora: {analise.associados_catalogo}\n\n"
            "As medidas, quantidades e alterações locais da linha principal "
            "serão mantidas. Os associados gerados serão reconstruídos."
        )
        if analise.linhas_editadas_localmente:
            mensagem += (
                f"\n\nATENÇÃO: {analise.linhas_editadas_localmente} associado(s) "
                "têm edições locais. Essas edições serão perdidas."
            )

        confirmar = QMessageBox.question(
            self,
            "Atualizar peça da biblioteca",
            mensagem,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoItemCusteioLinhaService(session)
                resultado = service.atualizar_peca_da_biblioteca(
                    linha.id,
                    confirmar_perda_edicoes=bool(
                        analise.linhas_editadas_localmente
                    ),
                )
                self._recalcular_item_completo(service)
        except EntradasCusteioInvalidas as error:
            self.carregar()
            self.status_label.setText(str(error))
            return
        except (SQLAlchemyError, ValueError) as error:
            self.carregar()
            self.status_label.setText(
                str(error) or "Não foi possível atualizar a peça da biblioteca."
            )
            return

        self.carregar()
        mensagem_resultado = (
            f"Peça {resultado.peca_codigo} atualizada: "
            f"{resultado.associados_removidos} associado(s) substituído(s), "
            f"{resultado.associados_criados} criado(s)."
        )
        if resultado.avisos:
            mensagem_resultado += " " + " ".join(resultado.avisos)
        self.status_label.setText(mensagem_resultado)

    def _recalcular_item_completo(self, service) -> None:
        """Run the full costing pipeline for the item (shared by Atualizar and the
        Mat. default dropdown). Delegates to the single service orchestrator."""
        service.recalcular_item_completo(self.item_id)

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

    # --- Import a saved module into the item (phase 8U.2) ---------------------

    def importar_modulo(self) -> None:
        """Open the import dialog and append the chosen module to the costing."""
        utilizador = app_session.current_user
        user_id = utilizador.id if utilizador is not None else None

        try:
            with SessionLocal() as session:
                modulos_utilizador, modulos_globais = DefModuloService(
                    session
                ).listar_modulos_para_dialogo(user_id)
        except SQLAlchemyError:
            self.status_label.setText(
                "Não foi possível carregar os módulos guardados."
            )
            return

        if not modulos_utilizador and not modulos_globais:
            self.status_label.setText("Não há módulos guardados para importar.")
            return

        def carregar_linhas(modulo_id: int):
            try:
                with SessionLocal() as session:
                    com_linhas = DefModuloService(session).obter_com_linhas(modulo_id)
                    return com_linhas.linhas if com_linhas else []
            except SQLAlchemyError:
                return []

        dialog = ImportarModuloDialog(
            self,
            modulos_utilizador=modulos_utilizador,
            modulos_globais=modulos_globais,
            obter_linhas=carregar_linhas,
        )
        if not dialog.exec() or dialog.modulo_id_selecionado is None:
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoItemCusteioLinhaService(session)
                resultado = service.inserir_modulo_no_item(
                    self.item_id, dialog.modulo_id_selecionado
                )
                self._recalcular_item_completo(service)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível importar o módulo.")
            return

        self.carregar()
        mensagem = (
            f"Módulo {resultado.modulo_codigo} importado: "
            f"{resultado.criadas} linha(s)."
        )
        if resultado.avisos:
            mensagem += " " + " ".join(resultado.avisos)
        self.status_label.setText(mensagem)

    # --- Save selection as a reusable module (phase 8U.1) ---------------------

    def _ids_linhas_selecionadas(self) -> list[int]:
        """Return the cost-line ids of the currently selected rows."""
        rows = sorted(idx.row() for idx in self.table.selectionModel().selectedRows())
        return [
            self._custeio_by_row[row].id
            for row in rows
            if row in self._custeio_by_row
        ]

    def _atualizar_botao_modulo(self) -> None:
        """Enable 'Guardar como Módulo' only when lines are selected."""
        self.guardar_modulo_button.setEnabled(bool(self._ids_linhas_selecionadas()))

    def _atualizar_botao_biblioteca(self) -> None:
        """Enable catalog refresh for a library piece or generated child."""
        linha = self._get_linha_selecionada()
        self.refresh_library_piece_button.setEnabled(
            bool(
                linha is not None
                and (linha.def_peca_id is not None or linha.linha_pai_id is not None)
            )
        )

    def _copiar_imagem_modulo(
        self, origem: str | None, codigo: str
    ) -> tuple[str | None, str | None]:
        """Copy the chosen image into the configured module-images folder.

        Returns (caminho_final, aviso). On any problem keeps the original path
        and returns a friendly warning (never raises).
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

    def guardar_como_modulo(self) -> None:
        """Save the selected costing lines as a reusable module."""
        linha_ids = self._ids_linhas_selecionadas()
        if not linha_ids:
            self.status_label.setText("Selecione pelo menos uma linha para guardar.")
            return

        utilizador = app_session.current_user
        user_id = utilizador.id if utilizador is not None else None

        try:
            with SessionLocal() as session:
                modulos_utilizador, modulos_globais = DefModuloService(
                    session
                ).listar_modulos_para_dialogo(user_id)
        except SQLAlchemyError:
            modulos_utilizador, modulos_globais = [], []

        guardado: dict = {}

        def handle_save(dados: GuardarModuloDialogData) -> bool:
            imagem_path, aviso_imagem = self._copiar_imagem_modulo(
                dados.imagem_path, dados.codigo
            )
            try:
                with SessionLocal() as session:
                    service = DefModuloService(session)
                    if dados.modulo_id is not None:
                        resultado = service.substituir_de_linhas_custeio(
                            modulo_id=dados.modulo_id,
                            orcamento_item_id=self.item_id,
                            linha_ids=linha_ids,
                            nome=dados.nome,
                            descricao=dados.descricao,
                            ambito=dados.ambito,
                            user_id=user_id,
                            categoria=dados.categoria,
                            imagem_path=imagem_path,
                        )
                    else:
                        resultado = service.guardar_de_linhas_custeio(
                            orcamento_item_id=self.item_id,
                            linha_ids=linha_ids,
                            codigo=dados.codigo,
                            nome=dados.nome,
                            descricao=dados.descricao,
                            ambito=dados.ambito,
                            user_id=user_id,
                            categoria=dados.categoria,
                            imagem_path=imagem_path,
                        )
            except ValueError as error:
                dialog.set_error(str(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar o módulo.")
                return False

            guardado["resultado"] = resultado
            guardado["substituido"] = dados.modulo_id is not None
            guardado["aviso_imagem"] = aviso_imagem
            return True

        dialog = GuardarModuloDialog(
            self,
            on_save=handle_save,
            num_linhas=len(linha_ids),
            modulos_utilizador=modulos_utilizador,
            modulos_globais=modulos_globais,
        )
        if dialog.exec() and guardado:
            resultado = guardado["resultado"]
            verbo = "substituído" if guardado.get("substituido") else "guardado"
            mensagem = (
                f"Módulo {resultado.modulo.codigo} {verbo} "
                f"({len(resultado.linhas)} linhas)."
            )
            if guardado.get("aviso_imagem"):
                mensagem += " " + guardado["aviso_imagem"]
            self.status_label.setText(mensagem)

    def _coluna_editavel(
        self, header: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> bool:
        """Return True when the given column is editable for the given line."""
        # A separator is purely visual: only its optional free-text label edits.
        if linha.tipo_linha == SEPARADOR:
            return header == "Descrição livre"

        if header in self.EDITABLE_COLUMNS:
            if linha.tipo_linha == OPERACAO_MANUAL:
                # Manual-operation lines have no measures: only the quantity is
                # editable (editing it recomputes the time and cost).
                return header in ("QT mod", "QT und")
            # The QT mod chain is derived: only a division's module count is
            # editable; on pieces/components QT mod is read-only.
            if header == "QT mod":
                return linha.tipo_linha == DIVISAO_INDEPENDENTE
            # The division has no per-unit quantity (it only multiplies below);
            # on pieces/components QT und is where quantities are entered.
            if header == "QT und":
                return linha.tipo_linha != DIVISAO_INDEPENDENTE
            return True  # Comp / Larg / Esp

        # Free-text note: editable on every line (informative; phase 8V.1).
        if header == "Descrição livre":
            return True

        if header == "Fator série":
            return self._linha_calcula_total(linha)

        return False

    def _create_library_panel(self) -> QWidget:
        """Build the parts library panel (search + tree + selection tools).

        The panel is hidden/shown as a whole by ``toggle_biblioteca`` (the toggle
        button lives in the costing button bar), so when hidden it collapses
        completely — no residual strip is left (phase 8V.2).
        """
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        self.library_title = QLabel("Biblioteca de peças")
        self.library_title.setObjectName("orcamentoItemCusteioLibraryTitle")

        self.library_search = CampoPesquisa(placeholder="Pesquisar peça…")
        self.library_search.pesquisa_mudou.connect(self._aplicar_filtro_biblioteca)

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

        layout.addWidget(self.library_title)
        layout.addWidget(self.library_search)
        layout.addWidget(self.tree_biblioteca_pecas, stretch=1)
        layout.addWidget(self.so_selecionados_check)
        layout.addWidget(self.selecionados_label)
        layout.addWidget(self.add_selections_button)

        panel.setLayout(layout)
        # No hard minimum so the splitter can collapse the panel completely.
        panel.setMinimumWidth(0)
        return panel

    def toggle_biblioteca(self) -> None:
        """Fully hide the parts library (table takes all the width), or restore it."""
        if self._biblioteca_visivel:
            # Remember the current widths to restore them later.
            self._biblioteca_sizes = self.workspace_splitter.sizes()
            self.library_panel.setVisible(False)
            total = sum(self.workspace_splitter.sizes()) or 1000
            # Give ALL the space to the table: no residual strip on the left.
            self.workspace_splitter.setSizes([0, total])
            self.toggle_biblioteca_button.setText("Mostrar Biblioteca")
            self.toggle_biblioteca_button.setToolTip(
                "Mostrar novamente a biblioteca de peças."
            )
            self._biblioteca_visivel = False
        else:
            self.library_panel.setVisible(True)
            self.workspace_splitter.setSizes(self._biblioteca_sizes or [320, 1000])
            self.toggle_biblioteca_button.setText("Ocultar Biblioteca")
            self.toggle_biblioteca_button.setToolTip(
                "Ocultar a biblioteca de peças para a tabela ocupar todo o espaço."
            )
            self._biblioteca_visivel = True

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
        termo = self.library_search.texto().strip().lower()
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
            leaf.setToolTip(0, self._biblioteca_tooltip(peca, codigo_orlas))
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

    def _biblioteca_tooltip(self, peca: DefPecaResumo, codigo_orlas: str) -> str:
        """Multiline detail tooltip for a library leaf (the tree column is narrow).

        Uses only the data already on DefPecaResumo; the components line is
        omitted (the resumo carries no component codes — no per-leaf DB query).
        """
        if peca.sem_material:
            tipo = "Peça de serviço (sem material)"
        elif peca.tipo_peca == COMPOSTA:
            tipo = "Composta"
        else:
            tipo = "Simples"

        return "\n".join(
            [
                f"Código: {peca.codigo}",
                f"Nome: {peca.nome}",
                f"Tipo: {tipo}",
                f"Grupo: {peca.grupo or '—'}",
                f"Código de orlas: [{codigo_orlas}]",
                f"Chave ValueSet: {peca.chave_valueset_material or '—'}",
            ]
        )

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
        except ValueError as error:
            self.status_label.setText(str(error))
            QMessageBox.warning(self, "Divisão independente necessária", str(error))
            return
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

    def _update_item_info(self) -> None:
        """Atualiza a barra de cabeçalho (nome do item + dims) e o breadcrumb."""
        self.cabecalho.definir(
            self._titulo_cabecalho(),
            [
                f"Altura: {format_mm(self.item.altura)}",
                f"Largura: {format_mm(self.item.largura)}",
                f"Prof: {format_mm(self.item.profundidade)}",
                f"Qtd: {format_quantity(self.item.quantidade)}",
            ],
        )
        self.breadcrumb.set_items(self._build_breadcrumb_items())

    def _preencher_tabela(self, linhas: list[OrcamentoItemCusteioLinhaResumo]) -> None:
        """Fill the costing lines table, mapping known fields to columns."""
        self._carregando_tabela = True
        try:
            self._custeio_by_row = {}
            self._quantidades_por_linha = self._calcular_quantidades_das_linhas(linhas)
            self.table.setRowCount(len(linhas))

            for row_index, linha in enumerate(linhas):
                self._custeio_by_row[row_index] = linha
                self._preencher_linha(row_index, linha)
        finally:
            self._carregando_tabela = False

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

    def _aplicar_erros_entrada(self) -> None:
        """Highlight invalid persisted inputs after the table has been filled."""
        if not self._erros_entrada:
            return

        row_por_linha_id = {
            linha.id: row for row, linha in self._custeio_by_row.items()
        }
        coluna_por_nome = {
            header: indice for indice, header in enumerate(self.TABLE_HEADERS)
        }
        fundo_erro = QColor("#FDE2E1")
        texto_erro = QColor("#A11A1A")

        for erro in self._erros_entrada:
            row = row_por_linha_id.get(erro.linha_id)
            coluna = coluna_por_nome.get(erro.campo)
            if row is None or coluna is None:
                continue
            item = self.table.item(row, coluna)
            if item is None:
                continue
            item.setBackground(fundo_erro)
            item.setForeground(texto_erro)
            tooltip_atual = item.toolTip().strip()
            item.setToolTip(
                f"{tooltip_atual}\n\n{erro.mensagem}" if tooltip_atual else erro.mensagem
            )

    def _resumo_erros_entrada(self) -> str:
        """Compact validation summary for the page status area."""
        primeiros = "; ".join(erro.mensagem for erro in self._erros_entrada[:2])
        restantes = len(self._erros_entrada) - 2
        if restantes > 0:
            primeiros += f"; e mais {restantes} erro(s)"
        return f"Entradas inválidas: {primeiros}"

    def _calcular_quantidades_das_linhas(
        self, linhas: list[OrcamentoItemCusteioLinhaResumo]
    ) -> dict[int, ResultadoQuantidade]:
        """Map line id -> computed quantity (qt_total + chain) for the display."""
        return calcular_quantidades(
            [
                LinhaQuantidade(
                    id=linha.id,
                    tipo_linha=linha.tipo_linha,
                    qt_mod=linha.qt_mod,
                    qt_und=linha.qt_und,
                    linha_pai_id=linha.linha_pai_id,
                )
                for linha in linhas
            ]
        )

    def _preencher_linha(
        self, row_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Fill one table row from a line resumo (caller guards _carregando_tabela)."""
        if linha.tipo_linha == SEPARADOR:
            self._preencher_linha_separador(row_index, linha)
            self._estilizar_linha(row_index, linha)
            return

        valores = self._linha_para_valores(linha)
        for column_index, header in enumerate(self.TABLE_HEADERS):
            if header == "Mat. default" and self._montar_combo_material(
                row_index, column_index, linha
            ):
                continue
            if header == "Módulo":
                self.table.setItem(
                    row_index, column_index, self._criar_item_modulo(linha)
                )
                continue
            if header in self.EXCLUSAO_COLUMNS:
                item = self._criar_item_exclusao(header, linha)
            else:
                # Formula tooltip on result columns; otherwise the full content
                # (helps narrow text columns).
                tooltip = self._tooltip_formula(header, linha)
                item = criar_item_tabela(valores.get(header, ""), tooltip=tooltip)
                if header == "Mat. default":
                    item.setToolTip(self._tooltip_mat_default(linha))
                if self._coluna_editavel(header, linha):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_index, column_index, item)

        self._estilizar_linha(row_index, linha)
        self._realcar_desp_placa_inteira(row_index, linha)

    def _realcar_desp_placa_inteira(
        self, row_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Highlight the "Desp %" cell of a line under a whole-board adjustment.

        When ``desperdicio_percentagem_original`` is set, the line's waste was
        raised to whole-board figures (Não-Stock): the cell gets a warm-ochre
        highlight and a tooltip showing the original→adjusted waste (phase 8W.2.1).
        """
        if linha.desperdicio_percentagem_original is None:
            return
        try:
            column_index = self.TABLE_HEADERS.index("Desp %")
        except ValueError:
            return
        item = self.table.item(row_index, column_index)
        if item is None:
            return

        item.setBackground(QColor(PLACA_INTEIRA_FUNDO))
        item.setForeground(QColor(PLACA_INTEIRA_TEXTO))
        item.setToolTip(
            "Placa inteira (Nao Stock): % desperdício ajustada de "
            f"{formatar_percentagem(linha.desperdicio_percentagem_original)} para "
            f"{formatar_percentagem(linha.desperdicio_percentagem)} para refletir "
            "a compra de placas inteiras."
        )

    def _estilizar_linha(
        self, row_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Apply the Lança Encanto per-type style to a row (phase 8V.4).

        Presentation only: background/foreground/font + uppercase display of the
        division header (read-only cells only, so the data is never changed).
        Selection still highlights on top (the system selection colour).
        """
        estilo = estilo_linha_custeio(
            linha.tipo_linha, eh_filho=linha.linha_pai_id is not None
        )
        zebra = cor_zebra(row_index)
        fonte_base = self.table.font()

        for column_index, header in enumerate(self.TABLE_HEADERS):
            item = self.table.item(row_index, column_index)
            if item is None:
                continue  # combo cells (Mat. default) keep their own background

            if estilo.fundo is not None:
                fundo = estilo.fundo
            elif estilo.realce_estrutural and header in COLUNAS_REALCE_COMPOSTA:
                fundo = BEGE_AREIA
            else:
                fundo = zebra
            item.setBackground(QColor(fundo))

            if estilo.texto is not None:
                item.setForeground(QColor(estilo.texto))

            if estilo.negrito or estilo.italico:
                fonte = QFont(fonte_base)
                fonte.setBold(estilo.negrito)
                fonte.setItalic(estilo.italico)
                item.setFont(fonte)

            # Uppercase only the read-only cells (never the editable label, so an
            # edit cannot persist an upper-cased value).
            if estilo.maiusculas and not self._coluna_editavel(header, linha):
                texto = item.text()
                if texto:
                    item.setText(texto.upper())

        if linha.tipo_linha == SEPARADOR:
            self.table.setRowHeight(row_index, self._ALTURA_SEPARADOR)

    def _preencher_linha_separador(
        self, row_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Render a separator row: a discrete, mostly-empty, non-editable line.

        No material dropdown, no exclusion checkboxes and no module thumbnail —
        only the type label and an optional free-text label ("Descrição livre",
        the single editable cell). The discreet styling comes in phase 8V.4.
        """
        for column_index, header in enumerate(self.TABLE_HEADERS):
            # Clear any cell widget left over from a previous (non-separator) fill.
            self.table.removeCellWidget(row_index, column_index)
            if header == "Tipo linha":
                texto = get_custeio_linha_type_label(linha.tipo_linha)
            elif header == "Descrição livre":
                texto = linha.descricao_livre or ""
            else:
                texto = ""
            item = criar_item_tabela(texto)
            if header == "Descrição livre":
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_index, column_index, item)

    def _criar_item_modulo(
        self, linha: OrcamentoItemCusteioLinhaResumo
    ) -> QTableWidgetItem:
        """Build the read-only "Módulo" cell: a thumbnail + zoom tooltip.

        Lines without a module image stay empty; if the image cannot be opened a
        discreet placeholder is shown (never raises).
        """
        item = criar_item_tabela("")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        caminho = getattr(linha, "modulo_imagem_path", None)
        if not caminho:
            return item

        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            item.setText("(sem img)")
            item.setToolTip(f"Imagem do módulo não encontrada:\n{caminho}")
            return item

        item.setIcon(
            QIcon(
                pixmap.scaled(
                    self._TAMANHO_MINIATURA_MODULO,
                    self._TAMANHO_MINIATURA_MODULO,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        )
        # Hover zoom: a bigger image rendered from the file path (file:// URL).
        item.setToolTip(tooltip_imagem_html(caminho))
        return item

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
        """Return True when the line computes a total (not division/composite/separator)."""
        return linha.tipo_linha not in (
            DIVISAO_INDEPENDENTE,
            PECA_COMPOSTA,
            SEPARADOR,
        )

    # --- 'Mat. default' dropdown (item ValueSet options per line) -------------

    def _linha_aceita_dropdown_material(
        self, linha: OrcamentoItemCusteioLinhaResumo
    ) -> bool:
        """True for PECA/FERRAGEM lines (incl. components) that carry material."""
        if linha.tipo_linha not in (PECA, FERRAGEM):
            return False
        return not getattr(linha, "sem_material", False)

    def _montar_combo_material(
        self, row_index: int, column_index: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> bool:
        """Place a Mat. default dropdown on the cell when there are options.

        Returns True when a combobox was set (caller skips the text item); False
        leaves the cell as read-only text (with a tooltip explaining why).
        """
        self.table.removeCellWidget(row_index, column_index)
        if not self._linha_aceita_dropdown_material(linha):
            return False

        opcoes = opcoes_valueset_compativeis(
            linha.chave_valueset, self._valueset_opcoes, self._chave_tipos
        )
        if not opcoes:
            return False

        self.table.setCellWidget(
            row_index, column_index, self._criar_combo_material(linha, opcoes)
        )
        return True

    def _criar_combo_material(
        self, linha: OrcamentoItemCusteioLinhaResumo, opcoes: list
    ) -> QComboBox:
        """Build the per-line Mat. default combobox with the compatible options."""
        combo = QComboBox()
        combo.setToolTip(self._tooltip_mat_default(linha))

        atual_id = self._opcao_atual_id(linha, opcoes)
        if atual_id is None:
            # Current material is not one of the options: keep it visible (no-op).
            combo.addItem(f"(atual) {linha.mat_default or '—'}", None)
        for opcao in opcoes:
            combo.addItem(self._label_opcao_material(opcao), opcao.id)

        indice = combo.findData(atual_id) if atual_id is not None else 0
        if indice >= 0:
            combo.setCurrentIndex(indice)
        # Connect AFTER selecting, so the initial set does not fire the handler.
        combo.currentIndexChanged.connect(
            lambda _i, linha_id=linha.id, c=combo: self._on_material_combo_changed(
                linha_id, c
            )
        )
        return combo

    @staticmethod
    def _label_opcao_material(opcao) -> str:
        """Concise label: key, useful description and net price."""
        codigo = opcao.codigo_opcao or opcao.nome_opcao or "—"
        descricao = (
            opcao.descricao_no_orcamento
            or opcao.descricao_materia_prima
            or opcao.descricao
            or codigo
        )
        preco = format_currency(opcao.preco_liquido)
        return f"{opcao.chave} · {descricao} · Pliq {preco or '—'}"

    @staticmethod
    def _opcao_atual_id(linha: OrcamentoItemCusteioLinhaResumo, opcoes: list):
        """Return the option id matching the line's current material, or None."""
        atual = (linha.mat_default or "").strip()
        if not atual:
            return None

        chave = (linha.chave_valueset or "").strip().upper()
        for opcao in opcoes:
            codigo = (opcao.codigo_opcao or opcao.nome_opcao or "").strip()
            if (opcao.chave or "").strip().upper() == chave and codigo == atual:
                return opcao.id
        return None

    def _tooltip_mat_default(self, linha: OrcamentoItemCusteioLinhaResumo) -> str:
        """Tooltip for the Mat. default cell: the rule + the current option."""
        return (
            "Material da linha a partir do ValueSet do item.\n"
            "Placas (MATERIAL): troca entre quaisquer materiais; "
            "Ferragens/sistemas: só a mesma família (mesma chave).\n"
            f"Opção atual: {linha.mat_default or '—'}"
        )

    def _on_material_combo_changed(self, linha_id: int, combo: QComboBox) -> None:
        """Apply the chosen ValueSet option to the line and recompute the costs."""
        if self._carregando_tabela:
            return

        opcao_id = combo.currentData()
        if opcao_id is None:
            return  # "(atual)" placeholder -> no change

        try:
            with SessionLocal() as session:
                service = OrcamentoItemCusteioLinhaService(session)
                service.aplicar_opcao_valueset_na_linha(linha_id, opcao_id)
                # Reuse the full pipeline so every dependent column is consistent.
                self._recalcular_item_completo(service)
            mensagem = "Material aplicado do ValueSet do item (custos recalculados)."
        except (SQLAlchemyError, ValueError):
            mensagem = "Não foi possível aplicar o material selecionado."

        # Reload outside the combo signal (the reload rebuilds/destroys the combo).
        def _recarregar() -> None:
            self.carregar()
            self.status_label.setText(mensagem)

        QTimer.singleShot(0, _recarregar)

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

        # Quantities: the chain (modules × piece × component) and the total.
        if header in ("QT mod", "QT und", "QT total"):
            return self._tooltip_quantidade(header, linha)

        # Measure expressions: rule + formula + substituted value.
        if header == "Comp":
            return self._tooltip_medida("Comprimento", linha.comp, linha.comp_real)
        if header == "Larg":
            return self._tooltip_medida("Largura", linha.larg, linha.larg_real)
        if header == "Esp":
            return self._tooltip_medida("Espessura", linha.esp, linha.esp_real)

        # Evaluated measures (real): the value and its origin.
        if header == "Comp real":
            return self._tooltip_medida_real(
                "Comprimento real", linha.comp, linha.comp_real
            )
        if header == "Larg real":
            return self._tooltip_medida_real("Largura real", linha.larg, linha.larg_real)
        if header == "Esp real":
            return self._tooltip_medida_real("Espessura real", linha.esp, linha.esp_real)

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
            if eh_unidade_ml(linha.unidade):
                return self._tooltip_3(
                    "Ferragem ao metro linear (SPP).",
                    "SPP ML total × preço × (1 + desp)",
                    f"= {format_quantity(linha.consumo_ml_total)} × "
                    f"{format_currency(linha.preco_liquido)} × "
                    f"{format_quantity(fator)} = "
                    f"{format_currency(linha.custo_ferragem)}",
                )
            return self._tooltip_3(
                "Ferragem à unidade.",
                "Qt total × preço × (1 + desp)",
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
            preco, setup = self._tarifas_ml_valores_tooltip(linha, ("CORTE",))
            formula = "Custo corte = perímetro × QT × tarifa €/ML"
            if setup is not None:
                formula += " + QT × setup €/peça"
            return self._tooltip_3(
                "Custo de corte: perímetro da peça cortado na seccionadora, "
                "cobrado ao metro linear, mais movimentação por peça.",
                formula,
                self._com_tarifa(
                    self._substituicao_custo_corte(linha, qt, preco, setup),
                    self._tarifa_ml_tooltip(linha, ("CORTE",)),
                ),
            )
        if header == "Custo orlagem" and linha.custo_orlagem is not None:
            preco_curto, preco_longo, limite, setup = self._tarifas_lado_valores_tooltip(
                linha
            )
            formula = "Custo orlagem = Σ(preço por lado orlado) × QT"
            if setup is not None:
                formula += " + QT × setup €/peça"
            return self._tooltip_3(
                "Custo de orlagem: cada lado orlado da peça é cobrado pelo escalão "
                "da sua medida real, mais movimentação por peça.",
                formula,
                self._com_tarifa(
                    self._substituicao_custo_orlagem_lados(
                        linha, qt, preco_curto, preco_longo, limite, setup
                    ),
                    self._tarifa_lado_tooltip(linha),
                ),
            )
        if header == "Custo CNC" and linha.custo_cnc is not None:
            if getattr(linha, "tipo_linha", None) == FERRAGEM or linha.area_m2 is None:
                return self._tooltip_cnc_tempo(linha, qt)
            escalao = self._descricao_escalao_cnc_tooltip(linha)
            substituicao_cnc = (
                f"= área {format_quantity(linha.area_m2)} m² × QT "
                f"{format_quantity(qt)} → {format_currency(linha.custo_cnc)}"
            )
            if escalao:
                substituicao_cnc = f"{escalao}\n{substituicao_cnc}"
            return self._tooltip_3(
                "Custo de CNC: maquinação cobrada pelo escalão de área da peça, "
                "multiplicada pela quantidade.",
                "Custo CNC = preço do escalão (por área) × QT",
                self._com_tarifa(
                    substituicao_cnc,
                    self._tarifa_cnc_tooltip(linha),
                ),
            )
        if header == "Custo mont./manual" and linha.custo_montagem_manual is not None:
            return self._tooltip_montagem_manual(linha, qt)
        if header == "Custo produção" and linha.custo_producao is not None:
            fator = self._fator_serie_aplicado(linha)
            parciais = (
                f"{format_currency(linha.custo_corte)} + "
                f"{format_currency(linha.custo_orlagem)} + "
                f"{format_currency(linha.custo_cnc)} + "
                f"{format_currency(linha.custo_montagem_manual)}"
            )
            if fator is not None:
                substituicao = (
                    f"= ({parciais}) × fator {format_quantity(fator)} = "
                    f"{format_currency(linha.custo_producao)}"
                )
            else:
                substituicao = f"= {parciais} = {format_currency(linha.custo_producao)}"
            return self._tooltip_3(
                "Custo de produção da peça: soma dos custos de corte, orlagem, CNC "
                "e montagem/manual, multiplicada pelo fator série quando definido.",
                "Custo produção = (corte + orlagem + CNC + mont./manual) × fator série",
                substituicao,
            )
        if header == "Tempo corte" and linha.tempo_corte is not None:
            return self._tooltip_3(
                self.TEMPO_INFORMATIVO,
                "Tempo corte = QT × tempo de corte por peça",
                f"= QT {format_quantity(qt)} → "
                f"{format_quantity(linha.tempo_corte)} min",
            )
        if header == "Tempo orlagem" and linha.tempo_orlagem is not None:
            return self._tooltip_3(
                self.TEMPO_INFORMATIVO,
                "Tempo orlagem = ML de orla × tempo por ML",
                f"= {format_quantity(ml_orla_total)} ml → "
                f"{format_quantity(linha.tempo_orlagem)} min",
            )
        if header == "Tempo CNC" and linha.tempo_cnc is not None:
            qt_calc = qt if qt is not None else Decimal("1")
            minutos_por_peca = linha.tempo_cnc / qt_calc if qt_calc else None
            setup = getattr(linha, "tempo_setup", None)
            nota_setup = (
                f"   (o setup {format_quantity(setup)} min aparece em Tempo setup)"
                if setup
                else ""
            )
            return self._tooltip_3(
                self.TEMPO_INFORMATIVO,
                "Tempo CNC = tempo por peça × QT",
                f"= {format_quantity(minutos_por_peca)} min/peça × QT "
                f"{format_quantity(qt_calc)} = {format_quantity(linha.tempo_cnc)} min"
                f"{nota_setup}",
            )
        if header == "Tempo montagem" and linha.tempo_montagem is not None:
            return self._tooltip_3(
                self.TEMPO_INFORMATIVO,
                "Tempo montagem = QT × tempo de montagem por peça "
                "(os mesmos minutos do Custo mont./manual)",
                f"= QT {format_quantity(qt)} → "
                f"{format_quantity(linha.tempo_montagem)} min",
            )
        if header == "Tempo manual" and linha.tempo_manual is not None:
            return self._tooltip_3(
                self.TEMPO_INFORMATIVO,
                "Tempo manual = QT × tempo manual por peça "
                "(os mesmos minutos do Custo mont./manual)",
                f"= QT {format_quantity(qt)} → "
                f"{format_quantity(linha.tempo_manual)} min",
            )
        if header == "Tempo setup" and linha.tempo_setup is not None:
            return self._tooltip_3(
                self.TEMPO_INFORMATIVO,
                "Tempo setup = soma dos setups das operações",
                f"= {format_quantity(linha.tempo_setup)} min",
            )
        if header == "Tipo produção" and linha.tipo_producao:
            return (
                f"Custos de produção desta linha calculados com tarifas "
                f"{linha.tipo_producao}.\n"
                "O tipo vem do padrão da versão ou da exceção do item (página de "
                "Items)."
            )
        if header == "Fator série" and self._linha_calcula_total(linha):
            return (
                "Fator manual que multiplica APENAS o custo de produção da linha.\n"
                "Vazio = 1,00. Ex.: 0,90 reduz o custo de produção em 10%."
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

    def _fator_serie_aplicado(self, linha) -> Decimal | None:
        """Return the line's fator série when it actually affects the cost."""
        fator = linha.fator_serie if isinstance(linha.fator_serie, Decimal) else None
        if fator is None or fator <= 0:
            return None
        return fator

    def _usar_serie_linha(self, linha) -> bool:
        """Return True when the line's production costs used SERIE tariffs."""
        return normalize_tipo_producao(linha.tipo_producao) == TIPO_PRODUCAO_SERIE

    def _maquina_da_linha_por_tipo(self, linha, tipos: tuple):
        """Resolve a line machine by type from the cached active machines."""
        for codigo in (linha.maquina or "").split(";"):
            maquina = self._maquinas_por_codigo.get(codigo.strip())
            if maquina is not None and (maquina.tipo or "").upper() in tipos:
                return maquina
        return None

    def _tarifas_ml_valores_tooltip(self, linha, tipos: tuple):
        """Return the effective ML price and setup used by the production cost."""
        maquina = self._maquina_da_linha_por_tipo(linha, tipos)
        if maquina is None:
            return None, None
        usar_serie = self._usar_serie_linha(linha)
        preco, _ = escolher_tarifa(
            getattr(maquina, "preco_ml_std", None),
            getattr(maquina, "preco_ml_serie", None),
            usar_serie,
        )
        setup, _ = escolher_tarifa(
            getattr(maquina, "custo_setup_peca_std", None),
            getattr(maquina, "custo_setup_peca_serie", None),
            usar_serie,
        )
        return preco, setup

    def _tarifas_lado_valores_tooltip(self, linha):
        """Return ORLAGEM short/long side tariff, limit and setup for tooltip."""
        maquina = self._maquina_da_linha_por_tipo(linha, ("ORLAGEM",))
        if maquina is None:
            return None, None, Decimal("1500"), None
        usar_serie = self._usar_serie_linha(linha)
        preco_curto, _ = escolher_tarifa(
            getattr(maquina, "preco_lado_curto_std", None),
            getattr(maquina, "preco_lado_curto_serie", None),
            usar_serie,
        )
        preco_longo, _ = escolher_tarifa(
            getattr(maquina, "preco_lado_longo_std", None),
            getattr(maquina, "preco_lado_longo_serie", None),
            usar_serie,
        )
        setup, _ = escolher_tarifa(
            getattr(maquina, "custo_setup_peca_std", None),
            getattr(maquina, "custo_setup_peca_serie", None),
            usar_serie,
        )
        limite = normalizar_numero(getattr(maquina, "limite_lado_mm", None))
        return preco_curto, preco_longo, limite or Decimal("1500"), setup

    def _substituicao_custo_corte(self, linha, qt, preco, setup) -> str:
        """Build the substituted cut-cost breakdown."""
        perimetro = linha.perimetro_ml
        total = linha.custo_corte
        if perimetro is None or preco is None:
            return (
                f"= {format_quantity(perimetro)} ml × {format_quantity(qt)} → "
                f"{format_currency(total)}"
            )

        qt_calc = qt if qt is not None else Decimal("1")
        parcela_ml = perimetro * qt_calc * preco
        formula = (
            f"= (perímetro {format_quantity(perimetro)} ml × QT "
            f"{format_quantity(qt_calc)} × {format_quantity(preco)} €/ML)"
        )
        if setup is None:
            return f"{formula}\n= {format_currency(total)}"

        parcela_setup = qt_calc * setup
        formula += (
            f" + (QT {format_quantity(qt_calc)} × setup "
            f"{format_quantity(setup)} €/peça)"
        )
        return (
            f"{formula}\n"
            f"= {format_currency(parcela_ml)} + {format_currency(parcela_setup)}\n"
            f"= {format_currency(total)}"
        )

    def _substituicao_custo_orlagem_lados(
        self, linha, qt, preco_curto, preco_longo, limite, setup
    ) -> str:
        """Build the substituted edge-side production-cost breakdown."""
        total = linha.custo_orlagem
        if preco_curto is None or preco_longo is None:
            return f"= {format_currency(total)}"

        digitos = digitos_orla(getattr(linha, "codigo_orlas", None))
        if digitos is None or all(digito == 0 for digito in digitos):
            return f"= sem lados orlados → {format_currency(total)}"

        qt_calc = qt if qt is not None else Decimal("1")
        comp = normalizar_numero(getattr(linha, "comp_real", None))
        larg = normalizar_numero(getattr(linha, "larg_real", None))
        medidas = (comp, comp, larg, larg)
        curto = longo = 0
        for digito, medida in zip(digitos, medidas, strict=True):
            if digito not in (ORLA_FINA, ORLA_GROSSA):
                continue
            if medida is None:
                return f"= dados de medida em falta → {format_currency(total)}"
            if medida <= limite:
                curto += 1
            else:
                longo += 1

        if curto == 0 and longo == 0:
            return f"= sem lados orlados → {format_currency(total)}"

        parcela_curto = Decimal(curto) * preco_curto
        parcela_longo = Decimal(longo) * preco_longo
        custo_lados_unit = parcela_curto + parcela_longo
        partes = []
        if longo:
            partes.append(
                f"({longo} lados > {format_quantity(limite)}mm × "
                f"{self._format_euro_compacto(preco_longo)})"
            )
        if curto:
            partes.append(
                f"({curto} lados ≤ {format_quantity(limite)}mm × "
                f"{self._format_euro_compacto(preco_curto)})"
            )
        primeira_linha = (
            f"= {' + '.join(partes)} = {self._format_euro_compacto(custo_lados_unit)}"
        )

        setup_calc = setup or Decimal("0")
        total_setup = qt_calc * setup_calc
        segunda_linha = (
            f"= {self._format_euro_compacto(custo_lados_unit)} × QT "
            f"{format_quantity(qt_calc)}"
        )
        if setup is not None:
            segunda_linha += (
                f" + (QT {format_quantity(qt_calc)} × setup "
                f"{self._format_euro_compacto(setup_calc)})"
            )
        segunda_linha += f" = {self._format_euro_compacto(total)}"
        return (
            f"{primeira_linha}\n"
            f"{segunda_linha}"
        )

    def _escalao_cnc_da_linha(self, linha):
        """Return the CNC area tier selected for the line, or None."""
        maquina = self._maquina_da_linha_por_tipo(linha, ("CNC",))
        if maquina is None:
            return None
        return selecionar_escalao_area(
            self._escaloes_por_maquina.get(maquina.id, []), linha.area_m2
        )

    def _descricao_escalao_cnc_tooltip(self, linha) -> str | None:
        """Describe the CNC tier selected for a line."""
        escalao = self._escalao_cnc_da_linha(linha)
        if escalao is None:
            return None
        return (
            f"Nível {escalao.nivel} "
            f"({self._format_area_limite_cnc(getattr(escalao, 'area_max_m2', None))}) "
            f"— peça com {format_quantity(linha.area_m2)} m²"
        )

    def _format_area_limite_cnc(self, area_max_m2) -> str:
        """Format a CNC tier limit for the tooltip."""
        if area_max_m2 is None:
            return "sem limite"
        try:
            area = (
                area_max_m2
                if isinstance(area_max_m2, Decimal)
                else Decimal(str(area_max_m2))
            )
            area_txt = format(area.quantize(Decimal("0.01")), "f").replace(".", ",")
            return f"até {area_txt} m²"
        except (InvalidOperation, ValueError):
            return f"até {format_quantity(area_max_m2)} m²"

    def _descrever_tarifa(self, valor_std, valor_serie, usar_serie, unidade) -> str | None:
        """Build the "tarifa SERIE/STD ..." note for a tooltip (or None)."""
        valor, fallback = escolher_tarifa(valor_std, valor_serie, usar_serie)
        if valor is None:
            return None
        if usar_serie and fallback:
            return (
                f"tarifa STD {format_currency(valor)}{unidade} "
                "(SERIE não definida — fallback)"
            )
        tipo = TIPO_PRODUCAO_SERIE if usar_serie else TIPO_PRODUCAO_STD
        return f"tarifa {tipo} {format_currency(valor)}{unidade}"

    def _tarifa_ml_tooltip(self, linha, tipos: tuple) -> str | None:
        """Tariff note (€/ML) of the line's cut machine, or None."""
        maquina = self._maquina_da_linha_por_tipo(linha, tipos)
        if maquina is None:
            return None
        return self._descrever_tarifa(
            maquina.preco_ml_std,
            maquina.preco_ml_serie,
            self._usar_serie_linha(linha),
            "/ML",
        )

    def _tarifa_lado_tooltip(self, linha) -> str | None:
        """Tariff note (€/lado) of the line's edging machine, or None."""
        maquina = self._maquina_da_linha_por_tipo(linha, ("ORLAGEM",))
        if maquina is None:
            return None
        usar_serie = self._usar_serie_linha(linha)
        curto, fallback_curto = escolher_tarifa(
            maquina.preco_lado_curto_std,
            maquina.preco_lado_curto_serie,
            usar_serie,
        )
        longo, fallback_longo = escolher_tarifa(
            maquina.preco_lado_longo_std,
            maquina.preco_lado_longo_serie,
            usar_serie,
        )
        if curto is None or longo is None:
            return None
        limite = normalizar_numero(maquina.limite_lado_mm) or Decimal("1500")
        tipo = TIPO_PRODUCAO_SERIE if usar_serie else TIPO_PRODUCAO_STD
        texto = (
            f"tarifa {tipo} {self._format_euro_compacto(curto)}/lado "
            f"≤{format_quantity(limite)}mm · "
            f"{self._format_euro_compacto(longo)}/lado >{format_quantity(limite)}mm"
        )
        if usar_serie and (fallback_curto or fallback_longo):
            texto += " (SERIE não definida — fallback)"
        return texto

    def _tarifa_cnc_tooltip(self, linha) -> str | None:
        """Tariff note (€/peça do escalão) of the line's CNC machine, or None."""
        maquina = self._maquina_da_linha_por_tipo(linha, ("CNC",))
        if maquina is None:
            return None
        escalao = selecionar_escalao_area(
            self._escaloes_por_maquina.get(maquina.id, []), linha.area_m2
        )
        if escalao is None:
            return None
        return self._descrever_tarifa(
            escalao.preco_peca_std,
            escalao.preco_peca_serie,
            self._usar_serie_linha(linha),
            "/peça",
        )

    def _tarifa_cnc_hora_tooltip(self, linha) -> str | None:
        """Tariff note (€/h) of the line's CNC machine, or None."""
        maquina = self._maquina_da_linha_por_tipo(linha, ("CNC",))
        if maquina is None:
            return None
        return self._descrever_tarifa(
            getattr(maquina, "custo_hora", None),
            getattr(maquina, "custo_hora_serie", None),
            self._usar_serie_linha(linha),
            "/h",
        )

    def _tarifa_hora_tooltip(self, linha) -> str | None:
        """Tariff note (€/h) of the line's manual/assembly machine, or None."""
        maquina = None
        if linha.def_maquina_id is not None:
            maquina = self._maquinas_por_id.get(linha.def_maquina_id)
        if maquina is None:
            maquina = self._maquina_da_linha_por_tipo(linha, ("MONTAGEM", "MANUAL"))
        if maquina is None:
            return None
        return self._descrever_tarifa(
            maquina.custo_hora,
            maquina.custo_hora_serie,
            self._usar_serie_linha(linha),
            "/h",
        )

    def _com_tarifa(self, substituicao: str, tarifa: str | None) -> str:
        """Append the tariff note to a tooltip substitution block."""
        if not tarifa:
            return substituicao
        return f"{substituicao}\n{tarifa}"

    @staticmethod
    def _format_euro_compacto(valor) -> str:
        """Format currency without the UI space before the euro sign."""
        return format_currency(valor).replace(" €", "€")

    def _tooltip_cnc_tempo(
        self, linha: OrcamentoItemCusteioLinhaResumo, qt
    ) -> str:
        """3-block tooltip for hardware CNC cost by machine time."""
        custo = linha.custo_cnc
        tempo_variavel = linha.tempo_cnc
        setup = normalizar_numero(getattr(linha, "tempo_setup", None)) or Decimal("0")
        tempo_total = None
        if tempo_variavel is not None:
            tempo_total = tempo_variavel + setup
        elif setup:
            tempo_total = setup
        custo_hora = self._custo_hora_derivado(custo, tempo_total)

        if tempo_variavel is None:
            formula = "Custo CNC = (tempo / 60) × custo/hora da máquina"
            substituicao = (
                f"= tempo / 60 × custo/hora = {format_currency(custo)}"
            )
        elif setup:
            formula = "Custo CNC = (setup + tempo por peça × QT) / 60 × custo/hora"
            qt_calc = qt if qt is not None else Decimal("1")
            minutos_por_peca = tempo_variavel / qt_calc if qt_calc else None
            substituicao = (
                f"= ({format_quantity(setup)} setup + "
                f"{format_quantity(minutos_por_peca)} min/peça × QT "
                f"{format_quantity(qt_calc)}) / 60 × "
                f"{format_currency(custo_hora)}/h\n"
                f"= {format_quantity(tempo_total)} min / 60 × "
                f"{format_quantity(custo_hora)} = {format_currency(custo)}"
            )
        else:
            formula = "Custo CNC = (tempo / 60) × custo/hora da máquina"
            qt_calc = qt if qt is not None else Decimal("1")
            minutos_por_peca = tempo_variavel / qt_calc if qt_calc else None
            substituicao = (
                f"= {format_quantity(minutos_por_peca)} min/peça × QT "
                f"{format_quantity(qt_calc)} = {format_quantity(tempo_variavel)} min\n"
                f"= {format_quantity(tempo_variavel)} / 60 × "
                f"{format_currency(custo_hora)} = {format_currency(custo)}"
            )

        return self._tooltip_3(
            "Custo de CNC por tempo: minutos de maquinação da ferragem, ao custo/hora da máquina CNC.",
            formula,
            self._com_tarifa(
                substituicao,
                self._tarifa_cnc_hora_tooltip(linha),
            ),
        )

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
                self._com_tarifa(
                    f"= {format_quantity(minutos)} × {format_quantity(qt)} / 60 × "
                    f"{format_currency(custo_hora)} = {format_currency(custo)}",
                    self._tarifa_hora_tooltip(linha),
                ),
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
            self._com_tarifa(
                f"= {format_quantity(tempo_total)} min / 60 × "
                f"{format_currency(custo_hora)} = {format_currency(custo)}",
                self._tarifa_hora_tooltip(linha),
            ),
        )

    def _tooltip_quantidade(
        self, header: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> str:
        """3-block tooltip for the quantity columns (QT mod / QT und / QT total).

        Uses the resolved chain (modules × main piece × component) so QT total is
        shown with the effective division quantity, e.g. "3 × 1 × 5 = 15".
        """
        resultado = self._quantidades_por_linha.get(linha.id)

        if linha.tipo_linha == DIVISAO_INDEPENDENTE:
            modulos = resultado.qt_total if resultado is not None else linha.qt_mod
            return self._tooltip_3(
                "Número de módulos do bloco: aplica-se a todas as linhas abaixo "
                "até à próxima divisão independente.",
                "qt_mod efetivo do bloco = nº de módulos da divisão",
                f"= {format_quantity(modulos)} módulos",
            )

        if resultado is None:  # defensive: chain not computed yet
            return self._tooltip_3(
                "Quantidades da linha.",
                "QT total = qt_mod efetivo × qt_und",
                f"= {format_quantity(linha.quantidade)}",
            )

        descricoes = {
            "QT mod": "Cadeia de quantidades: módulos × peça (× componente). "
            "Read-only nas peças; só editável na linha de divisão.",
            "QT und": "Quantidade por módulo/peça (editável). É aqui que se "
            "definem as quantidades (ex.: 5 dobradiças, 2 suportes).",
            "QT total": "Quantidade total da linha (entra nas áreas, custos e "
            "tempos).",
        }
        cadeia = " × ".join(format_quantity(fator) for fator in resultado.cadeia)
        return self._tooltip_3(
            descricoes.get(header, "Quantidades da linha."),
            "QT total = qt_mod efetivo × qt_und (× qt_und composta se componente)",
            f"= {cadeia} = {format_quantity(resultado.qt_total)}",
        )

    def _substituir_variaveis_medida(self, texto: str) -> str:
        """Replace the item variables (H/L/P...) in an expression with their mm values."""
        contexto = construir_contexto_item(
            self.item.altura, self.item.largura, self.item.profundidade
        )

        def _repl(match: "re.Match[str]") -> str:
            valor = contexto.get(match.group(0).upper())
            return format_quantity(valor) if valor is not None else match.group(0)

        return re.sub(r"[A-Za-z_]\w*", _repl, texto)

    def _tooltip_medida(self, label, raw, real) -> str | None:
        """3-block tooltip for a measure cell that holds an expression.

        Shows the (uppercased) expression, the substitution with the item's real
        variable values when present, and the evaluated result in mm
        (e.g. "L/5*2 → 2100/5*2 = 840 mm").
        """
        if real is None:
            return None

        texto = normalizar_variaveis_medida((raw or "").strip())
        tem_variavel = any(c.isalpha() for c in texto)
        tem_operador = any(c in "+-*/()" for c in texto)
        if not texto or not (tem_variavel or tem_operador):
            return None  # plain number: no formula tooltip needed

        meio = ""
        if tem_variavel:
            substituido = self._substituir_variaveis_medida(texto)
            if substituido != texto:
                meio = f" → {substituido}"

        return self._tooltip_3(
            f"{label} da peça: medida avaliada no contexto do item "
            "(H=altura, L=largura, P=profundidade).",
            f"{label} = expressão escrita pelo utilizador",
            f"= {texto}{meio} = {format_mm(real)}",
        )

    def _tooltip_medida_real(self, label, raw, real) -> str | None:
        """3-block tooltip for an evaluated measure (Comp/Larg/Esp real)."""
        if real is None:
            return None

        texto = normalizar_variaveis_medida((raw or "").strip())
        origem = (
            f"avaliado da expressão «{texto}»"
            if texto
            else "herdado (material / medida do item)"
        )
        return self._tooltip_3(
            f"{label}: medida em mm já avaliada, usada nos cálculos da linha.",
            f"{label} = {origem}",
            f"= {format_mm(real)}",
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

        if header == "Fator série":
            self._on_fator_serie_changed(row, column, linha)
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
        descricao_livre = None
        if header == "Descrição livre":
            # On a division the text is its identity (descricao); on every other
            # line it is a free note kept in the dedicated descricao_livre field.
            if linha.tipo_linha == DIVISAO_INDEPENDENTE:
                descricao = novo_valor
            else:
                descricao_livre = novo_valor
        else:
            # Comp/Larg/Esp accept variable expressions: store them with the
            # variable letters uppercased (the evaluator is case-insensitive).
            if header in ("Comp", "Larg", "Esp"):
                novo_valor = normalizar_variaveis_medida(novo_valor)
            valores[self.EDITABLE_COLUMNS[header]] = novo_valor

        try:
            with SessionLocal() as session:
                # Fast inline edit: save only this line; the costs (full pipeline)
                # stay on the Atualizar button. Quantities DO propagate (a division
                # governs the block below; a composite parent's qt_und reaches its
                # components), so qt edits reload the whole table.
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
                    descricao_livre=descricao_livre,
                    propagar_item=False,
                )
        except ValueError as error:
            # Avoid a recursive cellChanged loop: restore only this row while
            # the table signal guard is active.
            self._atualizar_linha_visivel(row, linha)
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self._atualizar_linha_visivel(row, linha)
            self.status_label.setText("Não foi possível atualizar a linha de custeio.")
            return

        if header in ("QT mod", "QT und"):
            # A quantity edit may change other lines (division block / composite
            # components): reload so every QT mod chain / QT total is consistent.
            self.carregar()
            if linha.tipo_linha == DIVISAO_INDEPENDENTE:
                self.status_label.setText("Quantidades do bloco atualizadas.")
            else:
                self.status_label.setText(
                    "Quantidades atualizadas. Use Atualizar para recalcular custos."
                )
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

    def _on_fator_serie_changed(
        self, row: int, column: int, linha: OrcamentoItemCusteioLinhaResumo
    ) -> None:
        """Save an edited fator série and recompute the line's production cost."""
        item = self.table.item(row, column)
        novo_valor = item.text().strip() if item is not None else ""

        try:
            with SessionLocal() as session:
                resumo = OrcamentoItemCusteioLinhaService(
                    session
                ).atualizar_fator_serie_linha(linha.id, novo_valor or None)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText(
                "Fator série inválido (use um número maior que 0; vazio = 1,00)."
            )
            self.carregar()
            return

        if resumo is not None:
            self._atualizar_linha_visivel(row, resumo)
        self.status_label.setText("Fator série atualizado (custo de produção e total).")

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
        return linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR)

    def inserir_separador_linha(self) -> None:
        """Insert a visual separation line below the selected line.

        Never splits a composite piece: if the selection is a composite header or
        a child, the separator goes AFTER the whole block (service rule).
        """
        linha = self._get_linha_selecionada()
        try:
            with SessionLocal() as session:
                OrcamentoItemCusteioLinhaService(session).inserir_separador(
                    self.item_id, linha.id if linha is not None else None
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível inserir a linha de separação.")
            return

        self.carregar()
        if linha is not None and (
            linha.tipo_linha == PECA_COMPOSTA or linha.linha_pai_id is not None
        ):
            self.status_label.setText(
                "Linha de separação inserida após a peça composta "
                "(para não a partir)."
            )
        else:
            self.status_label.setText("Linha de separação inserida.")

    # --- Copy / cut / paste of cost lines (phase 8V.5) ------------------------

    def _instalar_atalhos_clipboard(self) -> None:
        """Bind Ctrl+C / Ctrl+X / Ctrl+V on the table (only when it has focus, so
        cell editors keep their own copy/paste)."""
        for sequencia, handler in (
            (QKeySequence.StandardKey.Copy, self.copiar_linhas),
            (QKeySequence.StandardKey.Cut, self.cortar_linhas),
            (QKeySequence.StandardKey.Paste, self.colar_linhas),
        ):
            atalho = QShortcut(sequencia, self.table)
            atalho.setContext(Qt.ShortcutContext.WidgetShortcut)
            atalho.activated.connect(handler)

    @classmethod
    def _clipboard_tem_conteudo(cls) -> bool:
        return cls._clipboard_custeio is not None and bool(
            cls._clipboard_custeio.linhas
        )

    def copiar_linhas(self) -> None:
        """Copy the selected lines (whole composite blocks) to the clipboard."""
        self._guardar_no_clipboard("COPIAR")

    def cortar_linhas(self) -> None:
        """Cut the selected lines: copied now, source removed on a successful paste."""
        self._guardar_no_clipboard("CORTAR")

    def _guardar_no_clipboard(self, modo: str) -> None:
        ids = self._ids_linhas_selecionadas()
        if not ids:
            self.status_label.setText("Selecione pelo menos uma linha.")
            return
        try:
            with SessionLocal() as session:
                clipboard = OrcamentoItemCusteioLinhaService(
                    session
                ).construir_clipboard(self.item_id, ids, modo)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível copiar as linhas.")
            return

        # Store on the CLASS so it persists across pages (paste between items);
        # a new copy/cut replaces (and thus cancels) any pending cut.
        OrcamentoItemCusteioPage._clipboard_custeio = clipboard
        total = len(clipboard.linhas)
        verbo = "cortada(s)" if modo == "CORTAR" else "copiada(s)"
        self.status_label.setText(
            f"{total} linha(s) {verbo}. Use 'Colar abaixo' (Ctrl+V) para inserir."
        )

    def colar_linhas(self) -> None:
        """Paste the clipboard block below the selected line (never inside a
        composite), then run the full Atualizar pipeline on this item."""
        clipboard = OrcamentoItemCusteioPage._clipboard_custeio
        if clipboard is None or not clipboard.linhas:
            self.status_label.setText("Não há linhas para colar.")
            return

        linha = self._get_linha_selecionada()
        try:
            with SessionLocal() as session:
                service = OrcamentoItemCusteioLinhaService(session)
                resultado = service.colar_clipboard(
                    self.item_id,
                    clipboard,
                    linha.id if linha is not None else None,
                )
                self._recalcular_item_completo(service)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível colar as linhas.")
            return

        # A successful CUT consumes its source lines, so the clipboard is cleared.
        if clipboard.modo == "CORTAR":
            OrcamentoItemCusteioPage._clipboard_custeio = None

        self.carregar()
        mensagem = f"Linhas coladas: {resultado.inseridas}."
        if resultado.cortadas:
            mensagem += f" Linhas cortadas: {resultado.cortadas}."
        self.status_label.setText(mensagem)

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
        menu.addAction("Inserir linha de separação", self.inserir_separador_linha)
        menu.addSeparator()
        menu.addAction("Copiar (Ctrl+C)", self.copiar_linhas)
        menu.addAction("Cortar (Ctrl+X)", self.cortar_linhas)
        acao_colar = menu.addAction("Colar abaixo (Ctrl+V)", self.colar_linhas)
        acao_colar.setEnabled(self._clipboard_tem_conteudo())
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
            except ValueError as error:
                dialog.set_error(str(error))
                return False
            except SQLAlchemyError:
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
            except ValueError as error:
                dialog.set_error(str(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível atualizar o acabamento da linha.")
                return False

            saved = True
            return True

        dialog = CusteioLinhaAcabamentoDialog(linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Acabamento da linha atualizado.")

    def _maquinas_montagem_manual(self):
        """Active MANUAL/MONTAGEM/EMBALAMENTO/CNC machines for the manual dialog."""
        try:
            with SessionLocal() as session:
                maquinas = DefMaquinaService(session).listar_maquinas_ativas()
        except SQLAlchemyError:
            return []
        return [
            m
            for m in maquinas
            if (m.tipo or "").upper() in ("MANUAL", "MONTAGEM", "EMBALAMENTO", "CNC")
        ]

    def inserir_operacao_manual_linha(self) -> None:
        """Open the dialog to add a user-defined manual-operation line."""
        maquinas = self._maquinas_montagem_manual()
        if not maquinas:
            self.status_label.setText(
                "Crie uma máquina MANUAL, MONTAGEM, EMBALAMENTO ou CNC "
                "(Configurações → Máquinas)."
            )
            return

        saved = False
        linha_selecionada = self._get_linha_selecionada()
        apos_linha_id = linha_selecionada.id if linha_selecionada is not None else None

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
                        apos_linha_id=apos_linha_id,
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
            # A division has no piece description: its identifying text lives in
            # ``descricao`` and is shown/edited through the "Descrição livre" cell.
            descricao_col = ""
            descricao_livre = linha.descricao or ""
        else:
            descricao_col = ("  - " + linha.descricao) if nivel else linha.descricao
            # Pieces/hardware/components keep their note in a dedicated field, so
            # it never collides with the piece "Descrição" (phase 8V.1).
            descricao_livre = linha.descricao_livre or ""
        return {
            "Ordem": "" if linha.ordem is None else str(linha.ordem),
            "Tipo linha": self._tipo_linha_label(linha),
            "Código": linha.codigo or "",
            "Descrição livre": descricao_livre,
            "Def. Peça": linha.def_peca_codigo
            or ("" if linha.def_peca_id is None else str(linha.def_peca_id)),
            "Descrição": descricao_col,
            "Linha pai": "" if linha.linha_pai_id is None else str(linha.linha_pai_id),
            "Nível": str(nivel),
            # The "Módulo" column shows a thumbnail (set in _criar_item_modulo),
            # not text.
            "Módulo": "",
            "QT mod": self._valor_qt_mod(linha),
            "QT und": self._valor_qt_und(linha),
            "QT total": format_quantity(linha.quantidade),
            "Comp": self._format_medida_var(linha.comp),
            "Larg": self._format_medida_var(linha.larg),
            "Esp": self._format_medida_var(linha.esp),
            "Comp real": format_quantity(linha.comp_real),
            "Larg real": format_quantity(linha.larg_real),
            "Esp real": format_quantity(linha.esp_real),
            "Área m²": self._format_medida3(linha.area_m2),
            "Perímetro ML": self._format_medida3(linha.perimetro_ml),
            "Chave ValueSet": linha.chave_valueset or "",
            "Prioridade": (
                ""
                if linha.valueset_prioridade is None
                else str(linha.valueset_prioridade)
            ),
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
            "Fator série": format_quantity(linha.fator_serie),
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

    def _tipo_linha_label(self, linha: OrcamentoItemCusteioLinhaResumo) -> str:
        """Return the display-only type label for one costing line."""
        if linha.tipo_linha != OPERACAO_MANUAL:
            return get_custeio_linha_type_label(linha.tipo_linha)

        tipo_maquina = ""
        if linha.def_maquina_id is not None:
            maquina = self._maquinas_por_id.get(linha.def_maquina_id)
            tipo_maquina = (getattr(maquina, "tipo", None) or "").strip().upper()

        labels = {
            "CNC": "Operação CNC",
            "MONTAGEM": "Operação Montagem",
            "EMBALAMENTO": "Operação Embalamento",
        }
        return labels.get(tipo_maquina, "Operação manual")

    def _handle_back(self) -> None:
        """Return to the items page through the optional callback."""
        if self.on_back is not None:
            self.on_back()

    def _build_title(self) -> str:
        """Return the page title for the active item."""
        return f"Custeio do Item: {self._format_item_label(self.item)}"

    def _titulo_cabecalho(self) -> str:
        """Nome legível do item para a barra (1.ª linha da descrição; senão o código/item)."""
        descricao = (self.item.descricao or "").strip()
        if descricao:
            return descricao.splitlines()[0].strip()
        return self._format_item_label(self.item)

    def _build_breadcrumb_items(self) -> list[BreadcrumbItem]:
        """Return breadcrumb items (clic\u00e1veis) for the active item costing page."""
        items: list[BreadcrumbItem] = []
        if self.orcamento_codigo:
            items.append(
                BreadcrumbItem(f"Or\u00e7amento {self.orcamento_codigo}", self._handle_back)
            )
        items.append(
            BreadcrumbItem(f"Item: {self._format_item_label(self.item)}", self._handle_back)
        )
        items.append(BreadcrumbItem("Custeio"))
        return items

    @staticmethod
    def _format_item_label(item: OrcamentoItemResumo) -> str:
        """Return a display label for one item."""
        if item.codigo:
            return f"{item.codigo} - {item.item}"

        return item.item

    def _format_medida_var(self, value) -> str:
        """Display a measure cell (Comp/Larg/Esp) with variables uppercased."""
        if value is None:
            return ""

        return normalizar_variaveis_medida(str(value))

    def _cadeia_quantidade(self, linha: OrcamentoItemCusteioLinhaResumo) -> str:
        """The quantity chain of a line, e.g. "3 x 3 x 1" (or "" when unknown)."""
        resultado = self._quantidades_por_linha.get(linha.id)
        if resultado is None:
            return ""

        return formatar_cadeia(resultado.cadeia)

    def _valor_qt_mod(self, linha: OrcamentoItemCusteioLinhaResumo) -> str:
        """QT mod cell text: the quantity chain (a plain number on manual lines).

        A division shows just its module count (the chain is a single factor) and
        is the only line where QT mod is editable; pieces/components show the full
        derived chain (read-only).
        """
        if linha.tipo_linha == OPERACAO_MANUAL:
            return format_quantity(linha.qt_mod)

        return self._cadeia_quantidade(linha)

    def _valor_qt_und(self, linha: OrcamentoItemCusteioLinhaResumo) -> str:
        """QT und cell text: empty on a division (it only multiplies the block)."""
        if linha.tipo_linha == DIVISAO_INDEPENDENTE:
            return ""

        return format_quantity(linha.qt_und)

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
