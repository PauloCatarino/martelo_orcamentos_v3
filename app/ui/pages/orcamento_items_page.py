"""Budget items tab page."""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.item_types import get_item_type_label
from app.domain.numeros import formatar_percentagem, parse_decimal_humano
from app.domain.precos import (
    BlocosCusto,
    MargensOrcamento,
    ResultadoObjetivo,
    margem_lucro_efetiva_pct,
)
from app.domain.producao_types import (
    TIPO_PRODUCAO_SERIE,
    TIPO_PRODUCAO_STD,
    tipo_producao_efetivo,
)
from app.domain.custeio_simplificado import (
    MODALIDADE_CUSTEIO_SIMPLIFICADO,
    MODALIDADE_CUSTEIO_STANDARD,
)
from app.domain.margens_padrao_types import (
    PERFIL_MARGENS_CLIENTE,
    PERFIL_MARGENS_CLIENTE_FINAL,
    PERFIL_MARGENS_STANDARD,
)
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services.def_margem_padrao_service import DefMargemPadraoService
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_service import (
    CriarOrcamentoItemSimplesData,
    EditarOrcamentoItemSimplesData,
    OrcamentoItemService,
)
from app.services.orcamento_service import OrcamentoService
from app.ui import tema
from app.ui.dialogs.novo_item_dialog import NovoItemDialog, NovoItemDialogData
from app.ui.widgets.breadcrumb import Breadcrumb, BreadcrumbItem
from app.ui.widgets.descricao_delegate import DescricaoItemDelegate
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_mm, format_quantity


