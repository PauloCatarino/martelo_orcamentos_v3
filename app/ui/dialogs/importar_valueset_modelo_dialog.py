"""Dialog for selecting a ValueSet model to import into a budget."""

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
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_valueset_modelo_service import DefValuesetModeloService


class ImportarValuesetModeloDialog(QDialog):
    """Modal dialog to search and select an active ValueSet model."""

    TABLE_HEADERS = ["Código", "Nome", "Tipo", "Âmbito", "Ativo"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.selected_modelo: DefValuesetModeloResumo | None = None
        self._all_modelos: list[DefValuesetModeloResumo] = []
        self._modelos_by_row: dict[int, DefValuesetModeloResumo] = {}

        self.setWindowTitle("Importar Modelo ValueSet")
        self.setModal(True)
        self.setMinimumSize(640, 420)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar modelo...")
        self.search_input.textChanged.connect(self._aplicar_filtro)

        self.status_label = QLabel("")
        self.status_label.setObjectName("importarValuesetModeloStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.import_button = QPushButton("Importar")
        self.import_button.clicked.connect(self._importar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.search_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar()

    def _carregar(self) -> None:
        """Load active ValueSet models."""
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                self._all_modelos = DefValuesetModeloService(session).listar_modelos_ativos()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os modelos ValueSet.")
            return

        self._aplicar_filtro()

    def _aplicar_filtro(self) -> None:
        """Filter the loaded models by the search term."""
        termo = self.search_input.text().strip().lower()
        if termo:
            modelos = [
                modelo
                for modelo in self._all_modelos
                if termo in (modelo.codigo or "").lower()
                or termo in (modelo.nome or "").lower()
                or termo in (modelo.tipo or "").lower()
            ]
        else:
            modelos = list(self._all_modelos)

        self._preencher(modelos)

        if not modelos:
            self.status_label.setText("Sem modelos ValueSet para mostrar.")
        else:
            self.status_label.clear()

    def _preencher(self, modelos: list[DefValuesetModeloResumo]) -> None:
        """Fill the table with ValueSet models."""
        self._modelos_by_row = {}
        self.table.setRowCount(len(modelos))

        for row_index, modelo in enumerate(modelos):
            self._modelos_by_row[row_index] = modelo
            values = [
                modelo.codigo,
                modelo.nome,
                modelo.tipo or "",
                modelo.ambito,
                "Sim" if modelo.ativo else "Não",
            ]
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _get_selected(self) -> DefValuesetModeloResumo | None:
        """Return the selected model."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._modelos_by_row.get(row)

    def _importar(self) -> None:
        """Confirm the selected model and close the dialog."""
        modelo = self._get_selected()
        if modelo is None:
            self.status_label.setText("Selecione um modelo para importar.")
            return

        self.selected_modelo = modelo
        self.accept()

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Select a model when the user double-clicks its row."""
        self.table.selectRow(row)
        self._importar()
