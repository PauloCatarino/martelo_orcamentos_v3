"""Production process list page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.models.producao import Producao
from app.services.producao_service import ProducaoService, filtrar_processos
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class ProducaoPage(QWidget):
    """Read-only production process page."""

    TABLE_HEADERS = [
        "Ano",
        "Processo",
        "Estado",
        "Cliente",
        "Ref Cliente",
        "Obra",
        "Localização",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
        "Responsável",
        "Tipo Pasta",
    ]
    COLUMN_WIDTHS = {
        "Ano": 60,
        "Processo": 115,
        "Estado": 110,
        "Cliente": 190,
        "Ref Cliente": 110,
        "Obra": 210,
        "Localização": 150,
        "Nº Enc PHC": 95,
        "V. Obra": 75,
        "V. CutRite": 80,
        "Data Início": 95,
        "Data Entrega": 95,
        "Responsável": 120,
        "Tipo Pasta": 170,
    }
    CENTERED_HEADERS = {
        "Ano",
        "Processo",
        "Estado",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
    }

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[Producao] = []

        self.cabecalho = BarraCabecalho(
            "Produção",
            ["Obras em produção do Martelo V3"],
        )

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_processos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.estado_combo = QComboBox()
        self.cliente_combo = QComboBox()
        self.responsavel_combo = QComboBox()
        for combo in (self.estado_combo, self.cliente_combo, self.responsavel_combo):
            combo.currentTextChanged.connect(self._render)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(self.campo_pesquisa)
        filters_layout.addWidget(QLabel("Estado"))
        filters_layout.addWidget(self.estado_combo)
        filters_layout.addWidget(QLabel("Cliente"))
        filters_layout.addWidget(self.cliente_combo)
        filters_layout.addWidget(QLabel("Responsável"))
        filters_layout.addWidget(self.responsavel_combo)
        filters_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("producaoStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self._aplicar_larguras_colunas()
        ligar_persistencia_larguras(self.table, "producao")

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("producaoFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.footer_label)

        self.setLayout(layout)
        self.carregar_processos()

    def carregar_processos(self) -> None:
        """Load production processes into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                processos = ProducaoService(session).listar_processos()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar a producao.")
            return

        self._todos = list(processos)
        self._atualizar_filtros()
        self._render()

        if not self._todos:
            self.status_label.setText("Sem processos de produção para mostrar.")

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search and filters."""
        filtrados = filtrar_processos(
            self._todos,
            texto=self.campo_pesquisa.texto(),
            estado=self._combo_valor(self.estado_combo),
            cliente=self._combo_valor(self.cliente_combo),
            responsavel=self._combo_valor(self.responsavel_combo),
        )
        self._preencher_tabela(filtrados)
        self.footer_label.setText(f"{len(filtrados)} de {len(self._todos)}")

    def _limpar_filtros(self) -> None:
        """Clear search and reset all filters to 'Todos'."""
        widgets = (
            self.campo_pesquisa,
            self.estado_combo,
            self.cliente_combo,
            self.responsavel_combo,
        )
        estados_sinais = [(widget, widget.blockSignals(True)) for widget in widgets]
        self.campo_pesquisa.limpar()
        for combo in (self.estado_combo, self.cliente_combo, self.responsavel_combo):
            if combo.count():
                combo.setCurrentIndex(0)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)
        self._render()

    def _atualizar_filtros(self) -> None:
        """Populate filter combos from the loaded list, preserving selection."""
        self._popular_combo(
            self.estado_combo,
            self._combinar_valores(list(ESTADOS_PRODUCAO), self._valores_distintos("estado")),
        )
        self._popular_combo(
            self.cliente_combo,
            self._valores_distintos("nome_cliente"),
        )
        self._popular_combo(
            self.responsavel_combo,
            self._valores_distintos("responsavel"),
        )

    def _popular_combo(self, combo: QComboBox, valores: list[str]) -> None:
        atual = combo.currentText() or "Todos"
        estado_anterior = combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos")
        for valor in valores:
            combo.addItem(valor)

        indice = combo.findText(atual)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(estado_anterior)

    def _valores_distintos(self, atributo: str) -> list[str]:
        valores = {
            str(valor).strip()
            for valor in (
                getattr(processo, atributo, None) for processo in self._todos
            )
            if valor is not None and str(valor).strip()
        }
        return sorted(valores, key=str.lower)

    @staticmethod
    def _combinar_valores(primeiros: list[str], restantes: list[str]) -> list[str]:
        valores: list[str] = []
        vistos: set[str] = set()
        for valor in [*primeiros, *restantes]:
            chave = valor.strip().lower()
            if not chave or chave in vistos:
                continue
            valores.append(valor)
            vistos.add(chave)
        return valores

    @staticmethod
    def _combo_valor(combo: QComboBox) -> str | None:
        valor = combo.currentText().strip()
        if not valor or valor == "Todos":
            return None
        return valor

    def _preencher_tabela(self, processos: list[Producao]) -> None:
        """Fill the table with production processes."""
        self.table.setRowCount(len(processos))

        for row_index, processo in enumerate(processos):
            values = [
                processo.ano,
                processo.codigo_processo,
                processo.estado or "",
                processo.nome_cliente or "",
                processo.ref_cliente or "",
                processo.obra or "",
                processo.localizacao or "",
                processo.num_enc_phc,
                processo.versao_obra,
                processo.versao_plano,
                processo.data_inicio or "",
                processo.data_entrega or "",
                processo.responsavel or "",
                processo.tipo_pasta or "",
            ]

            for column_index, value in enumerate(values):
                header = self.TABLE_HEADERS[column_index]
                item = self._criar_item_tabela(value, header)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, {"producao_id": processo.id})
                self.table.setItem(row_index, column_index, item)

    def _criar_item_tabela(self, value: str, header: str) -> QTableWidgetItem:
        """Create a table item with the list page alignment conventions."""
        item = QTableWidgetItem(value or "")
        if header in self.CENTERED_HEADERS:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        if value:
            item.setToolTip(value)
        return item

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)
