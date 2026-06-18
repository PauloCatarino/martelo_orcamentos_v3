"""Customers page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from app.domain.clientes_lista import filtrar_clientes
from app.repositories.cliente_repository import ClienteListaResumo, ClienteRepository
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa


class ClientesPage(QWidget):
    """Customers page with temporary customers list."""

    TABLE_HEADERS = [
        "Nome",
        "Simplex",
        "Morada",
        "Email",
        "WEB",
        "Telefone",
        "Telem\u00f3vel",
        "Num PHC",
        "Info 1",
        "Info 2",
    ]
    COLUMN_WIDTHS = {
        "Nome": 220,
        "Simplex": 160,
        "Morada": 260,
        "Email": 220,
        "WEB": 220,
        "Telefone": 110,
        "Telem\u00f3vel": 110,
        "Num PHC": 90,
        "Info 1": 180,
        "Info 2": 180,
    }

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[ClienteListaResumo] = []

        title = QLabel("Clientes")
        title.setObjectName("pageTitle")

        tabs = QTabWidget()
        tabs.addTab(self._criar_tab_temporarios(), "Clientes Tempor\u00e1rios")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(tabs, stretch=1)
        self.setLayout(layout)

        self.carregar()

    def _criar_tab_temporarios(self) -> QWidget:
        tab = QWidget()

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._render)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("clientesStatus")

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

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("clientesFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.footer_label)
        tab.setLayout(layout)

        return tab

    def carregar(self) -> None:
        """Load temporary customers from the database."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                clientes = ClienteRepository(session).list_temporarios()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os clientes.")
            return

        self._todos = list(clientes)
        self._render()

        if not self._todos:
            self.status_label.setText("Sem clientes temporarios para mostrar.")

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search."""
        filtrados = filtrar_clientes(self._todos, texto=self.campo_pesquisa.texto())
        self._preencher_tabela(filtrados)
        self.footer_label.setText(f"{len(filtrados)} clientes")

    def _preencher_tabela(self, clientes: list[ClienteListaResumo]) -> None:
        """Fill the table with customer read models."""
        self.table.setRowCount(len(clientes))

        for row_index, cliente in enumerate(clientes):
            values = [
                cliente.nome,
                cliente.nome_simplex or "",
                cliente.morada or "",
                cliente.email or "",
                cliente.pagina_web or "",
                cliente.telefone or "",
                cliente.telemovel or "",
                cliente.num_cliente_phc or "",
                cliente.info_1 or "",
                cliente.info_2 or "",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if value:
                    item.setToolTip(value)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, cliente.id)
                self.table.setItem(row_index, column_index, item)

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)
