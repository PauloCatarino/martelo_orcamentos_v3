"""Raw materials catalog page."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.utils.formatters import format_currency, format_quantity


class MateriasPrimasPage(QWidget):
    """Page for listing imported raw materials."""

    TABLE_HEADERS = [
        "Ref LE",
        "Descri\u00e7\u00e3o",
        "Tipo Excel",
        "Fam\u00edlia Excel",
        "Unidade",
        "Desp %",
        "Pre\u00e7o L\u00edquido",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self._materias_primas: list[DefMateriaPrimaResumo] = []

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

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar mat\u00e9ria-prima...")
        self.search_input.textChanged.connect(self.aplicar_pesquisa)

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
        layout.addWidget(self.search_input)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_materias_primas()

    def carregar_materias_primas(self) -> None:
        """Load raw materials into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()
        self._materias_primas = []

        try:
            with SessionLocal() as session:
                materias_primas = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as materias-primas.")
            return

        self._materias_primas = materias_primas
        self.aplicar_pesquisa()

        if not materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        """Filter the loaded raw materials according to the search text."""
        self.status_label.clear()
        search_text = self.search_input.text()

        if not search_text.strip():
            filtered = self._materias_primas
        else:
            filtered = [
                materia
                for materia in self._materias_primas
                if materia_matches_search(materia, search_text)
            ]

        self._preencher_tabela(filtered)

        if not self._materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")
        elif search_text.strip() and not filtered:
            self.status_label.setText("Sem resultados para a pesquisa.")

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
                formatar_percentagem(
                    normalize_percentagem_humana(materia.desperdicio_percentagem)
                ),
                format_currency(materia.preco_liquido),
                materia.coresp_orla_0_4 or "",
                materia.coresp_orla_1_0 or "",
                format_quantity(materia.comprimento),
                format_quantity(materia.largura),
                format_quantity(materia.espessura),
                "Sim" if materia.ativo else "N\u00e3o",
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))


def normalize_search_text(value: object) -> str:
    """Normalize text for accent-insensitive, case-insensitive search."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def materia_matches_search(materia: DefMateriaPrimaResumo, search_text: str) -> bool:
    """Return whether a raw material matches all search tokens."""
    tokens = normalize_search_text(search_text).split()
    if not tokens:
        return True

    searchable_text = normalize_search_text(
        " ".join(
            [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                materia.fornecedor or "",
            ]
        )
    )

    return all(token in searchable_text for token in tokens)
