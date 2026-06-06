"""Simple budget detail page."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import OrcamentoService
from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage
from app.ui.pages.orcamento_items_page import OrcamentoItemsPage
from app.ui.widgets.breadcrumb import Breadcrumb
from app.utils.formatters import format_currency, format_version


class OrcamentoDetailPage(QWidget):
    """Read-only detail page for a selected budget version."""

    def __init__(self, orcamento: OrcamentoResumo, on_back=None) -> None:
        super().__init__()

        self.orcamento = orcamento
        self.on_back = on_back
        self._dados_gerais_labels: dict[str, QLabel] = {}
        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())

        self.title_label = QLabel(f"Or\u00e7amento {orcamento.codigo_versao}")
        self.title_label.setObjectName("orcamentoDetailTitle")

        back_button = QPushButton("Voltar \u00e0 lista")
        back_button.clicked.connect(self._handle_back)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.title_label, stretch=1)
        header_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignRight)

        tabs = QTabWidget()
        tabs.addTab(self._create_dados_gerais_tab(), "Dados Gerais")
        tabs.addTab(
            OrcamentoItemsPage(
                orcamento.orcamento_versao_id,
                orcamento_codigo=orcamento.codigo_versao,
                on_items_changed=self._handle_items_changed,
            ),
            "Items",
        )
        tabs.addTab(OrcamentoCusteioPage(orcamento.orcamento_versao_id), "Custeio")
        tabs.addTab(self._create_placeholder_tab("Resumo do or\u00e7amento ser\u00e1 apresentado aqui."), "Resumo")
        tabs.addTab(self._create_placeholder_tab("Hist\u00f3rico de altera\u00e7\u00f5es ser\u00e1 apresentado aqui."), "Hist\u00f3rico")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header_layout)
        layout.addWidget(self.breadcrumb)
        layout.addWidget(tabs, stretch=1)

        self.setLayout(layout)

    def _handle_back(self) -> None:
        """Call the optional back callback."""
        if self.on_back is not None:
            self.on_back()

    def _create_dados_gerais_tab(self) -> QWidget:
        """Create the general data tab."""
        tab = QWidget()
        form_layout = QFormLayout()

        for key, label in [
            ("codigo_versao", "C\u00f3digo da vers\u00e3o"),
            ("ano", "Ano"),
            ("num_orcamento", "N\u00ba Or\u00e7amento"),
            ("numero_versao", "Vers\u00e3o"),
            ("cliente_nome", "Cliente"),
            ("obra", "Obra"),
            ("descricao", "Descri\u00e7\u00e3o"),
            ("localizacao", "Localiza\u00e7\u00e3o"),
            ("ref_cliente", "Refer\u00eancia cliente"),
            ("estado", "Estado"),
            ("preco_total", "Pre\u00e7o total"),
            ("created_at", "Criado em"),
        ]:
            value_label = QLabel("")
            self._dados_gerais_labels[key] = value_label
            form_layout.addRow(label, value_label)

        self._update_dados_gerais_labels()

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addStretch()
        tab.setLayout(layout)

        return tab

    def _handle_items_changed(self) -> None:
        """Refresh general budget data after items change."""
        try:
            with SessionLocal() as session:
                orcamento = OrcamentoService(session).get_orcamento_by_versao_id(
                    self.orcamento.orcamento_versao_id
                )
        except SQLAlchemyError:
            return

        if orcamento is None:
            return

        self.orcamento = orcamento
        self._update_dados_gerais_labels()

    def _update_dados_gerais_labels(self) -> None:
        """Update the labels in the general data tab."""
        self.title_label.setText(f"Or\u00e7amento {self.orcamento.codigo_versao}")
        self.breadcrumb.set_items(self._build_breadcrumb_items())
        values = {
            "codigo_versao": self.orcamento.codigo_versao,
            "ano": str(self.orcamento.ano),
            "num_orcamento": self.orcamento.num_orcamento,
            "numero_versao": format_version(self.orcamento.numero_versao),
            "cliente_nome": self.orcamento.cliente_nome,
            "obra": self.orcamento.obra or "",
            "descricao": self.orcamento.descricao or "",
            "localizacao": self.orcamento.localizacao or "",
            "ref_cliente": self.orcamento.ref_cliente or "",
            "estado": self.orcamento.estado,
            "preco_total": format_currency(self.orcamento.preco_total),
            "created_at": self._format_datetime(self.orcamento.created_at),
        }

        for key, value in values.items():
            label = self._dados_gerais_labels.get(key)
            if label is not None:
                label.setText(value)

    def _build_breadcrumb_items(self) -> list[str]:
        """Return breadcrumb items for the active budget."""
        return [f"Or\u00e7amento {self.orcamento.codigo_versao}"]

    def _create_placeholder_tab(self, text: str) -> QWidget:
        """Create a simple placeholder tab."""
        tab = QWidget()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(label)
        tab.setLayout(layout)

        return tab

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        """Format a datetime value for display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")
