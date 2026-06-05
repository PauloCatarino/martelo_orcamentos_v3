"""Raw materials catalog page."""

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
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.utils.formatters import format_currency


class MateriasPrimasPage(QWidget):
    """Page for listing imported raw materials."""

    TABLE_HEADERS = [
        "Ref LE",
        "Descri\u00e7\u00e3o",
        "Tipo Excel",
        "Fam\u00edlia Excel",
        "Unidade",
        "Pre\u00e7o L\u00edquido",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        title = QLabel("Mat\u00e9rias-Primas")
        title.setObjectName("pageTitle")

        info = QLabel(
            "Cat\u00e1logo de mat\u00e9rias-primas importado a partir do Excel. "
            "Estes dados ser\u00e3o usados futuramente nas configura\u00e7\u00f5es de "
            "or\u00e7amento, items e custeio."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_materias_primas)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("materiasPrimasStatus")

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
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_materias_primas()

    def carregar_materias_primas(self) -> None:
        """Load raw materials into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                materias_primas = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as materias-primas.")
            return

        self._preencher_tabela(materias_primas)

        if not materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")

    def _preencher_tabela(self, materias_primas: list[DefMateriaPrimaResumo]) -> None:
        """Fill the table with raw material read models."""
        self.table.setRowCount(len(materias_primas))

        for row_index, materia in enumerate(materias_primas):
            values = [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                format_currency(materia.preco_liquido),
                "Sim" if materia.ativo else "N\u00e3o",
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
