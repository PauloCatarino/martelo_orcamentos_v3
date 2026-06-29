"""Budget (version) reports page (phase 8W.1).

Three read-only tabs for the whole version:
- "Relatório de Orçamento": customer + budget identification + the items table
  with the subtotal / IVA / grand total footer;
- "Resumo de Consumos": the boards/edge-banding/hardware/machines tables built
  from the 8W.0 aggregation (consumption ALWAYS counts, even with "Excluir");
- "Dashboards": four matplotlib bar charts of the same aggregation (phase 8W.3a).

No exports (8W.4) nor pie chart (8W.3b) here yet.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.export_paths import subpasta_versao
from app.domain.relatorio_totais import (
    IVA_PADRAO_PCT,
    TotaisRelatorio,
    calcular_totais_relatorio,
)
from app.services.email_service import (
    carregar_email_config,
    construir_assunto_email,
    construir_corpo_email,
    enviar_email,
    escrever_relatorio_email,
    get_email_log_path,
)
from app.services.orcamento_export_service import OrcamentoExportService
from app.services.orcamento_historico_service import OrcamentoHistoricoService
from app.services.orcamento_item_service import OrcamentoItemService
from app.services.orcamento_pdf_export import REPORTLAB_DISPONIVEL
from app.services.orcamento_service import OrcamentoService
from app.services.plano_corte_service import PlanoCorteService
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.ui import tema
from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.ui.widgets.relatorio_dashboards import DashboardsWidget
from app.ui.widgets.table_item import criar_item_tabela
from app.utils.formatters import (
    format_currency,
    format_mm,
    format_quantity,
    format_version,
)

# IVA_PADRAO_PCT, TotaisRelatorio and calcular_totais_relatorio moved to
# app.domain.relatorio_totais (phase 8W.4.1) and re-imported above so they stay
# importable from this page (existing tests / callers keep working).

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


class OrcamentoRelatoriosPage(QWidget):
    """Reports page for one budget version (all its items)."""

    ITEMS_HEADERS = [
        "Item", "Código", "Descrição", "Altura", "Largura", "Profundidade",
        "Unidade", "Qt", "Preço Unitário", "Preço Total",
    ]
    PLACAS_HEADERS = [
        "Ref", "Descrição", "P.Liq", "Und", "Desp %", "Comp", "Larg", "Esp",
        "Qt.Pla", "Área", "m² Usad", "m² Peças", "C.MP Tot", "C.Placa Usad",
        "Custo no Orç.", "Não Stock",
    ]
    ORLAS_HEADERS = ["Ref Orla", "Descr. Mat.", "Esp", "Larg", "ML Tot", "Custo Tot"]
    FERRAGENS_HEADERS = [
        "Ref", "Descrição", "P.Liq", "Und", "Desp %", "Qt", "ML Sup",
        "Custo Und", "Custo Tot",
    ]
    MAQUINAS_HEADERS = [
        "Operação", "Custo Total", "ML Corte", "ML Orlado", "Nº Peças",
    ]

    # Initial column widths suited to the content (phase 8W.2-UX, Part D);
    # "Descrição" is wide enough to show the full text. Columns stay resizable
    # (Interactive), so the user can still adjust them.
    PLACAS_LARGURAS = {
        "Ref": 80, "Descrição": 240, "P.Liq": 70, "Und": 45, "Desp %": 60,
        "Comp": 60, "Larg": 60, "Esp": 50, "Qt.Pla": 60, "Área": 75,
        "m² Usad": 75, "m² Peças": 75, "C.MP Tot": 80, "C.Placa Usad": 95,
        "Custo no Orç.": 95, "Não Stock": 75,
    }
    ORLAS_LARGURAS = {
        "Ref Orla": 110, "Descr. Mat.": 240, "Esp": 60, "Larg": 60,
        "ML Tot": 80, "Custo Tot": 90,
    }
    FERRAGENS_LARGURAS = {
        "Ref": 90, "Descrição": 240, "P.Liq": 70, "Und": 45, "Desp %": 60,
        "Qt": 60, "ML Sup": 70, "Custo Und": 80, "Custo Tot": 90,
    }
    MAQUINAS_LARGURAS = {
        "Operação": 200, "Custo Total": 100, "ML Corte": 90, "ML Orlado": 90,
        "Nº Peças": 80,
    }

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
        "Custo no Orç.": (
            "Custo que ESTA placa leva ao orçamento.\n"
            "Não-Stock ativo → C.Placa Usad; caso contrário → C.MP Tot.\n"
            "O agravamento é a diferença (C.Placa Usad − C.MP Tot)."
        ),
        "Não Stock": (
            "Marque para comprar placas inteiras desta placa (obra à medida).\n"
            "O orçamento passa a usar o custo de placa inteira (mais caro).\n"
            "Grave com o botão 'Gravar Não-Stock' para persistir."
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
        # Não-Stock editing state (phase 8W.2). Toggling a checkbox persists and
        # recalculates immediately (8W.2-UX, Part A) — there is no save button.
        self._placas_por_linha: dict = {}
        self._carregando_placas = False

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoRelatoriosStatus")

        self.dashboards = DashboardsWidget()

        self.tabs = QTabWidget()
        self.tabs.addTab(self._criar_tab_relatorio(), "Relatório de Orçamento")
        self.tabs.addTab(self._criar_tab_consumos(), "Resumo de Consumos")
        self.tabs.addTab(self.dashboards, "Dashboards")

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
        ligar_persistencia_larguras(self.items_table, "rel_items")

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

        # Top bar with the export actions (PDF: 8W.4.1; Excel: 8W.4.2).
        self.exportar_pdf_button = QPushButton("Exportar PDF")
        self.exportar_pdf_button.clicked.connect(self._exportar_pdf)
        self.exportar_excel_button = QPushButton("Exportar Excel")
        self.exportar_excel_button.clicked.connect(self._exportar_excel)
        self.exportar_resumo_button = QPushButton("Exportar Resumo de Custos")
        self.exportar_resumo_button.clicked.connect(self._exportar_resumo_custos)
        self.exportar_phc_button = QPushButton("Exportar PHC")
        self.exportar_phc_button.setToolTip(
            "Gerar o Excel no formato para importar no PHC."
        )
        self.exportar_phc_button.clicked.connect(self._exportar_phc)
        self.exportar_plano_corte_button = QPushButton("Exportar Plano de Corte PDF")
        self.exportar_plano_corte_button.setToolTip(
            "Gera o plano de corte das placas em PDF (otimizado) na pasta da obra."
        )
        self.exportar_plano_corte_button.clicked.connect(self._exportar_plano_corte)
        self.enviar_email_button = QPushButton("Enviar Orçamento por Email")
        self.enviar_email_button.setToolTip(
            "Gera/anexa o PDF do orçamento e abre o email para confirmação antes de enviar."
        )
        self.enviar_email_button.clicked.connect(self._enviar_email)
        barra = QHBoxLayout()
        barra.addStretch()
        barra.addWidget(self.exportar_pdf_button)
        barra.addWidget(self.exportar_excel_button)
        barra.addWidget(self.exportar_resumo_button)
        barra.addWidget(self.exportar_phc_button)
        barra.addWidget(self.exportar_plano_corte_button)
        barra.addWidget(self.enviar_email_button)

        tab = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(barra)
        layout.addLayout(cabecalho)
        layout.addWidget(self.banner_relatorio)
        layout.addWidget(self._titulo_seccao("Items do Orçamento"))
        layout.addWidget(self.items_table, stretch=1)
        layout.addWidget(self.total_label)
        tab.setLayout(layout)
        return tab

    # ----- Layout: tab 2 (consumption summary) -----

    def _criar_tab_consumos(self) -> QWidget:
        # Only "Atualizar" remains: the Não-Stock checkbox now saves and
        # recalculates on its own (8W.2-UX, Part A).
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
            self.PLACAS_HEADERS,
            tooltips=self.PLACAS_TOOLTIPS,
            larguras=self.PLACAS_LARGURAS,
        )
        self.placas_table.itemChanged.connect(self._on_placa_item_changed)
        ligar_persistencia_larguras(self.placas_table, "rel_placas")

        # Total Não-Stock surcharge versus the %-waste cost.
        self.agravamento_label = QLabel("")
        self.agravamento_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 2px;"
        )

        self.orlas_table = self._criar_tabela(
            self.ORLAS_HEADERS,
            tooltips=self.ORLAS_TOOLTIPS,
            larguras=self.ORLAS_LARGURAS,
        )
        ligar_persistencia_larguras(self.orlas_table, "rel_orlas")
        self.ferragens_table = self._criar_tabela(
            self.FERRAGENS_HEADERS,
            tooltips=self.FERRAGENS_TOOLTIPS,
            larguras=self.FERRAGENS_LARGURAS,
        )
        ligar_persistencia_larguras(self.ferragens_table, "rel_ferragens")
        self.maquinas_table = self._criar_tabela(
            self.MAQUINAS_HEADERS,
            tooltips=self.MAQUINAS_TOOLTIPS,
            larguras=self.MAQUINAS_LARGURAS,
        )
        ligar_persistencia_larguras(self.maquinas_table, "rel_maquinas")

        # Compact, scrollable content: each table is fitted to its row count
        # (Part C), so the sections sit close together with no empty gaps and
        # the whole block scrolls if it grows tall.
        conteudo = QWidget()
        conteudo_layout = QVBoxLayout()
        conteudo_layout.setContentsMargins(0, 0, 0, 0)
        conteudo_layout.setSpacing(2)
        conteudo_layout.addWidget(self._titulo_seccao("Resumo de Placas"))
        conteudo_layout.addWidget(self.placas_table)
        conteudo_layout.addWidget(self.agravamento_label)
        conteudo_layout.addWidget(self._titulo_seccao("Resumo de Orlas"))
        conteudo_layout.addWidget(self.orlas_table)
        conteudo_layout.addWidget(self._titulo_seccao("Resumo de Ferragens"))
        conteudo_layout.addWidget(self.ferragens_table)
        conteudo_layout.addWidget(self._titulo_seccao("Resumo de Máquinas / MO"))
        conteudo_layout.addWidget(self.maquinas_table)
        conteudo_layout.addStretch()
        conteudo.setLayout(conteudo_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(conteudo)

        tab = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(topo)
        layout.addWidget(self.banner_consumos)
        layout.addWidget(self.nota_consumos)
        layout.addWidget(scroll, stretch=1)
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

    def _criar_tabela(self, headers, tooltips=None, larguras=None) -> QTableWidget:
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
        # Initial column widths suited to the content (Part D); still Interactive.
        if larguras:
            for indice, nome in enumerate(headers):
                if nome in larguras:
                    tabela.setColumnWidth(indice, larguras[nome])
        return tabela

    def _ajustar_altura_tabela(self, tabela, max_linhas=12) -> None:
        """Fit a table's height to its row count (Part C).

        The table shrinks to the header + its rows (no empty gaps); beyond
        ``max_linhas`` it is capped and a vertical scrollbar appears.
        """
        linhas = tabela.rowCount()
        altura_linha = tabela.verticalHeader().defaultSectionSize()
        cabecalho = tabela.horizontalHeader().sizeHint().height()
        # Reserve room for a possible horizontal scrollbar so the last row of a
        # wide table is never clipped.
        scrollbar = tabela.horizontalScrollBar().sizeHint().height()
        visiveis = min(max(linhas, 1), max_linhas)
        altura = (
            cabecalho
            + visiveis * altura_linha
            + scrollbar
            + 2 * tabela.frameWidth()
            + 2
        )
        tabela.setMinimumHeight(altura)
        tabela.setMaximumHeight(altura)

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
        self.dashboards.atualizar(resumo)

        hora = datetime.now().strftime("%H:%M:%S")
        mensagem = f"Relatórios atualizados às {hora}"
        self.banner_relatorio.setText(mensagem)
        self.banner_consumos.setText(mensagem)
        self.status_label.setText("")

    def _exportar_pdf(self) -> None:
        """Export the budget PDF to the version folder (phase 8W.4.1)."""
        if not REPORTLAB_DISPONIVEL:
            QMessageBox.warning(
                self,
                "Exportar PDF",
                "A biblioteca 'reportlab' não está instalada.\n"
                "Instale-a (pip install reportlab) para exportar o PDF.",
            )
            return

        try:
            with SessionLocal() as session:
                caminho = OrcamentoExportService(session).exportar_pdf_orcamento(
                    self.orcamento_versao_id
                )
        except (ValueError, SQLAlchemyError, RuntimeError) as erro:
            QMessageBox.critical(
                self,
                "Exportar PDF",
                f"Não foi possível exportar o PDF:\n{erro}",
            )
            return

        QMessageBox.information(
            self, "Exportar PDF", f"PDF criado em:\n{caminho}"
        )

    def _exportar_excel(self) -> None:
        """Export the budget Excel to the version folder (phase 8W.4.2)."""
        try:
            with SessionLocal() as session:
                caminho = OrcamentoExportService(session).exportar_excel_orcamento(
                    self.orcamento_versao_id
                )
        except (ValueError, SQLAlchemyError) as erro:
            QMessageBox.critical(
                self,
                "Exportar Excel",
                f"Não foi possível exportar o Excel:\n{erro}",
            )
            return

        QMessageBox.information(
            self, "Exportar Excel", f"Excel criado em:\n{caminho}"
        )

    def _exportar_phc(self) -> None:
        """Exporta o Excel no formato PHC para a pasta da versão (C2b)."""
        try:
            with SessionLocal() as session:
                caminho = OrcamentoExportService(session).exportar_excel_phc(
                    self.orcamento_versao_id
                )
        except (ValueError, SQLAlchemyError) as erro:
            QMessageBox.critical(
                self,
                "Exportar PHC",
                f"Não foi possível exportar o Excel PHC:\n{erro}",
            )
            return

        QMessageBox.information(
            self, "Exportar PHC", f"Excel PHC criado em:\n{caminho}"
        )

    def _exportar_plano_corte(self) -> None:
        """Gera o PDF do plano de corte (otimizado) na pasta da versão (C3.4)."""
        if not REPORTLAB_DISPONIVEL:
            QMessageBox.warning(
                self,
                "Plano de Corte",
                "A biblioteca 'reportlab' não está instalada.\n"
                "Instale-a (pip install reportlab) para gerar o plano de corte.",
            )
            return

        # Verificar se há peças de placa ANTES (evita gerar um PDF vazio).
        try:
            with SessionLocal() as session:
                grupos = PlanoCorteService(session).dados_plano_corte(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError as erro:
            QMessageBox.critical(
                self,
                "Plano de Corte",
                f"Não foi possível preparar o plano de corte:\n{erro}",
            )
            return

        if not grupos:
            QMessageBox.information(
                self,
                "Plano de Corte",
                "Este orçamento não tem peças de placa para gerar o plano de corte.",
            )
            return

        # A otimização pode demorar: cursor de espera durante a geração.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                caminho = OrcamentoExportService(session).exportar_plano_corte(
                    self.orcamento_versao_id
                )
        except (ValueError, SQLAlchemyError, RuntimeError) as erro:
            QMessageBox.critical(
                self,
                "Plano de Corte",
                f"Não foi possível gerar o plano de corte:\n{erro}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        QMessageBox.information(
            self, "Plano de Corte", f"Plano de corte criado em:\n{caminho}"
        )

    def _exportar_resumo_custos(self) -> None:
        """Exporta o Resumo de Custos (modelo) para a pasta da versao."""
        try:
            with SessionLocal() as session:
                caminho = OrcamentoExportService(session).exportar_resumo_custos(
                    self.orcamento_versao_id
                )
        except (ValueError, SQLAlchemyError) as erro:
            QMessageBox.critical(
                self,
                "Resumo de Custos",
                f"Não foi possível exportar o Resumo de Custos:\n{erro}",
            )
            return

        QMessageBox.information(
            self, "Resumo de Custos", f"Resumo de Custos criado em:\n{caminho}"
        )

    def _enviar_email(self) -> None:
        """Send the budget PDF by email and register the send in history."""
        orcamento = None
        cliente = None
        pdf_path = None
        anexos: list[str] = []
        pdf_filename = ""
        pasta_inicial = str(Path.home())

        try:
            with SessionLocal() as session:
                export = OrcamentoExportService(session)
                orcamento = export.orcamento_service.get_orcamento_by_versao_id(
                    self.orcamento_versao_id
                )
                cliente = export.orcamento_service.get_cliente_da_versao(
                    self.orcamento_versao_id
                )
                config = carregar_email_config(session)

                if orcamento is None or cliente is None:
                    QMessageBox.warning(
                        self,
                        "Email",
                        "Orçamento ou cliente não encontrado para esta versão.",
                    )
                    return

                try:
                    pdf_path = export.exportar_pdf_orcamento(self.orcamento_versao_id)
                except (ValueError, SQLAlchemyError, RuntimeError) as erro_pdf:
                    pasta = export.resolver_pasta_versao(
                        self.orcamento_versao_id, criar=False
                    )
                    if pasta is not None:
                        pasta_inicial = str(pasta)
                    QMessageBox.warning(
                        self,
                        "Email",
                        "Não foi possível gerar/anexar o PDF automaticamente.\n"
                        "Pode continuar e adicionar anexos manualmente.\n\n"
                        f"Detalhe: {erro_pdf}",
                    )
                else:
                    anexos = [str(pdf_path)]
                    pdf_filename = pdf_path.name
                    pasta_inicial = str(pdf_path.parent)
        except (ValueError, SQLAlchemyError, RuntimeError) as erro:
            QMessageBox.critical(
                self,
                "Email",
                f"Não foi possível preparar o email:\n{erro}",
            )
            return

        current_user = app_session.current_user
        remetente_email = getattr(current_user, "email", None)
        remetente_nome = (
            getattr(current_user, "nome", None)
            or getattr(current_user, "username", None)
        )
        total = getattr(orcamento, "preco_total", None) or Decimal("0")

        dialog = EmailOrcamentoDialog(
            self,
            destinatario=getattr(cliente, "email", "") or "",
            cc=str(remetente_email or ""),
            assunto=construir_assunto_email(orcamento),
            corpo=construir_corpo_email(
                orcamento,
                cliente,
                total,
                pdf_filename=pdf_filename,
            ),
            anexos=anexos,
            pasta_inicial=pasta_inicial,
        )
        if not dialog.exec():
            return

        if not dialog.destinatario():
            QMessageBox.warning(
                self,
                "Email",
                "Indique o destinatário antes de enviar.",
            )
            return

        try:
            enviar_email(
                dialog.destinatario(),
                dialog.assunto(),
                dialog.corpo_html(),
                dialog.anexos(),
                config=config,
                remetente_email=remetente_email,
                remetente_nome=remetente_nome,
                cc=dialog.cc(),
            )
        except Exception as erro:
            QMessageBox.critical(
                self,
                "Email",
                f"Falha ao enviar o email:\n{erro}\n\nLog: {get_email_log_path()}",
            )
            return

        # Best-effort: grava um relatório HTML do email na pasta do orçamento.
        pasta_relatorio = (
            pdf_path.parent if pdf_path is not None else Path(pasta_inicial)
        )
        nome_base = (
            f"Email_Enviado_{orcamento.num_orcamento}_"
            f"{subpasta_versao(orcamento.numero_versao)}"
        )
        relatorio = escrever_relatorio_email(
            pasta_relatorio,
            nome_base,
            remetente=f"{remetente_nome or ''} <{remetente_email or ''}>".strip(),
            destino=dialog.destinatario(),
            cc=dialog.cc(),
            assunto=dialog.assunto(),
            corpo_html=dialog.corpo_html(),
            anexos=dialog.anexos(),
        )

        try:
            with SessionLocal() as session:
                OrcamentoHistoricoService(session).registar(
                    self.orcamento_versao_id,
                    "email",
                    f"Orçamento enviado para {dialog.destinatario()}",
                )
                session.commit()
        except SQLAlchemyError as erro:
            QMessageBox.warning(
                self,
                "Email",
                "Email enviado, mas não foi possível registar no histórico:\n"
                f"{erro}",
            )
            return

        msg = "Email enviado com sucesso."
        if relatorio is not None:
            msg += f"\n\nRegisto gravado em:\n{relatorio}"
        QMessageBox.information(self, "Email", msg)

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
        # Compact heights fitted to each table's row count (Part C).
        self._ajustar_altura_tabela(self.placas_table, max_linhas=12)
        self._ajustar_altura_tabela(self.orlas_table, max_linhas=8)
        self._ajustar_altura_tabela(self.ferragens_table, max_linhas=12)
        self._ajustar_altura_tabela(self.maquinas_table, max_linhas=6)

    def _preencher_placas(self, placas) -> None:
        self._carregando_placas = True
        try:
            self.placas_table.setRowCount(0)
            self._placas_por_linha = {}
            agravamento_total = Decimal("0")
            coluna_nao_stock = self.PLACAS_HEADERS.index("Não Stock")
            for placa in placas:
                row = self.placas_table.rowCount()
                self.placas_table.insertRow(row)
                self._placas_por_linha[row] = placa
                agravamento_total += placa.agravamento
                valores = {
                    "Ref": placa.ref_le or "",
                    "Descrição": placa.descricao_no_orcamento or "",
                    "P.Liq": format_currency(placa.pliq),
                    "Und": placa.unidade or "",
                    "Desp %": self._fmt_pct(placa.desp),
                    "Comp": format_mm(placa.comp_mp),
                    "Larg": format_mm(placa.larg_mp),
                    "Esp": format_mm(placa.esp_mp),
                    "Qt.Pla": str(placa.qt_placas),
                    "Área": self._fmt_m2(placa.area_placa),
                    "m² Usad": self._fmt_m2(placa.m2_consumidos),
                    "m² Peças": self._fmt_m2(placa.m2_total_pecas),
                    "C.MP Tot": format_currency(placa.custo_mp_total),
                    "C.Placa Usad": format_currency(placa.custo_placa_inteira),
                    "Custo no Orç.": format_currency(placa.custo_no_orcamento),
                }
                for col, header in enumerate(self.PLACAS_HEADERS):
                    if col == coluna_nao_stock:
                        item = QTableWidgetItem()
                        flags = (
                            item.flags()
                            | Qt.ItemFlag.ItemIsUserCheckable
                        ) & ~Qt.ItemFlag.ItemIsEditable
                        item.setFlags(flags)
                        item.setCheckState(
                            Qt.CheckState.Checked
                            if placa.nao_stock
                            else Qt.CheckState.Unchecked
                        )
                        item.setToolTip(self._tooltip_nao_stock(placa))
                        self.placas_table.setItem(row, col, item)
                    else:
                        self.placas_table.setItem(
                            row, col, criar_item_tabela(valores.get(header, ""))
                        )
        finally:
            self._carregando_placas = False

        self.agravamento_label.setText(
            f"Agravamento total por Não-Stock: {format_currency(agravamento_total)}"
            if placas
            else ""
        )

    def _tooltip_nao_stock(self, placa) -> str:
        """Explain the Não-Stock feature and show THIS board's surcharge.

        The surcharge is the whole-board cost minus the theoretical %-waste cost
        (Part B), shown whether or not the board is currently marked.
        """
        agravamento = placa.custo_placa_inteira - placa.custo_mp_total
        return (
            "Não Stock: placa comprada de propósito para a obra. Quando ativo, o "
            "orçamento usa o custo de placa inteira em vez do % desperdício.\n"
            f"Agravamento desta placa: +{format_currency(agravamento)} "
            f"({format_currency(placa.custo_placa_inteira)} − "
            f"{format_currency(placa.custo_mp_total)})."
        )

    def _on_placa_item_changed(self, item) -> None:
        """Toggle a board's Não-Stock state: persist and recalculate at once.

        The checkbox does everything on its own (8W.2-UX, Part A) — there is no
        save button: it saves the state, re-runs the costing and refreshes both
        the consumption tables and the "Relatório de Orçamento" tab.
        """
        if self._carregando_placas:
            return
        if item.column() != self.PLACAS_HEADERS.index("Não Stock"):
            return
        placa = self._placas_por_linha.get(item.row())
        if placa is None:
            return

        marcado = item.checkState() == Qt.CheckState.Checked
        try:
            with SessionLocal() as session:
                RelatorioConsumosService(session).guardar_nao_stock(
                    self.orcamento_versao_id,
                    [(placa.ref_le, placa.descricao_no_orcamento, placa.esp_mp, marcado)],
                )
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível gravar o Não-Stock.")
            return

        # Recompute with the new Não-Stock state and refresh both tabs.
        self.carregar()

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
