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
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.componente_types import get_componente_type_label
from app.domain.orla_types import format_orla_code, get_orla_type_label
from app.domain.peca_types import COMPOSTA, get_peca_type_label, normalize_peca_type
from app.domain.regra_quantidade_types import get_regra_quantidade_label
from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_componente_service import (
    CriarDefPecaComponenteData,
    DefPecaComponenteService,
    EditarDefPecaComponenteData,
)
from app.services.def_peca_service import DefPecaService
from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog
from app.utils.formatters import format_quantity


class DefPecaDetailPage(QWidget):
    """Detail page for one reusable piece definition and its components."""

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
        self._is_composta = normalize_peca_type(peca.tipo_peca) == COMPOSTA
        self._componentes_by_row: dict[int, DefPecaComponenteResumo] = {}

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
            (
                "C\u00f3digo de orlas",
                format_orla_code(
                    self.peca.orla_c1,
                    self.peca.orla_c2,
                    self.peca.orla_l1,
                    self.peca.orla_l2,
                ),
            ),
            ("C1", get_orla_type_label(self.peca.orla_c1)),
            ("C2", get_orla_type_label(self.peca.orla_c2)),
            ("L1", get_orla_type_label(self.peca.orla_l1)),
            ("L2", get_orla_type_label(self.peca.orla_l2)),
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
        """Create the components tab with management actions."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.novo_componente_button = QPushButton("Novo Componente")
        self.novo_componente_button.clicked.connect(self.abrir_novo_componente)
        self.editar_componente_button = QPushButton("Editar Componente")
        self.editar_componente_button.clicked.connect(self.abrir_editar_componente)
        self.remover_componente_button = QPushButton("Remover Componente")
        self.remover_componente_button.clicked.connect(self.remover_componente)
        self.atualizar_componentes_button = QPushButton("Atualizar")
        self.atualizar_componentes_button.clicked.connect(self.recarregar_componentes)

        for button in (
            self.novo_componente_button,
            self.editar_componente_button,
            self.remover_componente_button,
        ):
            button.setEnabled(self._is_composta)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.novo_componente_button)
        buttons_layout.addWidget(self.editar_componente_button)
        buttons_layout.addWidget(self.remover_componente_button)
        buttons_layout.addWidget(self.atualizar_componentes_button)
        buttons_layout.addStretch()

        self.componentes_status_label = QLabel("")
        self.componentes_status_label.setObjectName("defPecaComponentesStatus")

        self.componentes_table = QTableWidget(0, len(self.COMPONENTES_HEADERS))
        self.componentes_table.setHorizontalHeaderLabels(self.COMPONENTES_HEADERS)
        self.componentes_table.verticalHeader().setVisible(False)
        self.componentes_table.setAlternatingRowColors(True)
        self.componentes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.componentes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.componentes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.componentes_table.cellDoubleClicked.connect(self._handle_componente_double_click)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.componentes_status_label)
        layout.addWidget(self.componentes_table, stretch=1)

        self._preencher_componentes()
        tab.setLayout(layout)
        return tab

    def _preencher_componentes(self) -> None:
        """Fill the components table from the current read models."""
        self._componentes_by_row = {}
        self.componentes_table.setRowCount(len(self.componentes))

        for row_index, componente in enumerate(self.componentes):
            self._componentes_by_row[row_index] = componente
            values = [
                str(componente.ordem),
                get_componente_type_label(componente.tipo_componente),
                self._format_componente_ref(componente),
                componente.descricao or "",
                format_quantity(componente.quantidade),
                get_regra_quantidade_label(componente.regra_quantidade),
                self._format_bool(componente.obrigatorio),
                self._format_bool(componente.ativo),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, componente.id)
                self.componentes_table.setItem(row_index, column_index, item)

        self.componentes_status_label.setText(self._componentes_status_text())

    def _componentes_status_text(self) -> str:
        """Return the status line for the components table."""
        if not self._is_composta:
            return "Esta pe\u00e7a \u00e9 simples e n\u00e3o tem componentes."
        if not self.componentes:
            return "Sem componentes. Use 'Novo Componente' para adicionar."
        return ""

    def recarregar_componentes(self) -> None:
        """Reload the components and piece labels from the database."""
        try:
            with SessionLocal() as session:
                self.componentes = DefPecaComponenteService(session).listar_componentes(
                    self.peca.id
                )
                all_pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.componentes_status_label.setText("Nao foi possivel carregar os componentes.")
            return

        self.component_labels = {item.id: f"{item.codigo} - {item.nome}" for item in all_pecas}
        self._preencher_componentes()

    def _get_selected_componente(self) -> DefPecaComponenteResumo | None:
        """Return the selected component read model."""
        row = self.componentes_table.currentRow()
        if row < 0:
            return None

        return self._componentes_by_row.get(row)

    def _handle_componente_double_click(self, row: int, _column: int) -> None:
        """Edit a component when the user double-clicks its row."""
        if not self._is_composta:
            return

        self.componentes_table.selectRow(row)
        self.abrir_editar_componente()

    def abrir_novo_componente(self) -> None:
        """Open the dialog to create a new component."""
        if not self._is_composta:
            return

        pecas_disponiveis = self._carregar_pecas_disponiveis()
        if pecas_disponiveis is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefPecaComponenteService(session).criar_componente(
                        CriarDefPecaComponenteData(
                            def_peca_pai_id=self.peca.id,
                            tipo_componente=form_data.tipo_componente,
                            def_peca_componente_id=form_data.def_peca_componente_id,
                            referencia_componente=form_data.referencia_componente,
                            descricao=form_data.descricao,
                            quantidade=form_data.quantidade,
                            regra_quantidade=form_data.regra_quantidade,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                        )
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("N\u00e3o foi poss\u00edvel guardar o componente.")
                return False

            saved = True
            return True

        dialog = DefPecaComponenteDialog(pecas_disponiveis, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.recarregar_componentes()
            self.componentes_status_label.setText("Componente criado.")

    def abrir_editar_componente(self) -> None:
        """Open the dialog to edit the selected component."""
        if not self._is_composta:
            return

        componente = self._get_selected_componente()
        if componente is None:
            self.componentes_status_label.setText("Selecione um componente para editar.")
            return

        pecas_disponiveis = self._carregar_pecas_disponiveis(componente)
        if pecas_disponiveis is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefPecaComponenteService(session).editar_componente(
                        componente.id,
                        EditarDefPecaComponenteData(
                            def_peca_pai_id=self.peca.id,
                            ordem=form_data.ordem,
                            tipo_componente=form_data.tipo_componente,
                            def_peca_componente_id=form_data.def_peca_componente_id,
                            referencia_componente=form_data.referencia_componente,
                            descricao=form_data.descricao,
                            quantidade=form_data.quantidade,
                            regra_quantidade=form_data.regra_quantidade,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                        ),
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("N\u00e3o foi poss\u00edvel guardar o componente.")
                return False

            saved = True
            return True

        dialog = DefPecaComponenteDialog(
            pecas_disponiveis, componente=componente, parent=self, on_save=handle_save
        )
        if dialog.exec() and saved:
            self.recarregar_componentes()
            self.componentes_status_label.setText("Componente atualizado.")

    def remover_componente(self) -> None:
        """Deactivate the selected component after confirmation."""
        if not self._is_composta:
            return

        componente = self._get_selected_componente()
        if componente is None:
            self.componentes_status_label.setText("Selecione um componente para remover.")
            return

        confirm = QMessageBox.question(
            self,
            "Remover componente",
            "Remover (desativar) o componente selecionado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                DefPecaComponenteService(session).desativar_componente(componente.id)
        except SQLAlchemyError:
            self.componentes_status_label.setText("N\u00e3o foi poss\u00edvel remover o componente.")
            return

        self.recarregar_componentes()
        self.componentes_status_label.setText("Componente removido.")

    def _carregar_pecas_disponiveis(
        self, componente: DefPecaComponenteResumo | None = None
    ) -> list[DefPecaResumo] | None:
        """Return active pieces usable as components, excluding the parent piece."""
        try:
            with SessionLocal() as session:
                all_pecas = DefPecaService(session).listar_pecas()
        except SQLAlchemyError:
            self.componentes_status_label.setText("Nao foi possivel carregar as pecas.")
            return None

        ref_id = componente.def_peca_componente_id if componente is not None else None
        return [
            peca
            for peca in all_pecas
            if peca.id != self.peca.id and (peca.ativo or peca.id == ref_id)
        ]

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
