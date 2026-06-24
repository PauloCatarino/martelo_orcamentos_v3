"""Dialog for picking an existing customer."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.clientes_lista import filtrar_clientes
from app.repositories.cliente_repository import ClienteListaResumo, ClienteRepository
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.table_item import criar_item_tabela


class SelecionarClienteDialog(QDialog):
    """Modal dialog to search and select an existing customer."""

    TABLE_HEADERS = ["Tipo", "Nome", "Simplex", "Email", "Telefone", "Telem\u00f3vel"]

    def __init__(self, parent=None, *, apenas_phc: bool = False) -> None:
        super().__init__(parent)

        self.selected_cliente: ClienteListaResumo | None = None
        self._todos: list[ClienteListaResumo] = []
        self._linhas: list[ClienteListaResumo] = []
        self._apenas_phc = apenas_phc

        self.setWindowTitle("Selecionar Cliente")
        self.setModal(True)
        self.setMinimumSize(760, 460)

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._render)

        self.status_label = QLabel("")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.select_button = QPushButton("Selecionar")
        self.select_button.clicked.connect(self._selecionar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.campo_pesquisa, stretch=1)

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

        self._carregar()

    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                repository = ClienteRepository(session)
                clientes = (
                    repository.list_phc()
                    if self._apenas_phc
                    else repository.list_todos()
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os clientes.")
            return

        self._todos = list(clientes)
        self._render()

        if not self._todos:
            self.status_label.setText("Sem clientes. Crie-os no menu Clientes.")

    def _render(self, *_args) -> None:
        filtrados = filtrar_clientes(self._todos, texto=self.campo_pesquisa.texto())
        self._linhas = list(filtrados)
        self.table.setRowCount(len(filtrados))

        for row_index, cliente in enumerate(filtrados):
            tipo = "Tempor\u00e1rio" if cliente.is_temporary else "PHC"
            values = [
                tipo,
                cliente.nome,
                cliente.nome_simplex or "",
                cliente.email or "",
                cliente.telefone or "",
                cliente.telemovel or "",
            ]
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, criar_item_tabela(value))

    def _get_selected(self) -> ClienteListaResumo | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._linhas):
            return None

        return self._linhas[row]

    def _selecionar(self) -> None:
        cliente = self._get_selected()
        if cliente is None:
            self.status_label.setText("Selecione um cliente.")
            return

        self.selected_cliente = cliente
        self.accept()

    def _handle_double_click(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self._selecionar()
