"""Orcamentos page."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

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

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.orcamento_estados import ESTADOS_ORCAMENTO
from app.domain.orcamentos_lista import filtrar_orcamentos, resumo_lista
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    EditarOrcamentoData,
    OrcamentoService,
)
from app.ui.dialogs.editar_orcamento_dialog import (
    EditarOrcamentoDialog,
    EditarOrcamentoDialogData,
)
from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.utils.formatters import format_currency, format_version


class OrcamentosPage(QWidget):
    """Structural budgets page without data access yet."""

    TABLE_HEADERS = [
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Estado",
        "Enc PHC",
        "Cliente",
        "Ref. Cliente",
        "Obra",
        "Localiza\u00e7\u00e3o",
        "Descri\u00e7\u00e3o",
        "Data",
        "Pre\u00e7o Total",
        "Utilizador",
        "Info 1",
        "Info 2",
    ]
    COLUMN_WIDTHS = {
        "Ano": 60,
        "N\u00ba Or\u00e7amento": 105,
        "Vers\u00e3o": 70,
        "Estado": 115,
        "Enc PHC": 85,
        "Cliente": 190,
        "Ref. Cliente": 110,
        "Obra": 210,
        "Localiza\u00e7\u00e3o": 150,
        "Descri\u00e7\u00e3o": 220,
        "Data": 95,
        "Pre\u00e7o Total": 110,
        "Utilizador": 110,
        "Info 1": 180,
        "Info 2": 180,
    }
    CENTERED_HEADERS = {"Ano", "Vers\u00e3o", "Estado", "Enc PHC", "Data", "Utilizador"}

    def __init__(self, on_open_orcamento: Callable[[OrcamentoResumo], None] | None = None) -> None:
        super().__init__()

        self.on_open_orcamento = on_open_orcamento
        self._orcamentos_by_row: dict[int, OrcamentoResumo] = {}
        self._todos: list[OrcamentoResumo] = []

        title = QLabel("Or\u00e7amentos")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Gest\u00e3o de or\u00e7amentos do Martelo V3")
        subtitle.setObjectName("pageSubtitle")

        self.new_button = QPushButton("Novo Or\u00e7amento")
        self.new_button.clicked.connect(self.abrir_novo_orcamento)

        self.open_button = QPushButton("Abrir Or\u00e7amento")
        self.open_button.clicked.connect(self.abrir_orcamento_selecionado)

        self.edit_button = QPushButton("Editar Or\u00e7amento")
        self.edit_button.clicked.connect(self.editar_orcamento_selecionado)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_orcamentos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.estado_combo = QComboBox()
        self.cliente_combo = QComboBox()
        self.utilizador_combo = QComboBox()
        for combo in (self.estado_combo, self.cliente_combo, self.utilizador_combo):
            combo.currentTextChanged.connect(self._render)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(self.campo_pesquisa)
        filters_layout.addWidget(QLabel("Estado"))
        filters_layout.addWidget(self.estado_combo)
        filters_layout.addWidget(QLabel("Cliente"))
        filters_layout.addWidget(self.cliente_combo)
        filters_layout.addWidget(QLabel("Utilizador"))
        filters_layout.addWidget(self.utilizador_combo)
        filters_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentosStatus")

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
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("orcamentosFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.footer_label)

        self.setLayout(layout)
        self.carregar_orcamentos()

    def carregar_orcamentos(self) -> None:
        """Load budget versions into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                orcamentos = OrcamentoService(session).list_orcamentos()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os orcamentos.")
            return

        self._todos = list(orcamentos)
        self._atualizar_filtros()
        self._render()

        if not self._todos:
            self.status_label.setText("Sem orcamentos para mostrar.")

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search and filters."""
        filtrados = filtrar_orcamentos(
            self._todos,
            texto=self.campo_pesquisa.texto(),
            estado=self._combo_valor(self.estado_combo),
            cliente=self._combo_valor(self.cliente_combo),
            utilizador=self._combo_valor(self.utilizador_combo),
        )
        self._preencher_tabela(filtrados)
        self._atualizar_rodape(filtrados)

    def _limpar_filtros(self) -> None:
        """Clear search and reset all filters to 'Todos'."""
        widgets = (
            self.campo_pesquisa,
            self.estado_combo,
            self.cliente_combo,
            self.utilizador_combo,
        )
        estados_sinais = [(widget, widget.blockSignals(True)) for widget in widgets]
        self.campo_pesquisa.limpar()
        for combo in (self.estado_combo, self.cliente_combo, self.utilizador_combo):
            if combo.count():
                combo.setCurrentIndex(0)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)
        self._render()

    def _atualizar_filtros(self) -> None:
        """Populate filter combos from the loaded list, preserving selection."""
        self._popular_combo(
            self.estado_combo,
            list(ESTADOS_ORCAMENTO),
        )
        self._popular_combo(
            self.cliente_combo,
            self._valores_distintos("cliente_nome"),
        )
        self._popular_combo(
            self.utilizador_combo,
            self._valores_distintos("utilizador"),
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
                getattr(orcamento, atributo, None) for orcamento in self._todos
            )
            if valor is not None and str(valor).strip()
        }
        return sorted(valores, key=str.lower)

    @staticmethod
    def _combo_valor(combo: QComboBox) -> str | None:
        valor = combo.currentText().strip()
        if not valor or valor == "Todos":
            return None
        return valor

    def abrir_novo_orcamento(self) -> None:
        """Open the simple new budget dialog."""
        dialog = NovoOrcamentoDialog(self)

        if not dialog.exec():
            return

        form_data = dialog.get_data()
        current_user = app_session.current_user
        created_by_id = current_user.id if current_user is not None else None

        try:
            with SessionLocal() as session:
                service = OrcamentoService(session)
                result = service.criar_orcamento_simples(
                    CriarOrcamentoSimplesData(
                        nome_cliente=form_data.nome_cliente,
                        email_cliente=form_data.email_cliente,
                        telefone_cliente=form_data.telefone_cliente,
                        obra=form_data.obra,
                        descricao=form_data.descricao,
                        localizacao=form_data.localizacao,
                        ref_cliente=form_data.ref_cliente,
                        enc_phc=form_data.enc_phc,
                        info_1=form_data.info_1,
                        info_2=form_data.info_2,
                        created_by_id=created_by_id,
                        margens_escolha=form_data.margens_escolha,
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel criar o orcamento.")
            return

        self.status_label.setText(f"Orcamento {result.codigo_versao} criado.")
        self.carregar_orcamentos()

    def _preencher_tabela(self, orcamentos: list[OrcamentoResumo]) -> None:
        """Fill the table with budget read models."""
        self._orcamentos_by_row = {}
        self.table.setRowCount(len(orcamentos))

        for row_index, orcamento in enumerate(orcamentos):
            self._orcamentos_by_row[row_index] = orcamento
            values = [
                str(orcamento.ano),
                orcamento.num_orcamento,
                format_version(orcamento.numero_versao),
                orcamento.estado,
                orcamento.enc_phc or "",
                orcamento.cliente_nome,
                orcamento.ref_cliente or "",
                orcamento.obra or "",
                orcamento.localizacao or "",
                orcamento.descricao or "",
                self._format_date(orcamento.created_at),
                format_currency(orcamento.preco_total),
                orcamento.utilizador or "",
                orcamento.info_1 or "",
                orcamento.info_2 or "",
            ]

            for column_index, value in enumerate(values):
                header = self.TABLE_HEADERS[column_index]
                item = self._criar_item_tabela(value, header)
                if column_index == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        {
                            "orcamento_id": orcamento.orcamento_id,
                            "orcamento_versao_id": orcamento.orcamento_versao_id,
                        },
                    )
                if header == "Estado":
                    self._aplicar_badge_estado(item, orcamento.estado)
                self.table.setItem(row_index, column_index, item)

    def _criar_item_tabela(self, value: str, header: str) -> QTableWidgetItem:
        """Create a table item with the list page alignment conventions."""
        item = QTableWidgetItem(value)
        if header in self.CENTERED_HEADERS:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        elif header == "Pre\u00e7o Total":
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        else:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        if value:
            item.setToolTip(value)
        return item

    def _aplicar_badge_estado(self, item: QTableWidgetItem, estado: str | None) -> None:
        fundo, texto = tema.cor_estado(estado)
        item.setBackground(QColor(fundo))
        item.setForeground(QColor(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)

    def _atualizar_rodape(self, orcamentos: list[OrcamentoResumo]) -> None:
        contagem, total = resumo_lista(orcamentos)
        self.footer_label.setText(
            f"{contagem} or\u00e7amentos \u00b7 Total: {format_currency(total)}"
        )

    def abrir_orcamento_selecionado(self) -> None:
        """Open the currently selected budget through the callback."""
        row = self.table.currentRow()
        orcamento = self._orcamentos_by_row.get(row)

        if row < 0 or orcamento is None:
            self.status_label.setText("Selecione um orcamento para abrir.")
            return

        if self.on_open_orcamento is not None:
            self.on_open_orcamento(orcamento)

    def editar_orcamento_selecionado(self) -> None:
        """Edit the general data of the currently selected budget."""
        row = self.table.currentRow()
        orcamento = self._orcamentos_by_row.get(row)

        if row < 0 or orcamento is None:
            self.status_label.setText("Selecione um orcamento para editar.")
            return

        dialog = EditarOrcamentoDialog(
            self,
            EditarOrcamentoDialogData(
                obra=orcamento.obra or "",
                descricao=orcamento.descricao,
                localizacao=orcamento.localizacao,
                ref_cliente=orcamento.ref_cliente,
                estado=orcamento.estado,
                enc_phc=orcamento.enc_phc,
                info_1=orcamento.info_1,
                info_2=orcamento.info_2,
            ),
        )

        if not dialog.exec():
            return

        form_data = dialog.get_data()
        current_user = app_session.current_user
        updated_by_id = current_user.id if current_user is not None else None

        try:
            with SessionLocal() as session:
                OrcamentoService(session).editar_orcamento(
                    orcamento.orcamento_id,
                    EditarOrcamentoData(
                        obra=form_data.obra,
                        descricao=form_data.descricao,
                        localizacao=form_data.localizacao,
                        ref_cliente=form_data.ref_cliente,
                        estado=form_data.estado,
                        enc_phc=form_data.enc_phc,
                        info_1=form_data.info_1,
                        info_2=form_data.info_2,
                    ),
                    updated_by_id=updated_by_id,
                    orcamento_versao_id=orcamento.orcamento_versao_id,
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel atualizar o orcamento.")
            return

        self.carregar_orcamentos()
        self.status_label.setText("Orcamento atualizado.")

    def _handle_row_double_click(self, row: int, _column: int) -> None:
        """Open a budget when the user double-clicks its table row."""
        self.table.selectRow(row)
        self.abrir_orcamento_selecionado()

    def _format_date(self, value: datetime | None) -> str:
        """Format a datetime value for table display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d")
