"""Dialog to manage the CNC area price tiers of a machine (phase 8S.0)."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.def_maquina_escalao_area_repository import (
    DefMaquinaEscalaoAreaResumo,
)
from app.services.def_maquina_escalao_area_service import (
    CriarEscalaoAreaData,
    DefMaquinaEscalaoAreaService,
    EditarEscalaoAreaData,
)
from app.ui.dialogs.escalao_area_dialog import EscalaoAreaDialog
from app.ui.widgets.table_item import criar_item_tabela
from app.utils.formatters import format_currency


class EscaloesAreaDialog(QDialog):
    """Modal dialog to list, add, edit and (de)activate a machine's area tiers."""

    HEADERS = ["Nível", "Área máx. (m²)", "Preço/peça STD", "Preço/peça SERIE", "Ativo"]

    def __init__(self, maquina_id: int, maquina_label: str = "", parent=None) -> None:
        super().__init__(parent)

        self.maquina_id = maquina_id
        self._escaloes_by_row: dict[int, DefMaquinaEscalaoAreaResumo] = {}

        self.setWindowTitle("Escalões de Área (CNC)")
        self.setModal(True)
        self.setMinimumSize(640, 420)

        info = QLabel(
            "Escalões de preço por área para CNC. Cada escalão aplica-se a peças "
            "com área até ao limite; o último escalão pode ficar sem limite. "
            f"{maquina_label}".strip()
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666666; font-size: 11px;")

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.status_label = QLabel("")
        self.status_label.setObjectName("escaloesAreaStatus")

        self.add_button = QPushButton("Adicionar")
        self.add_button.clicked.connect(self.abrir_novo_escalao)
        self.edit_button = QPushButton("Editar")
        self.edit_button.clicked.connect(self.abrir_editar_escalao)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_escalao_ativo)
        self.close_button = QPushButton("Fechar")
        self.close_button.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addWidget(self.add_button)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.toggle_button)
        actions.addStretch()
        actions.addWidget(self.close_button)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.status_label)
        layout.addLayout(actions)
        self.setLayout(layout)

        self.carregar()

    def carregar(self) -> None:
        """Reload the area tiers from the database."""
        try:
            with SessionLocal() as session:
                escaloes = DefMaquinaEscalaoAreaService(
                    session
                ).listar_escaloes_da_maquina(self.maquina_id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar os escalões.")
            return

        self._preencher(escaloes)

    def _preencher(self, escaloes: list[DefMaquinaEscalaoAreaResumo]) -> None:
        """Fill the tiers table."""
        self._escaloes_by_row = {}
        self.table.setRowCount(len(escaloes))

        for row_index, escalao in enumerate(escaloes):
            self._escaloes_by_row[row_index] = escalao
            values = [
                str(escalao.nivel),
                self._format_area(escalao.area_max_m2),
                format_currency(escalao.preco_peca_std),
                format_currency(escalao.preco_peca_serie),
                "Sim" if escalao.ativo else "Não",
            ]
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, criar_item_tabela(value))

    @staticmethod
    def _format_area(value) -> str:
        """Format an area limit with 2 decimals and the m2 unit (or "Sem limite")."""
        if value is None:
            return "Sem limite"

        texto = format(value.quantize(Decimal("0.01")), "f").replace(".", ",")
        return f"{texto} m2"

    def _get_selected(self) -> DefMaquinaEscalaoAreaResumo | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._escaloes_by_row.get(row)

    def _proximo_nivel(self) -> int:
        if not self._escaloes_by_row:
            return 1

        return max(e.nivel for e in self._escaloes_by_row.values()) + 1

    def abrir_novo_escalao(self) -> None:
        """Open the dialog to add a new tier."""
        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    DefMaquinaEscalaoAreaService(session).adicionar_escalao(
                        CriarEscalaoAreaData(
                            def_maquina_id=self.maquina_id,
                            nivel=form_data.nivel,
                            area_max_m2=form_data.area_max_m2,
                            preco_peca_std=form_data.preco_peca_std,
                            preco_peca_serie=form_data.preco_peca_serie,
                            ativo=form_data.ativo,
                        )
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível guardar o escalão.")
                return False

            saved = True
            return True

        dialog = EscalaoAreaDialog(
            proximo_nivel=self._proximo_nivel(), parent=self, on_save=handle_save
        )
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Escalão adicionado.")

    def abrir_editar_escalao(self) -> None:
        """Open the dialog to edit the selected tier."""
        escalao = self._get_selected()
        if escalao is None:
            self.status_label.setText("Selecione um escalão para editar.")
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    DefMaquinaEscalaoAreaService(session).editar_escalao(
                        escalao.id,
                        EditarEscalaoAreaData(
                            nivel=form_data.nivel,
                            area_max_m2=form_data.area_max_m2,
                            preco_peca_std=form_data.preco_peca_std,
                            preco_peca_serie=form_data.preco_peca_serie,
                            ativo=form_data.ativo,
                        ),
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("Não foi possível guardar o escalão.")
                return False

            saved = True
            return True

        dialog = EscalaoAreaDialog(escalao=escalao, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Escalão atualizado.")

    def alternar_escalao_ativo(self) -> None:
        """Toggle the active state of the selected tier (never deletes)."""
        escalao = self._get_selected()
        if escalao is None:
            self.status_label.setText("Selecione um escalão.")
            return

        try:
            with SessionLocal() as session:
                service = DefMaquinaEscalaoAreaService(session)
                if escalao.ativo:
                    service.desativar_escalao(escalao.id)
                else:
                    service.ativar_escalao(escalao.id)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível alterar o escalão.")
            return

        self.carregar()
        self.status_label.setText("Escalão atualizado.")

    def _handle_double_click(self, _row: int, _column: int) -> None:
        self.abrir_editar_escalao()
