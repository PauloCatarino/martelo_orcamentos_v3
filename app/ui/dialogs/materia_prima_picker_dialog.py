"""Dialog for picking a raw material from the catalog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.materia_prima_snapshot import (
    coresp_orla_0_4,
    coresp_orla_1_0,
    familia_materia_prima,
    tipo_materia_prima,
)
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.utils.formatters import format_currency, format_quantity


class MateriaPrimaPickerDialog(QDialog):
    """Modal dialog to search and select a raw material."""

    TABLE_HEADERS = [
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Ativo",
    ]

    OPCAO_TODOS = "(Todos)"

    def __init__(
        self,
        parent=None,
        initial_tipo: str | None = None,
        initial_familia: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.selected_materia: DefMateriaPrimaResumo | None = None
        self._materias_by_row: dict[int, DefMateriaPrimaResumo] = {}
        self._aplicando_filtros = False

        self.setWindowTitle("Selecionar Matéria-Prima")
        self.setModal(True)
        self.setMinimumSize(900, 540)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Pesquisar por referência, descrição, tipo ou família..."
        )
        self.search_input.returnPressed.connect(self.pesquisar)

        self.search_button = QPushButton("Pesquisar")
        self.search_button.clicked.connect(self.pesquisar)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.pesquisar)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.refresh_button)

        # Tipo / Família filters (pre-filled from the cost line when opened there).
        self.tipo_filter = QComboBox()
        self.familia_filter = QComboBox()
        self.limpar_filtros_button = QPushButton("Limpar filtros")
        self.limpar_filtros_button.clicked.connect(self.limpar_filtros)

        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Tipo:"))
        filtros_layout.addWidget(self.tipo_filter)
        filtros_layout.addWidget(QLabel("Família:"))
        filtros_layout.addWidget(self.familia_filter)
        filtros_layout.addWidget(self.limpar_filtros_button)
        filtros_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("materiaPrimaPickerStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.select_button = QPushButton("Selecionar")
        self.select_button.clicked.connect(self._selecionar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addLayout(search_layout)
        layout.addLayout(filtros_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar_opcoes_filtros()
        self._definir_filtro_inicial(self.tipo_filter, initial_tipo)
        self._definir_filtro_inicial(self.familia_filter, initial_familia)
        self.tipo_filter.currentIndexChanged.connect(self._on_filtro_changed)
        self.familia_filter.currentIndexChanged.connect(self._on_filtro_changed)

        self.pesquisar()

    def _carregar_opcoes_filtros(self) -> None:
        """Populate the Tipo/Família combos with the catalog's distinct values."""
        try:
            with SessionLocal() as session:
                materias = DefMateriaPrimaService(session).listar_materias_primas_ativas()
        except SQLAlchemyError:
            materias = []

        tipos = sorted(
            {
                (tipo_materia_prima(m) or "").strip()
                for m in materias
                if (tipo_materia_prima(m) or "").strip()
            }
        )
        familias = sorted(
            {
                (familia_materia_prima(m) or "").strip()
                for m in materias
                if (familia_materia_prima(m) or "").strip()
            }
        )

        self._aplicando_filtros = True
        for combo, valores in (
            (self.tipo_filter, tipos),
            (self.familia_filter, familias),
        ):
            combo.clear()
            combo.addItem(self.OPCAO_TODOS, None)
            for valor in valores:
                combo.addItem(valor, valor)
        self._aplicando_filtros = False

    def _definir_filtro_inicial(self, combo: QComboBox, valor: str | None) -> None:
        """Pre-select a combo value (tolerant of case/plural), adding it if missing."""
        if not valor:
            return

        valor_norm = valor.strip()
        if not valor_norm:
            return

        self._aplicando_filtros = True
        alvo = valor_norm.upper()
        indice = -1
        for i in range(combo.count()):
            texto = (combo.itemText(i) or "").strip().upper()
            if texto and (
                texto == alvo or texto.startswith(alvo) or alvo.startswith(texto)
            ):
                indice = i
                break

        if indice >= 0:
            combo.setCurrentIndex(indice)
        else:
            combo.addItem(valor_norm, valor_norm)
            combo.setCurrentIndex(combo.count() - 1)
        self._aplicando_filtros = False

    def _on_filtro_changed(self, _index: int) -> None:
        """Re-run the search when a filter changes (ignoring programmatic changes)."""
        if self._aplicando_filtros:
            return
        self.pesquisar()

    def limpar_filtros(self) -> None:
        """Reset both Tipo/Família filters to "(Todos)" and refresh the table."""
        self._aplicando_filtros = True
        self.tipo_filter.setCurrentIndex(0)
        self.familia_filter.setCurrentIndex(0)
        self._aplicando_filtros = False
        self.pesquisar()

    def pesquisar(self) -> None:
        """Search raw materials by term, then apply the Tipo/Família filters."""
        self.status_label.clear()
        termo = self.search_input.text()

        try:
            with SessionLocal() as session:
                materias = DefMateriaPrimaService(session).pesquisar(termo)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel pesquisar as materias-primas.")
            return

        tipo_filtro = self._filtro_atual(self.tipo_filter)
        familia_filtro = self._filtro_atual(self.familia_filter)
        if tipo_filtro:
            materias = [
                m for m in materias if self._corresponde(tipo_materia_prima(m), tipo_filtro)
            ]
        if familia_filtro:
            materias = [
                m
                for m in materias
                if self._corresponde(familia_materia_prima(m), familia_filtro)
            ]

        self._preencher(materias)

        if not materias:
            if tipo_filtro or familia_filtro:
                self.status_label.setText("Sem resultados para os filtros aplicados.")
            else:
                self.status_label.setText("Sem materias-primas para mostrar.")

    def _filtro_atual(self, combo: QComboBox) -> str | None:
        """Return the active filter value of a combo, or None for "(Todos)"."""
        valor = combo.currentData()
        return (valor or "").strip().upper() or None

    def _corresponde(self, valor, filtro: str) -> bool:
        """Match a material's type/family against a filter (case/plural tolerant)."""
        texto = (valor or "").strip().upper()
        if not texto:
            return False

        return texto == filtro or texto.startswith(filtro) or filtro.startswith(texto)

    def _preencher(self, materias: list[DefMateriaPrimaResumo]) -> None:
        """Fill the table with raw materials."""
        self._materias_by_row = {}
        self.table.setRowCount(len(materias))

        for row_index, materia in enumerate(materias):
            self._materias_by_row[row_index] = materia
            values = [
                materia.ref_le or "",
                materia.descricao or "",
                materia.unidade or "",
                format_currency(materia.preco_tabela),
                formatar_percentagem(normalize_percentagem_humana(materia.margem)),
                formatar_percentagem(normalize_percentagem_humana(materia.desconto)),
                format_currency(materia.preco_liquido),
                formatar_percentagem(
                    normalize_percentagem_humana(materia.desperdicio_percentagem)
                ),
                tipo_materia_prima(materia) or "",
                familia_materia_prima(materia) or "",
                coresp_orla_0_4(materia) or "",
                coresp_orla_1_0(materia) or "",
                format_quantity(materia.comprimento),
                format_quantity(materia.largura),
                format_quantity(materia.espessura),
                "Sim" if materia.ativo else "Não",
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _get_selected(self) -> DefMateriaPrimaResumo | None:
        """Return the selected raw material."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._materias_by_row.get(row)

    def _selecionar(self) -> None:
        """Confirm the selection and close the dialog."""
        materia = self._get_selected()
        if materia is None:
            self.status_label.setText("Selecione uma materia-prima.")
            return

        self.selected_materia = materia
        self.accept()

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Select a raw material when the user double-clicks its row."""
        self.table.selectRow(row)
        self._selecionar()
