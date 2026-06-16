"""Budget (version) reports page (phase 8W.1).

Two read-only tabs for the whole version:
- "Relatório de Orçamento": customer + budget identification + the items table
  with the subtotal / IVA / grand total footer;
- "Resumo de Consumos": the boards/edge-banding/hardware/machines tables built
  from the 8W.0 aggregation (consumption ALWAYS counts, even with "Excluir").

No exports (8W.4), dashboards (8W.3) nor Não-Stock toggle (8W.2) here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.orcamento_item_service import OrcamentoItemService
from app.services.orcamento_service import OrcamentoService
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.ui import tema
from app.ui.widgets.table_item import criar_item_tabela
from app.utils.formatters import (
    format_currency,
    format_mm,
    format_quantity,
    format_version,
)

# Default VAT rate (configurable constant; a per-budget setting can come later).
IVA_PADRAO_PCT = Decimal("23")

# Prominent note: the consumptions are the WHOLE-budget totals (item quantities
# already included) — for purchasing/warehouse.
_NOTA_CONSUMOS_TOPO = (
    "Os consumos são o TOTAL do orçamento (já multiplicados pela quantidade de "
    "cada item) — para aprovisionamento."
)

# The consumption tables include ALL consumed material (even items with Excluir
# active), so the warehouse/purchasing figures are complete.
_NOTA_CONSUMOS = (
    _NOTA_CONSUMOS_TOPO
    + " Incluem TODO o material consumido (m², ml, qt), mesmo quando o item tem "
    "'Excluir MP/Orla/Ferragem/Acabamento/Produção' ativo. As exclusões só "
    "afetam o custo/total do orçamento."
)


@dataclass(frozen=True)
class TotaisRelatorio:
    """Footer totals of the budget report items table."""

    total_qt: Decimal
    subtotal: Decimal
    iva_pct: Decimal
    iva: Decimal
    total_geral: Decimal


def calcular_totais_relatorio(items, iva_pct: Decimal = IVA_PADRAO_PCT) -> TotaisRelatorio:
    """Sum the items' quantity and price, then apply VAT (pure/testable)."""
    total_qt = Decimal("0")
    subtotal = Decimal("0")
    for item in items:
        total_qt += item.quantidade or Decimal("0")
        subtotal += item.preco_total or Decimal("0")
    iva = subtotal * iva_pct / Decimal("100")
    return TotaisRelatorio(
        total_qt=total_qt,
        subtotal=subtotal,
        iva_pct=iva_pct,
        iva=iva,
        total_geral=subtotal + iva,
    )