class OrcamentoItemsPage(QWidget):
    """Read-only items page for one budget version."""

    TABLE_HEADERS = [
        "Ordem",
        "C\u00f3digo",
        "Tipo",
        "Item",
        "Descri\u00e7\u00e3o",
        "Altura",
        "Largura",
        "Prof",
        "Qtd",
        "Und",
        "Pre\u00e7o Unit\u00e1rio",
        "Pre\u00e7o Total",
        "Ajuste",
        "Custo Produzido",
        "Custo MP",
        "Custo Produ\u00e7\u00e3o",
        "Custo Acabamentos",
        "Margem Lucro Efetiva",
        "Custeio",
        "Produ\u00e7\u00e3o",
    ]

    # Header tooltips: full names for the abbreviated columns and the meaning
    # of the price columns (the formula tooltips are per cell).
    HEADER_TOOLTIPS = {
        "Prof": "Profundidade do item (mm).",
        "Qtd": "Quantidade do item.",
        "Und": "Unidade do item.",
        "Custo Produzido": "Custo total de fabrico do item, sem margens "
        "(MP + orlas + ferragens, produ\u00e7\u00e3o e acabamentos das linhas ativas, "
        "para 1 unidade, respeitando os checks Excluir).",
        "Custo MP": "Bloco de mat\u00e9rias-primas: placas + orlas + ferragens "
        "das linhas ativas do custeio.",
        "Custo Produ\u00e7\u00e3o": "Bloco de produ\u00e7\u00e3o: m\u00e1quinas (corte, orlagem, CNC) "
        "e trabalho manual/montagem das linhas ativas do custeio.",
        "Custo Acabamentos": "Bloco de acabamentos das linhas ativas do custeio.",
        "Ajuste": "Ajuste manual em \u20ac somado ao pre\u00e7o unit\u00e1rio depois "
        "das margens (pode ser negativo). Edit\u00e1vel na c\u00e9lula.",
        "Margem Lucro Efetiva": "(Pre\u00e7o Unit\u00e1rio \u2212 Custo Produzido) "
        "/ Custo Produzido.",
        "Pre\u00e7o Unit\u00e1rio": "Pre\u00e7o calculado dos blocos de custo com as "
        "margens da vers\u00e3o; manual nos items sem custeio.",
        "Pre\u00e7o Total": "Pre\u00e7o Unit\u00e1rio \u00d7 Quantidade do item.",
    }

    OBJETIVO_TOOLTIP = (
        "Resolve as margens da versão para atingir o valor final desejado "
        "(re-aplica a fórmula, sem recalcular custeios).\n"
        "Primeiro ajusta a margem de lucro. Se o objetivo a consumir, fixa-a no "
        "mínimo de 0,1% e reduz as restantes margens por esta ordem: "
        "Matérias-Primas → Mão de Obra → Custos Administrativos "
        "→ Acabamentos."
    )

    PRODUCAO_DEFAULT_TOOLTIP = (
        "Padr\u00e3o de produ\u00e7\u00e3o da vers\u00e3o (STD ou SERIE): aplica-se a todos os items "
        "sem exce\u00e7\u00e3o pr\u00f3pria. Mudar recalcula os custos de produ\u00e7\u00e3o de todos os "
        "items do or\u00e7amento."
    )
    PRODUCAO_ITEM_TOOLTIP = (
        "Produ\u00e7\u00e3o deste item: Padr\u00e3o segue o padr\u00e3o da vers\u00e3o; STD/SERIE define "
        "uma exce\u00e7\u00e3o s\u00f3 para este item. Mudar recalcula s\u00f3 este item."
    )

    def __init__(
        self,
        orcamento_versao_id: int,
        orcamento_codigo: str | None = None,
        on_items_changed: Callable[[], None] | None = None,
        on_open_item_custeio: Callable[[OrcamentoItemResumo], None] | None = None,
        on_voltar_lista: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id
        self.orcamento_codigo = orcamento_codigo
        self.on_items_changed = on_items_changed
        self.on_open_item_custeio = on_open_item_custeio
        self.on_voltar_lista = on_voltar_lista
        self._items_by_row: dict[int, OrcamentoItemResumo] = {}
        self._blocos_por_item: dict[int, BlocosCusto] = {}
        self._margens = MargensOrcamento()
        self._carregando_margens = False
        self._carregando_tabela = False
        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())

        title = QLabel("Items do or\u00e7amento")
        title.setObjectName("orcamentoItemsTitle")

        self.new_button = QPushButton("Novo Item")
        self.new_button.clicked.connect(self.abrir_novo_item)

        self.edit_button = QPushButton("Editar Item")
        self.edit_button.clicked.connect(self.editar_item_selecionado)

        self.item_custeio_button = QPushButton("Custeio do Item")
        self.item_custeio_button.clicked.connect(self.abrir_custeio_item_selecionado)

        self.remove_button = QPushButton("Remover Item")
        self.remove_button.clicked.connect(self.remover_item_selecionado)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_items)

        self._tipo_producao_default = TIPO_PRODUCAO_STD
        self._carregando_producao = False

        self.producao_title_label = QLabel("Produção:")
        self.producao_title_label.setToolTip(self.PRODUCAO_DEFAULT_TOOLTIP)

        self.producao_std_button = QPushButton(TIPO_PRODUCAO_STD)
        self.producao_serie_button = QPushButton(TIPO_PRODUCAO_SERIE)
        estilo_toggle_producao = (
            f"QPushButton {{"
            f" background-color: {tema.BEGE_CLARO};"
            f" color: {tema.CASTANHO_ESCURO};"
            f" border: 1px solid {tema.CINZA_CASTANHO};"
            f" border-radius: 4px; padding: 4px 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {tema.BEGE_AREIA}; }}"
            f"QPushButton:checked {{"
            f" background-color: {tema.CASTANHO_ESCURO}; color: #FFFFFF;"
            f" border: 1px solid {tema.CASTANHO_ESCURO}; }}"
        )
        for botao in (self.producao_std_button, self.producao_serie_button):
            botao.setCheckable(True)
            botao.setToolTip(self.PRODUCAO_DEFAULT_TOOLTIP)
            botao.setStyleSheet(estilo_toggle_producao)

        self.producao_group = QButtonGroup(self)
        self.producao_group.setExclusive(True)
        self.producao_group.addButton(self.producao_std_button)
        self.producao_group.addButton(self.producao_serie_button)
        self.producao_std_button.setChecked(True)
        self.producao_std_button.clicked.connect(
            lambda: self._on_producao_default_clicked(TIPO_PRODUCAO_STD)
        )
        self.producao_serie_button.clicked.connect(
            lambda: self._on_producao_default_clicked(TIPO_PRODUCAO_SERIE)
        )

        # Cria o painel de margens primeiro para os botões "Atualizar Custos",
        # "Perfil" e "Repor Padrão" existirem e poderem ir para esta linha.
        margens_layout = self._criar_painel_margens()

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.item_custeio_button)
        actions_layout.addWidget(self.remove_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addSpacing(16)
        actions_layout.addWidget(self.producao_title_label)
        actions_layout.addWidget(self.producao_std_button)
        actions_layout.addWidget(self.producao_serie_button)
        actions_layout.addStretch()
        # Ações de custeio/perfil movidas da linha das margens para aqui (à
        # direita), para a linha das margens não sair fora do ecrã.
        actions_layout.addWidget(self.atualizar_custos_button)
        actions_layout.addWidget(QLabel("Perfil:"))
        actions_layout.addWidget(self.perfil_margens_combo)
        actions_layout.addWidget(self.repor_padrao_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoItemsStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        for column_index, header in enumerate(self.TABLE_HEADERS):
            header_item = self.table.horizontalHeaderItem(column_index)
            if header_item is None:
                continue
            if header == "Produção":
                header_item.setToolTip(self.PRODUCAO_ITEM_TOOLTIP)
            elif header in self.HEADER_TOOLTIPS:
                header_item.setToolTip(self.HEADER_TOOLTIPS[header])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Only the Ajuste cells carry the ItemIsEditable flag; the rest of the
        # table stays read-only (and double-click keeps opening the edit dialog).
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        # Resizable (Excel-like) columns: the user can drag the borders. Initial
        # widths are seeded once from the content (see _preencher_tabela); after
        # that they stay Interactive and keep the user's manual sizes.
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)
        self.table.cellChanged.connect(self._on_cell_changed)
        # Restore saved widths; if it restored, skip the content-based seed.
        self._larguras_iniciais_aplicadas = ligar_persistencia_larguras(
            self.table, "orcamento_items"
        )
        # Multi-line, formatted "Descrição" cell (title bold, "- " italic,
        # "* " italic green); rows are sized to the content (see _preencher_tabela).
        self.table.setWordWrap(True)
        self.table.setItemDelegateForColumn(
            self.TABLE_HEADERS.index("Descrição"),
            DescricaoItemDelegate(self.table),
        )

        self.items_list_widget = QWidget()
        items_layout = QVBoxLayout()
        items_layout.setContentsMargins(12, 12, 12, 12)
        items_layout.setSpacing(10)
        items_layout.addWidget(self.breadcrumb)
        items_layout.addWidget(title)
        items_layout.addLayout(actions_layout)
        items_layout.addLayout(margens_layout)
        items_layout.addWidget(self.status_label)
        items_layout.addWidget(self.table, stretch=1)
        self.items_list_widget.setLayout(items_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.items_list_widget)

        self.setLayout(layout)
        self.carregar_items()

    def carregar_items(self) -> None:
        """Load budget items into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                # Sync prices with the costing already stored on the lines (light:
                # no full pipeline recompute), so the list reflects the costing
                # without needing the "Atualizar Custos" button.
                item_service.aplicar_precos_da_versao(self.orcamento_versao_id)
                items = item_service.list_items_by_versao(self.orcamento_versao_id)
                tipo_default = item_service.get_tipo_producao_default(
                    self.orcamento_versao_id
                )
                margens = item_service.get_margens_versao(self.orcamento_versao_id)
                perfil_margens = item_service.get_perfil_margens_versao(self.orcamento_versao_id)
                blocos_por_item = item_service.get_blocos_custo_por_item(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os items.")
            return

        self._tipo_producao_default = tipo_default
        self._margens = margens
        self._perfil_margens = perfil_margens
        self._blocos_por_item = blocos_por_item
        self._atualizar_seletor_producao()
        self._atualizar_painel_margens()
        self._preencher_tabela(items)
        self._atualizar_soma_preco(items)

        if not items:
            self.status_label.setText("Sem items para mostrar.")

    def _criar_painel_margens(self) -> QHBoxLayout:
        """Build the 'Margens e Ajustes' panel (percent fields + totals)."""
        titulo = QLabel("Margens e Ajustes:")
        titulo.setToolTip(
            "Margens da versão do orçamento, aplicadas por bloco de custo ao "
            "calcular o preço de cada item. Sair de um campo aplica logo as "
            "margens (sem recalcular custeios)."
        )

        self.margem_lucro_spin = self._criar_spin_margem(
            "Margem de lucro: multiplica o subtotal (depois dos custos "
            "administrativos)."
        )
        self.margem_mp_spin = self._criar_spin_margem(
            "Margem de matérias-primas: multiplica o bloco MP "
            "(placas + orlas + ferragens)."
        )
        self.margem_mao_obra_spin = self._criar_spin_margem(
            "Margem de mão de obra: multiplica o bloco de produção "
            "(corte/orlagem/CNC/montagem/manual)."
        )
        self.margem_acabamentos_spin = self._criar_spin_margem(
            "Margem de acabamentos: multiplica o bloco de acabamentos."
        )
        self.custos_administrativos_spin = self._criar_spin_margem(
            "Custos administrativos: multiplicam a soma dos blocos com margem."
        )

        self.soma_preco_label = QLabel("Soma Preço Final: 0,00 €")
        self.soma_preco_label.setToolTip("Soma do Preço Total de todos os items.")

        self.objetivo_spin = QDoubleSpinBox()
        self.objetivo_spin.setDecimals(2)
        self.objetivo_spin.setRange(0.0, 99_999_999.99)
        self.objetivo_spin.setSuffix(" €")
        self.objetivo_spin.setMaximumWidth(120)
        self.objetivo_spin.setToolTip(
            "Valor final desejado para o orçamento (€). Use o botão ao lado "
            "para resolver as margens que o atingem."
        )

        self.objetivo_button = QPushButton("Ajustar Margens (Objetivo)")
        self.objetivo_button.setToolTip(self.OBJETIVO_TOOLTIP)
        self.objetivo_button.clicked.connect(self.ajustar_margens_objetivo)

        self.atualizar_custos_button = QPushButton("Atualizar Custos")
        self.atualizar_custos_button.setToolTip(
            "Recalcula o custeio completo de todos os items e aplica as "
            "margens: o preço calculado substitui o preço de cada item com "
            "linhas de custeio."
        )
        self.atualizar_custos_button.clicked.connect(self.atualizar_custos)

        self.repor_padrao_button = QPushButton("Repor Padrão")
        self.repor_padrao_button.setToolTip(
            "Substitui as margens desta versão pelo conjunto por defeito "
            "(margens do cliente se existirem, senão do utilizador, senão "
            "Standard) e recalcula os preços."
        )
        self.repor_padrao_button.clicked.connect(self.repor_margens_padrao)

        self.perfil_margens_combo = QComboBox()
        self.perfil_margens_combo.addItem("Standard", PERFIL_MARGENS_STANDARD)
        self.perfil_margens_combo.addItem("Cliente Final", PERFIL_MARGENS_CLIENTE_FINAL)
        self.perfil_margens_combo.addItem("Por Cliente", PERFIL_MARGENS_CLIENTE)
        self.perfil_margens_combo.setToolTip(
            "Perfil a usar quando escolher Repor Padrão. As margens do orçamento permanecem editáveis."
        )
        self.perfil_margens_combo.currentIndexChanged.connect(self._on_perfil_margens_changed)

        layout = QHBoxLayout()
        layout.addWidget(titulo)
        for label, spin in (
            ("Margem Lucro", self.margem_lucro_spin),
            ("Margem Matérias-Primas", self.margem_mp_spin),
            ("Margem Mão de Obra", self.margem_mao_obra_spin),
            ("Margem Acabamentos", self.margem_acabamentos_spin),
            ("Custos Administrativos", self.custos_administrativos_spin),
        ):
            campo_label = QLabel(label + ":")
            campo_label.setToolTip(spin.toolTip())
            layout.addWidget(campo_label)
            layout.addWidget(spin)
        layout.addSpacing(16)
        layout.addWidget(self.soma_preco_label)
        layout.addSpacing(16)
        objetivo_label = QLabel("Atingir Objetivo:")
        objetivo_label.setToolTip(self.objetivo_spin.toolTip())
        layout.addWidget(objetivo_label)
        layout.addWidget(self.objetivo_spin)
        layout.addWidget(self.objetivo_button)
        layout.addStretch()
        # "Atualizar Custos", "Perfil" e "Repor Padrão" ficam na linha de cima
        # (junto aos botões STD/SERIE) — ver _criar_linha_acoes —, para a linha
        # das margens não sair fora do ecrã com a janela maximizada.

        return layout

    def _criar_spin_margem(self, tooltip: str) -> QDoubleSpinBox:
        """Build one percent field of the margins panel."""
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(-100.0, 999.99)
        spin.setSuffix(" %")
        # Caixas compactas: um valor como "15,00 %" cabe em ~78px. Sem este limite
        # o QDoubleSpinBox estica-se e a linha das margens sai fora do ecrã.
        spin.setMaximumWidth(78)
        spin.setToolTip(tooltip)
        spin.editingFinished.connect(self._on_margens_editadas)
        return spin

    def _atualizar_painel_margens(self) -> None:
        """Reflect the version margins on the panel fields."""
        self._carregando_margens = True
        try:
            self.margem_lucro_spin.setValue(float(self._margens.margem_lucro_pct))
            self.margem_mp_spin.setValue(float(self._margens.margem_mp_pct))
            self.margem_mao_obra_spin.setValue(
                float(self._margens.margem_mao_obra_pct)
            )
            self.margem_acabamentos_spin.setValue(
                float(self._margens.margem_acabamentos_pct)
            )
            self.custos_administrativos_spin.setValue(
                float(self._margens.custos_administrativos_pct)
            )
            indice = self.perfil_margens_combo.findData(self._perfil_margens)
            self.perfil_margens_combo.setCurrentIndex(indice if indice >= 0 else 0)
        finally:
            self._carregando_margens = False

    def _atualizar_soma_preco(self, items: list[OrcamentoItemResumo]) -> None:
        """Refresh the 'Soma Preço Final' label from the loaded items."""
        soma = sum(
            (item.preco_total for item in items if item.preco_total is not None),
            Decimal("0"),
        )
        self.soma_preco_label.setText(f"Soma Preço Final: {format_currency(soma)}")
        # Seed the target field with the current total (the button reads it on
        # demand; nothing is applied just by loading).
        self.objetivo_spin.setValue(float(soma))

    def _margens_do_painel(self) -> MargensOrcamento:
        """Read the margins panel into a MargensOrcamento (Decimal, 2 dp)."""

        def valor(spin: QDoubleSpinBox) -> Decimal:
            return Decimal(str(round(spin.value(), 2)))

        return MargensOrcamento(
            margem_lucro_pct=valor(self.margem_lucro_spin),
            margem_mp_pct=valor(self.margem_mp_spin),
            margem_mao_obra_pct=valor(self.margem_mao_obra_spin),
            margem_acabamentos_pct=valor(self.margem_acabamentos_spin),
            custos_administrativos_pct=valor(self.custos_administrativos_spin),
        )

    def _on_margens_editadas(self) -> None:
        """Save the edited margins and re-apply the price formula (fast path)."""
        if self._carregando_margens:
            return

        margens = self._margens_do_painel()
        if margens == self._margens:
            return

        try:
            with SessionLocal() as session:
                resultado = OrcamentoItemService(session).definir_margens_versao(
                    self.orcamento_versao_id, margens
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível aplicar as margens.")
            self.carregar_items()
            return

        self._margens = margens
        self.carregar_items()
        self.status_label.setText(
            f"Margens aplicadas a {resultado.itens_atualizados} item(s); "
            f"{resultado.itens_sem_custeio} sem custeio (preço manual mantido)."
        )
        self._notify_items_changed()

    def atualizar_custos(self) -> None:
        """Recompute every item's costing pipeline and apply the margins."""
        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                items = item_service.list_items_by_versao(self.orcamento_versao_id)
                for item in items:
                    self._recalcular_custeio_do_item(session, item.id)
                resultado = item_service.aplicar_precos_da_versao(
                    self.orcamento_versao_id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar os custos.")
            return

        self.carregar_items()
        self.status_label.setText(
            f"Custos atualizados: preço calculado em {resultado.itens_atualizados} "
            f"item(s); {resultado.itens_sem_custeio} sem custeio (preço manual "
            "mantido)."
        )
        self._notify_items_changed()

    ORIGEM_MARGENS_LABELS = {
        "cliente": "margens do cliente",
        "cliente_final": "margens Cliente Final",
        "standard": "margens Standard",
        "zeros": "zeros (sem registo por defeito ativo)",
    }

    def _on_perfil_margens_changed(self) -> None:
        if self._carregando_margens:
            return
        try:
            with SessionLocal() as session:
                perfil = OrcamentoItemService(session).definir_perfil_margens_versao(
                    self.orcamento_versao_id, self.perfil_margens_combo.currentData()
                )
            self._perfil_margens = perfil
            self.status_label.setText("Perfil de margens guardado. Use Repor Padrão para o aplicar.")
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível guardar o perfil de margens.")

    def repor_margens_padrao(self) -> None:
        """Replace the version margins with the default set and re-price.

        Resolution order: customer margins if they exist, else the current
        user's, else the STANDARD record (zeros when nothing is active).
        """
        response = QMessageBox.question(
            self,
            "Repor Padrão",
            "Substituir as margens desta versão pelo conjunto por defeito?\n"
            "Os preços dos items serão recalculados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                cliente_id = OrcamentoService(session).get_cliente_id_by_versao(
                    self.orcamento_versao_id
                )
                margens, origem = DefMargemPadraoService(
                    session
                ).resolver_margens_perfil(self._perfil_margens, cliente_id)
                resultado = OrcamentoItemService(session).definir_margens_versao(
                    self.orcamento_versao_id, margens
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível repor as margens padrão.")
            return

        self.carregar_items()
        origem_label = self.ORIGEM_MARGENS_LABELS.get(origem, origem)
        self.status_label.setText(
            f"Margens repostas ({origem_label}); preço re-aplicado em "
            f"{resultado.itens_atualizados} item(s)."
        )
        self._notify_items_changed()

    def ajustar_margens_objetivo(self) -> None:
        """Resolve and apply the margins that reach the price target.

        Pure preview first (no write); the warning/unreachable dialogs decide
        whether to apply, then the resolved margins are stored and the formula
        is re-applied (no costing recompute), following the 8T.2 cascade.
        """
        objetivo = Decimal(str(round(self.objetivo_spin.value(), 2)))

        try:
            with SessionLocal() as session:
                resultado = OrcamentoItemService(session).resolver_objetivo_preco(
                    self.orcamento_versao_id, objetivo
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível resolver o objetivo de preço.")
            return

        # Step 1 warning: the target pins the profit margin at its 0.1% floor.
        if resultado.consome_lucro:
            resposta = QMessageBox.question(
                self,
                "Atingir Objetivo",
                "O objetivo consome a margem de lucro. A margem de lucro foi "
                "fixada no mínimo de 0,1% e o ajuste vai continuar descontando "
                "nas outras margens, por esta ordem: Matérias-Primas → Mão de "
                "Obra → Custos Administrativos → Acabamentos.\n\nContinuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                self.status_label.setText("Objetivo cancelado: margens inalteradas.")
                return

        # Final step: unreachable even with every margin at its minimum.
        if not resultado.atingido:
            resposta = QMessageBox.warning(
                self,
                "Objetivo não atingível",
                "Objetivo não atingível: o mínimo possível com margem de lucro "
                f"0,1% é {format_currency(resultado.minimo_possivel)} "
                f"(objetivo: {format_currency(objetivo)}).\n\n"
                "As margens foram colocadas nos mínimos. Aplicar?",
                QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if resposta != QMessageBox.StandardButton.Apply:
                self.status_label.setText("Objetivo cancelado: margens inalteradas.")
                return

        try:
            with SessionLocal() as session:
                aplicado = OrcamentoItemService(session).definir_margens_versao(
                    self.orcamento_versao_id, resultado.margens
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText(
                "Não foi possível aplicar as margens do objetivo."
            )
            self.carregar_items()
            return

        self._margens = resultado.margens
        self.carregar_items()
        self.status_label.setText(
            self._mensagem_objetivo(resultado, objetivo, aplicado.soma_preco_total)
        )
        self._notify_items_changed()

    def _mensagem_objetivo(
        self,
        resultado: ResultadoObjetivo,
        objetivo: Decimal,
        soma_final: Decimal,
    ) -> str:
        """Build the status message after applying a price-target resolution."""
        soma = format_currency(soma_final)
        if not resultado.atingido:
            return (
                "Objetivo não atingível: mínimo possível "
                f"{format_currency(resultado.minimo_possivel)} "
                f"(objetivo {format_currency(objetivo)}). Margens nos mínimos; "
                f"soma final {soma}."
            )
        if resultado.consome_lucro:
            return (
                "Objetivo atingido: margem de lucro no mínimo (0,1%) e margens "
                f"reduzidas em cascata. Soma final: {soma}."
            )
        lucro = self._fmt_pct(resultado.margens.margem_lucro_pct)
        return (
            f"Objetivo atingido: margem de lucro ajustada para {lucro}. "
            f"Soma final: {soma}."
        )

    def _atualizar_seletor_producao(self) -> None:
        """Reflect the version's production default on the STD/SERIE toggle."""
        self._carregando_producao = True
        try:
            serie = self._tipo_producao_default == TIPO_PRODUCAO_SERIE
            self.producao_serie_button.setChecked(serie)
            self.producao_std_button.setChecked(not serie)
        finally:
            self._carregando_producao = False

    def abrir_novo_item(self) -> None:
        """Open the new item dialog and create the item."""
        dialog = NovoItemDialog(self)

        if not dialog.exec():
            return

        form_data = dialog.get_data()

        try:
            with SessionLocal() as session:
                OrcamentoItemService(session).criar_item_simples(
                    CriarOrcamentoItemSimplesData(
                        orcamento_versao_id=self.orcamento_versao_id,
                        codigo=form_data.codigo,
                        tipo_item=form_data.tipo_item,
                        item=form_data.item,
                        descricao=form_data.descricao,
                        altura=form_data.altura,
                        largura=form_data.largura,
                        profundidade=form_data.profundidade,
                        quantidade=form_data.quantidade,
                        unidade=form_data.unidade,
                        preco_unitario=form_data.preco_unitario,
                        preco_manual=form_data.preco_manual,
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel criar o item.")
            return

        self.carregar_items()
        self.status_label.setText("Item criado.")
        self._notify_items_changed()

    def editar_item_selecionado(self) -> None:
        """Edit the currently selected item."""
        item_id = self._get_selected_item_id()
        if item_id is None:
            self.status_label.setText("Selecione um item para editar.")
            return

        gravar_como = False
        try:
            with SessionLocal() as session:
                service = OrcamentoItemService(session)
                item = service.get_item_by_id(item_id)
                if item is None:
                    self.status_label.setText("Item selecionado nao foi encontrado.")
                    return

                dialog = NovoItemDialog(self, item_data=self._dialog_data_from_item(item))
                if not dialog.exec():
                    return

                form_data = dialog.get_data()
                gravar_como = dialog.save_as_requested
                edicao = EditarOrcamentoItemSimplesData(
                    codigo=form_data.codigo,
                    tipo_item=form_data.tipo_item,
                    item=form_data.item,
                    descricao=form_data.descricao,
                    altura=form_data.altura,
                    largura=form_data.largura,
                    profundidade=form_data.profundidade,
                    quantidade=form_data.quantidade,
                    unidade=form_data.unidade,
                    preco_unitario=form_data.preco_unitario,
                    preco_manual=form_data.preco_manual,
                )
                if gravar_como:
                    service.duplicar_item(item_id, edicao)
                else:
                    service.editar_item_simples(item_id, edicao)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText(
                "Nao foi possivel duplicar o item."
                if gravar_como
                else "Nao foi possivel editar o item."
            )
            return

        self.carregar_items()
        self.status_label.setText(
            "Item duplicado (nova cópia editável)." if gravar_como else "Item atualizado."
        )
        self._notify_items_changed()

    def remover_item_selecionado(self) -> None:
        """Remove the currently selected item after confirmation."""
        item_id = self._get_selected_item_id()
        if item_id is None:
            self.status_label.setText("Selecione um item para remover.")
            return

        response = QMessageBox.question(
            self,
            "Remover Item",
            "Tem a certeza que pretende remover este item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                deleted = OrcamentoItemService(session).remover_item(item_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel remover o item.")
            return

        if not deleted:
            self.status_label.setText("Item selecionado nao foi encontrado.")
            return

        self.carregar_items()
        self.status_label.setText("Item removido.")
        self._notify_items_changed()

    def abrir_custeio_item_selecionado(self) -> None:
        """Open costing for the selected item through the optional callback."""
        item = self._get_selected_item()
        if item is None:
            self.status_label.setText("Selecione um item para abrir o custeio.")
            return

        if self.on_open_item_custeio is None:
            self.status_label.setText("Custeio do item indisponivel.")
            return

        self.status_label.clear()
        self.on_open_item_custeio(item)

    def _preencher_tabela(self, items: list[OrcamentoItemResumo]) -> None:
        """Fill the items table."""
        self._items_by_row = {}
        self._carregando_tabela = True
        try:
            self.table.setRowCount(len(items))

            for row_index, item in enumerate(items):
                self._items_by_row[row_index] = item
                producao_efetiva = tipo_producao_efetivo(
                    item.tipo_producao, self._tipo_producao_default
                )
                blocos = self._blocos_por_item.get(item.id)
                values = [
                    str(item.ordem),
                    item.codigo or "",
                    get_item_type_label(item.tipo_item),
                    item.item,
                    item.descricao or "",
                    format_mm(item.altura),
                    format_mm(item.largura),
                    format_mm(item.profundidade),
                    format_quantity(item.quantidade),
                    item.unidade or "",
                    format_currency(item.preco_unitario),
                    format_currency(item.preco_total),
                    format_currency(item.ajuste_eur),
                    format_currency(blocos.custo_produzido) if blocos else "",
                    format_currency(blocos.bloco_mp) if blocos else "",
                    format_currency(blocos.bloco_producao) if blocos else "",
                    format_currency(blocos.bloco_acabamento) if blocos else "",
                    self._format_percentagem(
                        margem_lucro_efetiva_pct(
                            item.preco_unitario,
                            blocos.custo_produzido if blocos else None,
                        )
                    ),
                    item.modalidade_custeio,
                    producao_efetiva,
                ]

                ajuste_column = self.TABLE_HEADERS.index("Ajuste")
                for column_index, value in enumerate(values):
                    header = self.TABLE_HEADERS[column_index]
                    tooltip = self._tooltip_formula(header, item, blocos)
                    # A coluna "Produção" mostra um combo; não pôr texto por baixo.
                    table_item = QTableWidgetItem(
                        "" if header == "Produção" else value
                    )
                    table_item.setBackground(QColor(tema.cor_zebra(row_index)))
                    if tooltip:
                        table_item.setToolTip(tooltip)
                    if item.preco_manual and header in ("Preço Unitário", "Preço Total"):
                        table_item.setBackground(QColor(tema.OCRE_SUAVE))
                        table_item.setForeground(QColor(tema.OCRE_ESCURO))
                        table_item.setToolTip("Preço manual — não vem do custeio.")
                    if column_index == 0:
                        table_item.setData(Qt.ItemDataRole.UserRole, item.id)
                    if column_index != ajuste_column:
                        table_item.setFlags(
                            table_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                        )
                    self.table.setItem(row_index, column_index, table_item)

                self.table.setCellWidget(
                    row_index,
                    self.TABLE_HEADERS.index("Produção"),
                    self._criar_combo_producao(item),
                )
                self.table.setCellWidget(
                    row_index,
                    self.TABLE_HEADERS.index("Custeio"),
                    self._criar_combo_custeio(item),
                )
        finally:
            self._carregando_tabela = False

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and items:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

        # Fit each row's height to its (possibly multi-line) description.
        self.table.resizeRowsToContents()

    def _tooltip_formula(
        self,
        header: str,
        item: OrcamentoItemResumo,
        blocos: BlocosCusto | None,
    ) -> str | None:
        """3-block tooltip (rule, formula, substitution) for the price columns.

        Substitutions show the REAL summands of each block (the parcels carried
        by BlocosCusto), not just the result.
        """
        if header == "Preço Unitário" and blocos is None:
            return "Preço manual: item sem linhas de custeio."
        if blocos is None:
            return None

        if header == "Custo Produzido":
            return self._tooltip_3(
                "Custo total de fabrico do item, sem margens.",
                "Custo Produzido = Custo MP + Custo Produção + Custo Acabamentos",
                f"= {self._fmt_eur(blocos.bloco_mp)} + "
                f"{self._fmt_eur(blocos.bloco_producao)} + "
                f"{self._fmt_eur(blocos.bloco_acabamento)} = "
                f"{self._fmt_eur(blocos.custo_produzido)} €",
            )
        if header == "Custo MP":
            return self._tooltip_3(
                "Bloco de matérias-primas: placas + orlas + ferragens "
                "das linhas ativas.",
                "Custo MP = Σ custo MP + Σ custo orlas + Σ custo ferragem",
                f"= {self._fmt_eur(blocos.parcela_mp)} + "
                f"{self._fmt_eur(blocos.parcela_orlas)} + "
                f"{self._fmt_eur(blocos.parcela_ferragem)} = "
                f"{self._fmt_eur(blocos.bloco_mp)} €",
            )
        if header == "Custo Produção":
            return self._tooltip_3(
                "Bloco de produção: máquinas e trabalho manual.",
                "Custo Produção = Σ corte + Σ orlagem + Σ CNC "
                "+ Σ montagem/manual",
                f"= {self._fmt_eur(blocos.parcela_corte)} + "
                f"{self._fmt_eur(blocos.parcela_orlagem)} + "
                f"{self._fmt_eur(blocos.parcela_cnc)} + "
                f"{self._fmt_eur(blocos.parcela_montagem_manual)} = "
                f"{self._fmt_eur(blocos.bloco_producao)} €",
            )
        if header == "Custo Acabamentos":
            return self._tooltip_3(
                "Bloco de acabamentos das linhas ativas.",
                "Custo Acabamentos = Σ custo acabamento das linhas ativas",
                f"= {self._fmt_eur(blocos.bloco_acabamento)} €",
            )
        if header == "Ajuste":
            return self._tooltip_3(
                "Ajuste manual em € (pode ser negativo), somado ao preço "
                "depois das margens. Editável nesta célula.",
                "Preço Unitário = subtotal × (1+admin) × (1+lucro) + Ajuste",
                f"Ajuste = {self._fmt_eur(item.ajuste_eur)} €",
            )
        if header == "Margem Lucro Efetiva":
            margem = margem_lucro_efetiva_pct(
                item.preco_unitario, blocos.custo_produzido
            )
            if margem is None:
                return None
            return self._tooltip_3(
                "Margem de lucro efetiva do item face ao custo produzido.",
                "Margem = (Preço Unitário − Custo Produzido) / Custo Produzido",
                f"= ({self._fmt_eur(item.preco_unitario)} − "
                f"{self._fmt_eur(blocos.custo_produzido)}) / "
                f"{self._fmt_eur(blocos.custo_produzido)} = "
                f"{self._format_percentagem(margem)}",
            )
        if header == "Preço Unitário":
            margens = self._margens
            return self._tooltip_3(
                "Preço calculado dos blocos de custo com as margens da versão.",
                "Preço = [MP×(1+m.MP) + Prod×(1+m.MO) + Acab×(1+m.Acab)] "
                "× (1+admin) × (1+lucro) + ajuste",
                f"= [{self._fmt_eur(blocos.bloco_mp)}×"
                f"(1+{self._fmt_pct(margens.margem_mp_pct)}) + "
                f"{self._fmt_eur(blocos.bloco_producao)}×"
                f"(1+{self._fmt_pct(margens.margem_mao_obra_pct)}) + "
                f"{self._fmt_eur(blocos.bloco_acabamento)}×"
                f"(1+{self._fmt_pct(margens.margem_acabamentos_pct)})] "
                f"× (1+{self._fmt_pct(margens.custos_administrativos_pct)} admin) "
                f"× (1+{self._fmt_pct(margens.margem_lucro_pct)} lucro) "
                f"+ ajuste {self._fmt_eur(item.ajuste_eur)} = "
                f"{self._fmt_eur(item.preco_unitario)} €",
            )
        if header == "Preço Total":
            return self._tooltip_3(
                "Preço total do item.",
                "Preço Total = Preço Unitário × Qtd",
                f"= {self._fmt_eur(item.preco_unitario)} × "
                f"{format_quantity(item.quantidade)} = "
                f"{self._fmt_eur(item.preco_total)} €",
            )

        return None

    @staticmethod
    def _tooltip_3(descricao: str, formula: str, substituicao: str | None) -> str:
        """Join the three tooltip blocks (rule, formula, substitution)."""
        blocos = [descricao, formula]
        if substituicao:
            blocos.append(substituicao)
        return "\n".join(blocos)

    @staticmethod
    def _fmt_eur(valor: Decimal | None) -> str:
        """Format an amount for tooltip parcels: 2 dp, thousands dot (1.846,05)."""
        numero = valor if valor is not None else Decimal("0")
        texto = f"{numero:,.2f}"  # 1,846.05
        return texto.translate({ord(","): ".", ord("."): ","})

    @staticmethod
    def _fmt_pct(valor: Decimal | None) -> str:
        """Format a margin for the price tooltip: trimmed percent (15% / 2,5%)."""
        if valor is None:
            return "0%"

        return formatar_percentagem(valor).replace(".", ",") or "0%"

    @staticmethod
    def _format_percentagem(valor: Decimal | None) -> str:
        """Format a percentage with 1 decimal and comma (25,3%), or ''.

        Tiny rounding artifacts must read as zero ("0,0%"), never "-0%".
        """
        if valor is None:
            return ""

        arredondado = valor.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if arredondado == 0:
            arredondado = Decimal("0.0")
        return f"{arredondado:.1f}%".replace(".", ",")

    def _on_cell_changed(self, row: int, column: int) -> None:
        """Save an inline-edited Ajuste cell and re-apply the item's price."""
        if self._carregando_tabela:
            return
        if self.TABLE_HEADERS[column] != "Ajuste":
            return

        item = self._items_by_row.get(row)
        if item is None:
            return

        cell = self.table.item(row, column)
        texto = cell.text().strip() if cell is not None else ""

        try:
            ajuste = parse_decimal_humano(texto)
        except ValueError:
            ajuste = None
            mensagem = "Ajuste inválido: use um número (ex.: -5 ou 12,50)."
        else:
            ajuste = ajuste if ajuste is not None else Decimal("0")
            mensagem = None

        if mensagem is None:
            try:
                with SessionLocal() as session:
                    OrcamentoItemService(session).definir_ajuste_item(item.id, ajuste)
                mensagem = "Ajuste do item gravado (preço re-aplicado)."
            except (SQLAlchemyError, ValueError):
                mensagem = "Não foi possível gravar o ajuste do item."

        # Reload outside the cellChanged signal (the reload rebuilds the table).
        def _recarregar() -> None:
            self.carregar_items()
            self.status_label.setText(mensagem)
            self._notify_items_changed()

        QTimer.singleShot(0, _recarregar)

    def _criar_combo_producao(self, item: OrcamentoItemResumo) -> QComboBox:
        """Build the per-item production combo (Padrão / STD / SERIE)."""
        combo = QComboBox()
        combo.setToolTip(self.PRODUCAO_ITEM_TOOLTIP)
        combo.addItem(f"Padrão ({self._tipo_producao_default})", None)
        combo.addItem(TIPO_PRODUCAO_STD, TIPO_PRODUCAO_STD)
        combo.addItem(TIPO_PRODUCAO_SERIE, TIPO_PRODUCAO_SERIE)

        if item.tipo_producao == TIPO_PRODUCAO_STD:
            combo.setCurrentIndex(1)
        elif item.tipo_producao == TIPO_PRODUCAO_SERIE:
            combo.setCurrentIndex(2)
        else:
            combo.setCurrentIndex(0)

        combo.currentIndexChanged.connect(
            lambda _indice, item_id=item.id, c=combo: self._on_producao_item_changed(
                item_id, c
            )
        )
        return combo

    def _criar_combo_custeio(self, item: OrcamentoItemResumo) -> QComboBox:
        """Build the independent Standard/Simplificado selector."""
        combo = QComboBox()
        combo.setToolTip(
            "Simplificado usa tarifas por escalão das peças deste item; "
            "STD/SERIE continua no campo Produção."
        )
        combo.addItem("Standard", MODALIDADE_CUSTEIO_STANDARD)
        combo.addItem("Simplificado", MODALIDADE_CUSTEIO_SIMPLIFICADO)
        combo.setCurrentIndex(1 if item.modalidade_custeio == MODALIDADE_CUSTEIO_SIMPLIFICADO else 0)
        combo.currentIndexChanged.connect(
            lambda _indice, item_id=item.id, c=combo: self._on_custeio_item_changed(item_id, c)
        )
        return combo

    def _on_custeio_item_changed(self, item_id: int, combo: QComboBox) -> None:
        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                item_service.definir_modalidade_custeio_item(item_id, combo.currentData())
                self._recalcular_custeio_do_item(session, item_id)
                item_service.recalcular_preco_item(item_id)
                session.commit()
            mensagem = "Modalidade de custeio atualizada."
        except (SQLAlchemyError, ValueError):
            mensagem = "Não foi possível mudar a modalidade de custeio."

        def _recarregar() -> None:
            self.carregar_items()
            self.status_label.setText(mensagem)
            self._notify_items_changed()
        QTimer.singleShot(0, _recarregar)

    def _on_producao_default_clicked(self, tipo_producao: str) -> None:
        """Save the version's production default and recompute every item."""
        if self._carregando_producao:
            return
        if tipo_producao == self._tipo_producao_default:
            return

        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                item_service.definir_tipo_producao_default(
                    self.orcamento_versao_id, tipo_producao
                )
                items = item_service.list_items_by_versao(self.orcamento_versao_id)
                for item in items:
                    self._recalcular_custeio_do_item(session, item.id)
                item_service.recalcular_total_versao(self.orcamento_versao_id)
                session.commit()
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível mudar o padrão de produção.")
            self.carregar_items()
            return

        self.carregar_items()
        self.status_label.setText(
            f"Padrão de produção: {tipo_producao}. Custos de produção recalculados "
            f"em {len(items)} item(s); as exceções por item foram respeitadas."
        )
        self._notify_items_changed()

    def _on_producao_item_changed(self, item_id: int, combo: QComboBox) -> None:
        """Save one item's production exception and recompute only that item."""
        tipo_producao = combo.currentData()

        try:
            with SessionLocal() as session:
                item_service = OrcamentoItemService(session)
                item_service.definir_tipo_producao_item(item_id, tipo_producao)
                self._recalcular_custeio_do_item(session, item_id)
                item_service.recalcular_total_versao(self.orcamento_versao_id)
                session.commit()
            mensagem = "Produção do item atualizada (custos recalculados)."
        except (SQLAlchemyError, ValueError):
            mensagem = "Não foi possível mudar a produção do item."

        # Reload outside the combo signal (the reload destroys the combo itself).
        def _recarregar() -> None:
            self.carregar_items()
            self.status_label.setText(mensagem)
            self._notify_items_changed()

        QTimer.singleShot(0, _recarregar)

    def _recalcular_custeio_do_item(self, session, item_id: int) -> None:
        """Run the costing Atualizar pipeline for one item (same as the page)."""
        OrcamentoItemCusteioLinhaService(session).recalcular_item_completo(item_id)

    def _get_selected_item_id(self) -> int | None:
        """Return the selected item id from the table."""
        item = self._get_selected_item()
        if item is not None:
            return item.id

        row = self.table.currentRow()
        if row < 0:
            return None

        table_item = self.table.item(row, 0)
        if table_item is None:
            return None

        item_id = table_item.data(Qt.ItemDataRole.UserRole)
        return int(item_id) if item_id is not None else None

    def _get_selected_item(self) -> OrcamentoItemResumo | None:
        """Return the selected item read model from the table."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._items_by_row.get(row)

    def _handle_row_double_click(self, row: int, column: int) -> None:
        """Edit an item when the user double-clicks its row.

        The Ajuste column is the exception: there the double-click opens the
        inline editor instead of the item dialog.
        """
        if self.TABLE_HEADERS[column] == "Ajuste":
            return

        self.table.selectRow(row)
        self.editar_item_selecionado()

    def _notify_items_changed(self) -> None:
        """Notify the parent page that item data changed."""
        if self.on_items_changed is not None:
            self.on_items_changed()

    @staticmethod
    def _format_item_label(item: OrcamentoItemResumo) -> str:
        """Return a short label for the selected item."""
        parts = [item.item.strip()]
        if item.codigo:
            parts.append(item.codigo.strip())

        label = " - ".join(part for part in parts if part)
        return label or f"Item {item.id}"

    def _build_breadcrumb_items(self) -> list:
        """Return breadcrumb items for the items page."""
        items: list = []
        if self.orcamento_codigo:
            items.append(
                BreadcrumbItem(
                    f"Or\u00e7amento {self.orcamento_codigo}",
                    self.on_voltar_lista,
                )
            )

        items.append("Items")
        return items

    def _dialog_data_from_item(self, item: OrcamentoItemResumo) -> NovoItemDialogData:
        """Convert an item read model into dialog data."""
        return NovoItemDialogData(
            codigo=item.codigo,
            item=item.item,
            descricao=item.descricao,
            altura=item.altura,
            largura=item.largura,
            profundidade=item.profundidade,
            quantidade=item.quantidade,
            unidade=item.unidade or "un",
            preco_unitario=item.preco_unitario or Decimal("0"),
            tipo_item=item.tipo_item,
            preco_manual=item.preco_manual,
        )
