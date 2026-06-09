"""Dialog for picking a raw material from the catalog."""

from __future__ import annotations

from PySide6.QtWidgets import (
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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.selected_materia: DefMateriaPrimaResumo | None = None
        self._materias_by_row: dict[int, DefMateriaPrimaResumo] = {}

        self.setWindowTitle("Selecionar Matéria-Prima")
        self.setModal(True)
        self.setMinimumSize(900, 500)

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
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.pesquisar()

    def pesquisar(self) -> None:
        """Search raw materials using the search box term."""
        self.status_label.clear()
        termo = self.search_input.text()

        try:
            with SessionLocal() as session:
                materias = DefMateriaPrimaService(session).pesquisar(termo)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel pesquisar as materias-primas.")
            return

        self._preencher(materias)

        if not materias:
            self.status_label.setText("Sem materias-primas para mostrar.")

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
