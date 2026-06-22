"""Simple budget detail page."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import OrcamentoService
from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage
from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage
from app.ui.pages.orcamento_items_page import OrcamentoItemsPage
from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage
from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage
from app.ui.widgets.breadcrumb import Breadcrumb
from app.utils.formatters import format_currency, format_version


class OrcamentoDetailPage(QWidget):
    """Read-only detail page for a selected budget version."""

    def __init__(self, orcamento: OrcamentoResumo, on_back=None) -> None:
        super().__init__()

        self.orcamento = orcamento
        self.on_back = on_back
        self._dados_gerais_labels: dict[str, QLabel] = {}
        self._item_custeio_page: OrcamentoItemCusteioPage | None = None
        self.breadcrumb = Breadcrumb(self._build_breadcrumb_items())

        back_button = QPushButton("Voltar \u00e0 lista")
        back_button.clicked.connect(self._handle_back)

        # The breadcrumb already shows "Or\u00e7amento <c\u00f3digo>", so it doubles as the
        # header title (no separate title label, no second breadcrumb row).
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.breadcrumb, stretch=1)
        header_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.items_stack = QStackedWidget()
        self.items_page = OrcamentoItemsPage(
            orcamento.orcamento_versao_id,
            orcamento_codigo=orcamento.codigo_versao,
            on_items_changed=self._handle_items_changed,
            on_open_item_custeio=self._open_item_custeio,
            on_voltar_lista=self._handle_back,
        )
        self.items_stack.addWidget(self.items_page)

        tabs = QTabWidget()
        tabs.addTab(self._create_dados_gerais_tab(), "Dados Gerais")
        tabs.addTab(self.items_stack, "Items")
        tabs.addTab(OrcamentoCusteioPage(orcamento.orcamento_versao_id), "Custeio")
        tabs.addTab(OrcamentoValuesetPage(orcamento.orcamento_versao_id), "ValueSet")
        tabs.addTab(
            OrcamentoRelatoriosPage(
                orcamento.orcamento_versao_id, orcamento=orcamento
            ),
            "Relat\u00f3rios",
        )
        tabs.addTab(self._create_placeholder_tab("Hist\u00f3rico de altera\u00e7\u00f5es ser\u00e1 apresentado aqui."), "Hist\u00f3rico")
        # Abrir por defeito no separador "Items".
        tabs.setCurrentWidget(self.items_stack)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
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
            ("info_1", "Info 1"),
            ("info_2", "Info 2"),
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

    def _open_item_custeio(self, item: OrcamentoItemResumo) -> None:
        """Open costing for one selected item inside the Items tab."""
        if self._item_custeio_page is not None:
            self.items_stack.removeWidget(self._item_custeio_page)
            self._item_custeio_page.deleteLater()

        self._item_custeio_page = OrcamentoItemCusteioPage(
            item,
            orcamento_codigo=self.orcamento.codigo_versao,
            orcamento_versao_id=self.orcamento.orcamento_versao_id,
            on_back=self._voltar_aos_items,
        )
        self.items_stack.addWidget(self._item_custeio_page)
        self.items_stack.setCurrentWidget(self._item_custeio_page)

    def _voltar_aos_items(self) -> None:
        """Return from item costing to the items table."""
        self.items_stack.setCurrentWidget(self.items_page)
        self.items_page.carregar_items()

    def _update_dados_gerais_labels(self) -> None:
        """Update the labels in the general data tab."""
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
            "info_1": self.orcamento.info_1 or "",
            "info_2": self.orcamento.info_2 or "",
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
