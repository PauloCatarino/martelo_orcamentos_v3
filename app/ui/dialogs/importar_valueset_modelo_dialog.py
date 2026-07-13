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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_valueset_modelo_service import DefValuesetModeloService
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class ImportarValuesetModeloDialog(QDialog):
    """Modal dialog to search and select an active ValueSet model.

    Models are split into two tabs: user models and global/shared models.
    """

    TABLE_HEADERS = ["Código", "Nome", "Tipo", "Ativo"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.selected_modelo: DefValuesetModeloResumo | None = None
        self._abas: dict[str, dict] = {}

        self.setWindowTitle("Importar Modelo ValueSet")
        self.setModal(True)
        self.setMinimumSize(660, 460)

        self.status_label = QLabel("")
        self.status_label.setObjectName("importarValuesetModeloStatus")

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_aba("user"), "Utilizador")
        self.tabs.addTab(self._build_aba("global"), "Global")

        self.import_button = QPushButton("Importar")
        self.import_button.clicked.connect(self._importar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs, stretch=1)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar()

    def _build_aba(self, key: str) -> QWidget:
        """Build one tab (search field + table) and register its state."""
        search = QLineEdit()
        search.setPlaceholderText("Pesquisar modelo...")
        search.textChanged.connect(lambda _text, aba_key=key: self._filtrar(aba_key))

        table = QTableWidget(0, len(self.TABLE_HEADERS))
        table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        ligar_persistencia_larguras(table, f"dialog_importar_valueset_{key}")
        table.cellDoubleClicked.connect(
            lambda row, _column, aba_key=key: self._selecionar_da_aba(aba_key, row)
        )

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(search)
        container_layout.addWidget(table, stretch=1)
        container.setLayout(container_layout)

        self._abas[key] = {"search": search, "table": table, "modelos": [], "by_row": {}}
        return container

    def _carregar(self) -> None:
        """Load user and global active ValueSet models."""
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                service = DefValuesetModeloService(session)
                self._abas["user"]["modelos"] = service.listar_modelos_utilizador()
                self._abas["global"]["modelos"] = service.listar_modelos_globais()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os modelos ValueSet.")
            return

        self._filtrar("user")
        self._filtrar("global")

    def _filtrar(self, key: str) -> None:
        """Filter one tab's models by its own search term."""
        aba = self._abas[key]
        termo = aba["search"].text().strip().lower()
        if termo:
            modelos = [
                modelo
                for modelo in aba["modelos"]
                if termo in (modelo.codigo or "").lower()
                or termo in (modelo.nome or "").lower()
                or termo in (modelo.tipo or "").lower()
            ]
        else:
            modelos = list(aba["modelos"])

        self._preencher(key, modelos)

    def _preencher(self, key: str, modelos: list[DefValuesetModeloResumo]) -> None:
        """Fill one tab's table with ValueSet models."""
        aba = self._abas[key]
        table = aba["table"]
        aba["by_row"] = {}
        table.setRowCount(len(modelos))

        for row_index, modelo in enumerate(modelos):
            aba["by_row"][row_index] = modelo
            values = [
                modelo.codigo,
                modelo.nome,
                modelo.tipo or "",
                "Sim" if modelo.ativo else "Não",
            ]
            for column_index, value in enumerate(values):
                table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _aba_ativa(self) -> str:
        """Return the key of the currently selected tab."""
        return "global" if self.tabs.currentIndex() == 1 else "user"

    def _get_selected(self) -> DefValuesetModeloResumo | None:
        """Return the model selected in the active tab."""
        aba = self._abas[self._aba_ativa()]
        row = aba["table"].currentRow()
        if row < 0:
            return None

        return aba["by_row"].get(row)

    def _importar(self) -> None:
        """Confirm the model selected in the active tab and close the dialog."""
        modelo = self._get_selected()
        if modelo is None:
            self.status_label.setText("Selecione um modelo.")
            return

        self.selected_modelo = modelo
        self.accept()

    def _selecionar_da_aba(self, key: str, row: int) -> None:
        """Select and accept a model when its row is double-clicked."""
        aba = self._abas[key]
        aba["table"].selectRow(row)
        modelo = aba["by_row"].get(row)
        if modelo is None:
            return

        self.selected_modelo = modelo
        self.accept()
