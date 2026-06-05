"""Piece definitions page."""

from __future__ import annotations

from PySide6.QtWidgets import (
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
from app.domain.peca_types import get_peca_type_label
from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_service import DefPecaService


class DefPecasPage(QWidget):
    """Page for listing reusable piece definitions."""

    TABLE_HEADERS = [
        "C\u00f3digo",
        "Nome",
        "Tipo",
        "Grupo",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        title = QLabel("Defini\u00e7\u00f5es de Pe\u00e7as")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Biblioteca de pe\u00e7as dispon\u00edveis para m\u00f3dulos, pe\u00e7as soltas e custeio")
        subtitle.setObjectName("pageSubtitle")

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_pecas)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("defPecasStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_pecas()

    def carregar_pecas(self) -> None:
        """Load piece definitions into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as definicoes de pecas.")
            return

        self._preencher_tabela(pecas)

        if not pecas:
            self.status_label.setText("Sem definicoes de pecas para mostrar.")

    def _preencher_tabela(self, pecas: list[DefPecaResumo]) -> None:
        """Fill the table with piece definition read models."""
        self.table.setRowCount(len(pecas))

        for row_index, peca in enumerate(pecas):
            values = [
                peca.codigo,
                peca.nome,
                get_peca_type_label(peca.tipo_peca),
                peca.grupo or "",
                "Sim" if peca.ativo else "N\u00e3o",
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
