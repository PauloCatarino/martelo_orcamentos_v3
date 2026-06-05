"""Piece definition detail page."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain.componente_types import get_componente_type_label
from app.domain.peca_types import get_peca_type_label
from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.repositories.def_peca_repository import DefPecaResumo
from app.utils.formatters import format_quantity


class DefPecaDetailPage(QWidget):
    """Read-only detail page for one reusable piece definition."""

    COMPONENTES_HEADERS = [
        "Ordem",
        "Tipo componente",
        "Componente / Refer\u00eancia",
        "Descri\u00e7\u00e3o",
        "Quantidade",
        "Regra quantidade",
        "Obrigat\u00f3rio",
        "Ativo",
    ]

    def __init__(
        self,
        peca: DefPecaResumo,
        componentes: list[DefPecaComponenteResumo] | None = None,
        component_labels: dict[int, str] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.peca = peca
        self.componentes = componentes or []
        self.component_labels = component_labels or {}
        self.on_back = on_back

        title = QLabel(f"Defini\u00e7\u00e3o de Pe\u00e7a: {peca.codigo}")
        title.setObjectName("defPecaDetailTitle")

        self.back_button = QPushButton("Voltar \u00e0 lista")
        self.back_button.clicked.connect(self._handle_back)

        header_layout = QHBoxLayout()
        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignRight)

        tabs = QTabWidget()
        tabs.addTab(self._create_dados_gerais_tab(), "Dados Gerais")
        tabs.addTab(self._create_componentes_tab(), "Componentes")
        tabs.addTab(self._create_placeholder_tab("Regras da pe\u00e7a ser\u00e3o configuradas numa fase posterior."), "Regras")
        tabs.addTab(
            self._create_placeholder_tab(
                "Opera\u00e7\u00f5es e m\u00e1quinas associadas ser\u00e3o configuradas numa fase posterior."
            ),
            "Opera\u00e7\u00f5es",
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header_layout)
        layout.addWidget(tabs, stretch=1)

        self.setLayout(layout)

    def _handle_back(self) -> None:
        """Call the optional back callback."""
        if self.on_back is not None:
            self.on_back()

    def _create_dados_gerais_tab(self) -> QWidget:
        """Create the general data tab."""
        tab = QWidget()
        form = QFormLayout()
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        fields = [
            ("C\u00f3digo", self.peca.codigo),
            ("Nome", self.peca.nome),
            ("Descri\u00e7\u00e3o", self.peca.descricao or ""),
            ("Tipo", get_peca_type_label(self.peca.tipo_peca)),
            ("Grupo", self.peca.grupo or ""),
            ("Ativo", self._format_bool(self.peca.ativo)),
            ("Criado em", self._format_datetime(self.peca.created_at)),
            ("Atualizado em", self._format_datetime(self.peca.updated_at)),
        ]

        for label, value in fields:
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            form.addRow(f"{label}:", value_label)

        tab.setLayout(form)
        return tab

    def _create_componentes_tab(self) -> QWidget:
        """Create the components tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        if not self.componentes:
            label = QLabel("Esta pe\u00e7a n\u00e3o tem componentes associados.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label, stretch=1)
            tab.setLayout(layout)
            return tab

        table = QTableWidget(0, len(self.COMPONENTES_HEADERS))
        table.setHorizontalHeaderLabels(self.COMPONENTES_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        table.setRowCount(len(self.componentes))
        for row_index, componente in enumerate(self.componentes):
            values = [
                str(componente.ordem),
                get_componente_type_label(componente.tipo_componente),
                self._format_componente_ref(componente),
                componente.descricao or "",
                format_quantity(componente.quantidade),
                componente.regra_quantidade or "",
                self._format_bool(componente.obrigatorio),
                self._format_bool(componente.ativo),
            ]

            for column_index, value in enumerate(values):
                table.setItem(row_index, column_index, QTableWidgetItem(value))

        layout.addWidget(table, stretch=1)
        tab.setLayout(layout)
        return tab

    def _create_placeholder_tab(self, text: str) -> QWidget:
        """Create one placeholder tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, stretch=1)
        tab.setLayout(layout)
        return tab

    def _format_componente_ref(self, componente: DefPecaComponenteResumo) -> str:
        """Return display text for one component reference."""
        if componente.def_peca_componente_id is not None:
            return self.component_labels.get(
                componente.def_peca_componente_id,
                f"Pe\u00e7a #{componente.def_peca_componente_id}",
            )

        return componente.referencia_componente or ""

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "N\u00e3o"

    def _format_datetime(self, value: datetime | None) -> str:
        """Format a datetime value for display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")
