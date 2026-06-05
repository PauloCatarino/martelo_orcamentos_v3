"""Piece definitions page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.orla_types import format_orla_code
from app.domain.peca_types import get_peca_type_label
from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_componente_service import DefPecaComponenteService
from app.services.def_peca_service import CriarDefPecaData, DefPecaService
from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog
from app.ui.pages.def_peca_detail_page import DefPecaDetailPage


class DefPecasPage(QWidget):
    """Page for listing reusable piece definitions."""

    TABLE_HEADERS = [
        "C\u00f3digo",
        "Nome",
        "Tipo",
        "Grupo",
        "Orlas",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self._pecas_by_row: dict[int, DefPecaResumo] = {}
        self._detail_page: DefPecaDetailPage | None = None

        title = QLabel("Defini\u00e7\u00f5es de Pe\u00e7as")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Biblioteca de pe\u00e7as dispon\u00edveis para m\u00f3dulos, pe\u00e7as soltas e custeio")
        subtitle.setObjectName("pageSubtitle")

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_pecas)

        self.new_button = QPushButton("Nova Pe\u00e7a")
        self.new_button.clicked.connect(self.abrir_nova_peca)

        self.open_button = QPushButton("Abrir Pe\u00e7a")
        self.open_button.clicked.connect(self.abrir_peca_selecionada)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.open_button)
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
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)

        self.list_widget = QWidget()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)
        list_layout.addWidget(title)
        list_layout.addWidget(subtitle)
        list_layout.addLayout(actions_layout)
        list_layout.addWidget(self.status_label)
        list_layout.addWidget(self.table, stretch=1)
        self.list_widget.setLayout(list_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.list_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.setLayout(layout)
        self.carregar_pecas()

    def carregar_pecas(self, select_codigo: str | None = None) -> None:
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
        if select_codigo:
            self._select_peca_by_codigo(select_codigo)

        if not pecas:
            self.status_label.setText("Sem definicoes de pecas para mostrar.")

    def abrir_nova_peca(self) -> None:
        """Open the new piece definition dialog."""
        created_codigo: str | None = None

        def handle_save(form_data) -> bool:
            nonlocal created_codigo

            try:
                with SessionLocal() as session:
                    DefPecaService(session).criar_peca(
                        CriarDefPecaData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            grupo=form_data.grupo,
                            tipo_peca=form_data.tipo_peca,
                            ativo=form_data.ativo,
                        )
                    )
            except IntegrityError:
                dialog.set_error("J\u00e1 existe uma pe\u00e7a com esse c\u00f3digo.")
                return False
            except (SQLAlchemyError, ValueError):
                dialog.set_error("N\u00e3o foi poss\u00edvel criar a pe\u00e7a.")
                return False

            created_codigo = form_data.codigo
            return True

        dialog = NovaDefPecaDialog(self, on_save=handle_save)

        if not dialog.exec():
            return

        if created_codigo is None:
            return

        self.carregar_pecas(select_codigo=created_codigo)
        self.status_label.setText(f"Pe\u00e7a {created_codigo} criada.")

    def _preencher_tabela(self, pecas: list[DefPecaResumo]) -> None:
        """Fill the table with piece definition read models."""
        self._pecas_by_row = {}
        self.table.setRowCount(len(pecas))

        for row_index, peca in enumerate(pecas):
            self._pecas_by_row[row_index] = peca
            values = [
                peca.codigo,
                peca.nome,
                get_peca_type_label(peca.tipo_peca),
                peca.grupo or "",
                format_orla_code(peca.orla_c1, peca.orla_c2, peca.orla_l1, peca.orla_l2),
                "Sim" if peca.ativo else "N\u00e3o",
            ]

            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column_index == 0:
                    table_item.setData(Qt.ItemDataRole.UserRole, peca.id)
                self.table.setItem(row_index, column_index, table_item)

    def abrir_peca_selecionada(self) -> None:
        """Open the currently selected piece definition detail."""
        peca = self._get_selected_peca()
        if peca is None:
            self.status_label.setText("Selecione uma pe\u00e7a para abrir.")
            return

        try:
            with SessionLocal() as session:
                componentes = DefPecaComponenteService(session).listar_componentes(peca.id)
                all_pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel abrir a definicao de peca.")
            return

        component_labels = {
            item.id: f"{item.codigo} - {item.nome}"
            for item in all_pecas
        }

        self.status_label.clear()
        self._show_detail_page(peca, componentes, component_labels)

    def _show_detail_page(
        self,
        peca: DefPecaResumo,
        componentes: list,
        component_labels: dict[int, str],
    ) -> None:
        """Replace the list with the piece definition detail page."""
        if self._detail_page is not None:
            self.stack.removeWidget(self._detail_page)
            self._detail_page.deleteLater()

        self._detail_page = DefPecaDetailPage(
            peca,
            componentes=componentes,
            component_labels=component_labels,
            on_back=self._voltar_a_lista,
        )
        self.stack.addWidget(self._detail_page)
        self.stack.setCurrentWidget(self._detail_page)

    def _voltar_a_lista(self) -> None:
        """Return to the already-loaded piece definition table."""
        self.stack.setCurrentWidget(self.list_widget)

    def _get_selected_peca(self) -> DefPecaResumo | None:
        """Return the selected piece definition read model."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._pecas_by_row.get(row)

    def _select_peca_by_codigo(self, codigo: str) -> None:
        """Select one table row by piece code."""
        for row_index, peca in self._pecas_by_row.items():
            if peca.codigo == codigo:
                self.table.selectRow(row_index)
                return

    def _handle_row_double_click(self, row: int, _column: int) -> None:
        """Open a piece definition when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_peca_selecionada()
