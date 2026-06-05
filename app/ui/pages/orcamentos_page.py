"""Orcamentos page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class OrcamentosPage(QWidget):
    """Structural budgets page without data access yet."""

    TABLE_HEADERS = [
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Cliente",
        "Obra",
        "Estado",
        "Pre\u00e7o Total",
        "Criado em",
    ]

    def __init__(self) -> None:
        super().__init__()

        title = QLabel("Or\u00e7amentos")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Gest\u00e3o de or\u00e7amentos do Martelo V3")
        subtitle.setObjectName("pageSubtitle")

        new_button = QPushButton("Novo Or\u00e7amento")
        new_button.setEnabled(False)

        refresh_button = QPushButton("Atualizar")
        refresh_button.setEnabled(False)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(new_button)
        actions_layout.addWidget(refresh_button)
        actions_layout.addStretch()

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
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