class OrcamentoRelatoriosPage(QWidget):
    """Reports page for one budget version (all its items)."""

    ITEMS_HEADERS = [
        "Item", "Código", "Descrição", "Altura", "Largura", "Profundidade",
        "Unidade", "Qt", "Preço Unitário", "Preço Total",
    ]
    PLACAS_HEADERS = [
        "Ref", "Descrição", "P.Liq", "Und", "Desp %", "Comp", "Larg", "Esp",
        "Qt.Pla", "Área", "m² Usad", "m² Peças", "C.MP Tot", "C.Placa Usad",
        "Não Stock",
    ]
    ORLAS_HEADERS = ["Ref Orla", "Descr. Mat.", "Esp", "Larg", "ML Tot", "Custo Tot"]
    FERRAGENS_HEADERS = [
        "Ref", "Descrição", "P.Liq", "Und", "Desp %", "Qt", "ML Sup",
        "Custo Und", "Custo Tot",
    ]
    MAQUINAS_HEADERS = [
        "Operação", "Custo Total", "ML Corte", "ML Orlado", "Nº Peças",
    ]

    # 3-block formula tooltips (descrição / fórmula / valores) on the calculated
    # columns; the example values illustrate that item quantities are included.
    PLACAS_TOOLTIPS = {
        "Qt.Pla": (
            "Placas inteiras necessárias (para aprovisionamento).\n"
            "Fórmula: ceil( m² peças × (1 + Desp%) ÷ Área da placa ).\n"
            "Ex.: 6,00 × 1,15 ÷ 5,985 = 1,15 → 2 placas."
        ),
        "Área": (
            "Área de uma placa inteira.\n"
            "Fórmula: (Comp ÷ 1000) × (Larg ÷ 1000).\n"
            "Ex.: 2750 × 1830 mm = 5,0325 m²."
        ),
        "m² Usad": (
            "m² consumidos com desperdício — TOTAL do orçamento.\n"
            "Fórmula: m² peças × (1 + Desp%).\n"
            "Ex.: 6,00 × 1,15 = 6,90 m²."
        ),
        "m² Peças": (
            "Área das peças, JÁ multiplicada pela quantidade de cada item.\n"
            "Fórmula: Σ área × Qt × quantidade do item.\n"
            "Ex.: 1 m² × 3 × 2 items = 6,00 m²."
        ),
        "C.MP Tot": (
            "Custo MP teórico (com % desperdício) — TOTAL do orçamento.\n"
            "Fórmula: Σ custo MP da linha × quantidade do item.\n"
            "Ex.: 20,00 € × 2 items = 40,00 €."
        ),
        "C.Placa Usad": (
            "Custo das placas inteiras a comprar.\n"
            "Fórmula: Qt.Pla × Área da placa × P.Liq.\n"
            "Ex.: 2 × 5,0325 × 5,79 = 58,28 €."
        ),
    }
    ORLAS_TOOLTIPS = {
        "ML Tot": (
            "Metros lineares de orla — TOTAL do orçamento.\n"
            "Fórmula: Σ ML por peça × quantidade do item.\n"
            "Ex.: 2 ml × 3 items = 6,00 ml."
        ),
        "Custo Tot": (
            "Custo da orla — TOTAL do orçamento.\n"
            "Fórmula: Σ custo de orla da linha × quantidade do item."
        ),
    }
    FERRAGENS_TOOLTIPS = {
        "Qt": (
            "Quantidade de ferragens — TOTAL do orçamento.\n"
            "Fórmula: Σ quantidade por unidade × quantidade do item.\n"
            "Ex.: 4 un × 3 items = 12 un."
        ),
        "Custo Tot": (
            "Custo das ferragens — TOTAL do orçamento.\n"
            "Fórmula: Σ custo de ferragem da linha × quantidade do item."
        ),
    }
    MAQUINAS_TOOLTIPS = {
        "Custo Total": (
            "Custo por centro (corte/orlagem/CNC/montagem) — TOTAL do orçamento.\n"
            "Fórmula: Σ custo do centro na linha × quantidade do item."
        ),
        "ML Corte": (
            "Metros lineares de corte (linhas com corte).\n"
            "Fórmula: Σ perímetro × Qt × quantidade do item."
        ),
        "ML Orlado": (
            "Metros lineares orlados (linhas com orlagem).\n"
            "Fórmula: Σ (ML orla fina + grossa) × quantidade do item."
        ),
    }

    def __init__(self, orcamento_versao_id: int, orcamento=None) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id
        self.orcamento = orcamento
        self._iva_pct = IVA_PADRAO_PCT

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoRelatoriosStatus")

        self.tabs = QTabWidget()
        self.tabs.addTab(self._criar_tab_relatorio(), "Relatório de Orçamento")
        self.tabs.addTab(self._criar_tab_consumos(), "Resumo de Consumos")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.tabs, stretch=1)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Auto-refresh whenever the Reports tab becomes visible (phase 8W.1.1)."""
        super().showEvent(event)
        self.carregar()

    # ----- Layout: tab 1 (budget report) -----

    def _criar_tab_relatorio(self) -> QWidget:
        cliente_box = QFormLayout()
        self._cliente_labels: dict[str, QLabel] = {}
        for chave, etiqueta in (
            ("nome", "Nome"),
            ("morada", "Morada"),
            ("email", "Email"),
            ("telefone", "Telefone"),
            ("num_cliente", "Nº Cliente"),
        ):
            label = QLabel("")
            self._cliente_labels[chave] = label
            cliente_box.addRow(etiqueta, label)

        orc_box = QFormLayout()
        self._orc_labels: dict[str, QLabel] = {}
        for chave, etiqueta in (
            ("num_orcamento", "Nº Orçamento"),
            ("versao", "Versão"),
            ("data", "Data"),
            ("obra", "Obra"),
            ("ref_cliente", "Ref. Cliente"),
        ):
            label = QLabel("")
            self._orc_labels[chave] = label
            orc_box.addRow(etiqueta, label)

        cabecalho = QHBoxLayout()
        cabecalho.addWidget(self._caixa_titulo("Dados do Cliente", cliente_box), 1)
        cabecalho.addWidget(
            self._caixa_titulo("Identificação do Orçamento", orc_box), 1
        )

        self.items_table = self._criar_tabela(self.ITEMS_HEADERS)

        self.total_label = QLabel("")
        self.total_label.setObjectName("orcamentoRelatoriosTotais")
        self.total_label.setStyleSheet(
            f"QLabel#orcamentoRelatoriosTotais {{ font-weight: bold; "
            f"color: {tema.CASTANHO_ESCURO}; padding: 4px; }}"
        )
        self.total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        # Update banner: right below the customer data, before the items table.
        self.banner_relatorio = self._criar_banner()

        tab = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(cabecalho)
        layout.addWidget(self.banner_relatorio)
        layout.addWidget(self._titulo_seccao("Items do Orçamento"))
        layout.addWidget(self.items_table, stretch=1)
        layout.addWidget(self.total_label)
        tab.setLayout(layout)
        return tab

    # ----- Layout: tab 2 (consumption summary) -----

    def _criar_tab_consumos(self) -> QWidget:
        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.clicked.connect(self.carregar)

        topo = QHBoxLayout()
        topo.addWidget(self.atualizar_button)
        topo.addStretch()

        # Update banner: right below the Atualizar button, before the boards table.
        self.banner_consumos = self._criar_banner()

        # Prominent note: the consumptions are the WHOLE-budget totals.
        self.nota_consumos = QLabel("ℹ " + _NOTA_CONSUMOS_TOPO)
        self.nota_consumos.setWordWrap(True)
        self.nota_consumos.setToolTip(_NOTA_CONSUMOS)
        self.nota_consumos.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 2px;"
        )

        self.placas_table = self._criar_tabela(
            self.PLACAS_HEADERS, tooltips=self.PLACAS_TOOLTIPS
        )
        self.orlas_table = self._criar_tabela(
            self.ORLAS_HEADERS, tooltips=self.ORLAS_TOOLTIPS
        )
        self.ferragens_table = self._criar_tabela(
            self.FERRAGENS_HEADERS, tooltips=self.FERRAGENS_TOOLTIPS
        )
        self.maquinas_table = self._criar_tabela(
            self.MAQUINAS_HEADERS, tooltips=self.MAQUINAS_TOOLTIPS
        )

        tab = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(topo)
        layout.addWidget(self.banner_consumos)
        layout.addWidget(self.nota_consumos)
        layout.addWidget(self._titulo_seccao("Resumo de Placas"))
        layout.addWidget(self.placas_table, stretch=2)
        layout.addWidget(self._titulo_seccao("Resumo de Orlas"))
        layout.addWidget(self.orlas_table, stretch=1)
        layout.addWidget(self._titulo_seccao("Resumo de Ferragens"))
        layout.addWidget(self.ferragens_table, stretch=2)
        layout.addWidget(self._titulo_seccao("Resumo de Máquinas / MO"))
        layout.addWidget(self.maquinas_table, stretch=1)
        tab.setLayout(layout)
        return tab

    # ----- Widgets helpers -----

    def _criar_banner(self) -> QLabel:
        """A discreet Lança Encanto banner for the 'updated at HH:MM:SS' message."""
        banner = QLabel("")
        banner.setStyleSheet(
            f"QLabel {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; border: 1px solid {tema.CINZA_CASTANHO}; "
            f"border-radius: 4px; padding: 4px 8px; font-weight: bold; }}"
        )
        return banner

    def _titulo_seccao(self, texto: str) -> QLabel:
        label = QLabel(texto)
        label.setStyleSheet(
            f"font-weight: bold; color: {tema.CASTANHO_ESCURO}; padding-top: 6px;"
        )
        return label

    def _caixa_titulo(self, titulo: str, form: QFormLayout) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._titulo_seccao(titulo))
        layout.addLayout(form)
        widget.setLayout(layout)
        return widget

    def _criar_tabela(self, headers, tooltips=None) -> QTableWidget:
        tabela = QTableWidget(0, len(headers))
        tabela.setHorizontalHeaderLabels(headers)
        tabela.verticalHeader().setVisible(False)
        tabela.setAlternatingRowColors(True)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        # Discreet Lança Encanto header style.
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        if tooltips:
            for indice, nome in enumerate(headers):
                item = tabela.horizontalHeaderItem(indice)
                if item is not None and nome in tooltips:
                    item.setToolTip(tooltips[nome])
        return tabela

    # ----- Data -----

    def carregar(self) -> None:
        """Recompute the costing of every item, then load the report data.

        The report reads the costs already stored on the lines, so it must first
        recompute the full costing pipeline of ALL items and apply the version
        prices — otherwise it would show a stale state (phase 8W.1.1).
        """
        try:
            with SessionLocal() as session:
                relatorio = RelatorioConsumosService(session)
                relatorio.recalcular_versao(self.orcamento_versao_id)

                orcamento_service = OrcamentoService(session)
                orcamento = orcamento_service.get_orcamento_by_versao_id(
                    self.orcamento_versao_id
                )
                cliente = orcamento_service.get_cliente_da_versao(
                    self.orcamento_versao_id
                )
                items = OrcamentoItemService(session).list_items_by_versao(
                    self.orcamento_versao_id
                )
                resumo = relatorio.resumo_da_versao(self.orcamento_versao_id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar os relatórios.")
            return

        if orcamento is not None:
            self.orcamento = orcamento

        self._preencher_cliente(cliente)
        self._preencher_identificacao()
        self._preencher_items(items)
        self._preencher_consumos(resumo)

        hora = datetime.now().strftime("%H:%M:%S")
        mensagem = f"Relatórios atualizados às {hora}"
        self.banner_relatorio.setText(mensagem)
        self.banner_consumos.setText(mensagem)
        self.status_label.setText("")

    def _preencher_cliente(self, cliente) -> None:
        nome = self.orcamento.cliente_nome if self.orcamento is not None else ""
        valores = {
            "nome": (cliente.nome if cliente is not None else nome) or "",
            "morada": (cliente.morada if cliente is not None else "") or "",
            "email": (cliente.email if cliente is not None else "") or "",
            "telefone": (cliente.telefone if cliente is not None else "") or "",
            "num_cliente": (cliente.num_cliente if cliente is not None else "") or "",
        }
        for chave, valor in valores.items():
            self._cliente_labels[chave].setText(valor)

    def _preencher_identificacao(self) -> None:
        orc = self.orcamento
        valores = {
            "num_orcamento": (orc.num_orcamento if orc else "") or "",
            "versao": format_version(orc.numero_versao) if orc else "",
            "data": self._format_data(orc.created_at) if orc else "",
            "obra": (orc.obra if orc else "") or "",
            "ref_cliente": (orc.ref_cliente if orc else "") or "",
        }
        for chave, valor in valores.items():
            self._orc_labels[chave].setText(valor)

    def _preencher_items(self, items) -> None:
        self.items_table.setRowCount(0)
        for item in items:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            valores = [
                str(item.ordem),
                item.codigo or "",
                item.descricao or item.item or "",
                format_mm(item.altura),
                format_mm(item.largura),
                format_mm(item.profundidade),
                item.unidade or "",
                format_quantity(item.quantidade),
                format_currency(item.preco_unitario),
                format_currency(item.preco_total),
            ]
            for col, texto in enumerate(valores):
                self.items_table.setItem(row, col, criar_item_tabela(texto))

        totais = calcular_totais_relatorio(items, self._iva_pct)
        self.total_label.setText(
            f"Total Qt: {format_quantity(totais.total_qt)}    |    "
            f"Subtotal: {format_currency(totais.subtotal)}    |    "
            f"IVA ({format_quantity(totais.iva_pct)}%): {format_currency(totais.iva)}"
            f"    |    Total Geral: {format_currency(totais.total_geral)}"
        )

    def _preencher_consumos(self, resumo) -> None:
        self._preencher_placas(resumo.placas)
        self._preencher_orlas(resumo.orlas)
        self._preencher_ferragens(resumo.ferragens)
        self._preencher_maquinas(resumo.maquinas)

    def _preencher_placas(self, placas) -> None:
        self.placas_table.setRowCount(0)
        for placa in placas:
            row = self.placas_table.rowCount()
            self.placas_table.insertRow(row)
            valores = [
                placa.ref_le or "",
                placa.descricao_no_orcamento or "",
                format_currency(placa.pliq),
                placa.unidade or "",
                self._fmt_pct(placa.desp),
                format_mm(placa.comp_mp),
                format_mm(placa.larg_mp),
                format_mm(placa.esp_mp),
                str(placa.qt_placas),
                self._fmt_m2(placa.area_placa),
                self._fmt_m2(placa.m2_consumidos),
                self._fmt_m2(placa.m2_total_pecas),
                format_currency(placa.custo_mp_total),
                format_currency(placa.custo_placa_inteira),
                "Sim" if placa.nao_stock else "Não",
            ]
            for col, texto in enumerate(valores):
                self.placas_table.setItem(row, col, criar_item_tabela(texto))

    def _preencher_orlas(self, orlas) -> None:
        self.orlas_table.setRowCount(0)
        for orla in orlas:
            row = self.orlas_table.rowCount()
            self.orlas_table.insertRow(row)
            valores = [
                orla.ref_orla or "",
                orla.descricao or "",
                f"{format_quantity(orla.espessura)} mm",
                format_mm(orla.largura),
                self._fmt_ml(orla.ml_total),
                format_currency(orla.custo_total),
            ]
            for col, texto in enumerate(valores):
                self.orlas_table.setItem(row, col, criar_item_tabela(texto))

    def _preencher_ferragens(self, ferragens) -> None:
        self.ferragens_table.setRowCount(0)
        for ferragem in ferragens:
            row = self.ferragens_table.rowCount()
            self.ferragens_table.insertRow(row)
            custo_und = (
                ferragem.custo_total / ferragem.qt_total
                if ferragem.qt_total
                else Decimal("0")
            )
            valores = [
                ferragem.ref_le or "",
                ferragem.descricao_no_orcamento or "",
                format_currency(ferragem.pliq),
                ferragem.unidade or "",
                self._fmt_pct(ferragem.desp),
                format_quantity(ferragem.qt_total),
                self._fmt_ml(ferragem.ml),
                format_currency(custo_und),
                format_currency(ferragem.custo_total),
            ]
            for col, texto in enumerate(valores):
                self.ferragens_table.setItem(row, col, criar_item_tabela(texto))

    def _preencher_maquinas(self, maquinas) -> None:
        self.maquinas_table.setRowCount(0)
        for maquina in maquinas:
            row = self.maquinas_table.rowCount()
            self.maquinas_table.insertRow(row)
            valores = [
                maquina.centro,
                format_currency(maquina.custo_total),
                self._fmt_ml(maquina.ml_corte) if maquina.ml_corte else "",
                self._fmt_ml(maquina.ml_orlado) if maquina.ml_orlado else "",
                format_quantity(maquina.num_pecas) if maquina.num_pecas else "",
            ]
            for col, texto in enumerate(valores):
                self.maquinas_table.setItem(row, col, criar_item_tabela(texto))

    # ----- Formatting helpers -----

    @staticmethod
    def _fmt_m2(valor) -> str:
        texto = format_quantity(valor)
        return f"{texto} m²" if texto else ""

    @staticmethod
    def _fmt_ml(valor) -> str:
        texto = format_quantity(valor)
        return f"{texto} ml" if texto else ""

    @staticmethod
    def _fmt_pct(valor) -> str:
        texto = format_quantity(valor)
        return f"{texto} %" if texto else ""

    @staticmethod
    def _format_data(value: datetime | None) -> str:
        if value is None:
            return ""
        return value.strftime("%Y-%m-%d")
