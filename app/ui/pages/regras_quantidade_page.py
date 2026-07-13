"""Quantity rules settings page (phase 8T.5.0)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
from app.repositories.def_regra_quantidade_repository import DefRegraQuantidadeResumo
from app.services.def_regra_quantidade_service import (
    CriarRegraQuantidadeData,
    DefRegraQuantidadeService,
    EditarRegraQuantidadeData,
)
from app.ui.dialogs.regra_quantidade_dialog import (
    RegraQuantidadeDialog,
    RegraQuantidadeDialogData,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class RegrasQuantidadePage(QWidget):
    """Settings page to manage configurable quantity rules."""

    TABLE_HEADERS = ["Código", "Nome", "Expressão", "Descrição/Tooltip", "Ativo"]

    def __init__(self) -> None:
        super().__init__()

        self.cabecalho = BarraCabecalho(
            "Regras de Quantidade",
            [
                "Regras (expressões) que calculam a quantidade de ferragens a partir "
                "das dimensões da peça principal (COMP, LARG, ESP) e da quantidade "
                "QT_PAI. Aqui apenas se definem e validam; a ligação aos componentes "
                "vem numa fase seguinte."
            ],
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("regrasQuantidadeStatus")

        self._registos_por_linha: dict[int, DefRegraQuantidadeResumo] = {}

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        ligar_persistencia_larguras(self.table, "regras_quantidade")

        self.nova_button = QPushButton("Nova Regra")
        self.nova_button.clicked.connect(self.nova_regra)

        self.editar_button = QPushButton("Editar Regra")
        self.editar_button.clicked.connect(self.editar_regra)

        self.ativar_button = QPushButton("Ativar/Desativar")
        self.ativar_button.clicked.connect(self.alternar_ativo)
        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(lambda _=0: self.carregar())

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.nova_button)
        buttons_layout.addWidget(self.editar_button)
        buttons_layout.addWidget(self.ativar_button)
        buttons_layout.addWidget(self.mostrar_inativas_check)
        buttons_layout.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self.carregar()

    def carregar(self) -> None:
        """Load the quantity rules into the table."""
        try:
            with SessionLocal() as session:
                registos = DefRegraQuantidadeService(session).listar()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as regras.")
            return

        if not self.mostrar_inativas_check.isChecked():
            registos = [registo for registo in registos if registo.ativo]

        self._preencher_tabela(registos)

    def _preencher_tabela(self, registos: list[DefRegraQuantidadeResumo]) -> None:
        """Fill the rules table."""
        self._registos_por_linha = {}
        self.table.setRowCount(len(registos))

        for row_index, registo in enumerate(registos):
            self._registos_por_linha[row_index] = registo
            values = [
                registo.codigo,
                registo.nome,
                registo.expressao,
                registo.descricao or "",
                "Sim" if registo.ativo else "Não",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if registo.descricao:
                    item.setToolTip(registo.descricao)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, registo.id)
                self.table.setItem(row_index, column_index, item)

        if not registos:
            self.status_label.setText("Sem regras de quantidade definidas.")

    def nova_regra(self) -> None:
        """Create a quantity rule through the dialog."""
        dialog = RegraQuantidadeDialog(self, titulo="Nova Regra de Quantidade")
        if not dialog.exec():
            return

        dados = dialog.get_data()
        try:
            with SessionLocal() as session:
                DefRegraQuantidadeService(session).criar(
                    CriarRegraQuantidadeData(
                        codigo=dados.codigo,
                        nome=dados.nome,
                        expressao=dados.expressao,
                        descricao=dados.descricao,
                        ativo=dados.ativo,
                    )
                )
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar a regra.")
            return

        self.carregar()
        self.status_label.setText("Regra de quantidade criada.")

    def editar_regra(self) -> None:
        """Edit the selected quantity rule."""
        registo = self._registo_selecionado()
        if registo is None:
            self.status_label.setText("Selecione uma regra para editar.")
            return

        dialog = RegraQuantidadeDialog(
            self,
            titulo="Editar Regra de Quantidade",
            dados=RegraQuantidadeDialogData(
                codigo=registo.codigo,
                nome=registo.nome,
                expressao=registo.expressao,
                descricao=registo.descricao,
                ativo=registo.ativo,
            ),
        )
        if not dialog.exec():
            return

        dados = dialog.get_data()
        try:
            with SessionLocal() as session:
                DefRegraQuantidadeService(session).editar(
                    registo.id,
                    EditarRegraQuantidadeData(
                        nome=dados.nome,
                        expressao=dados.expressao,
                        descricao=dados.descricao,
                    ),
                )
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível editar a regra.")
            return

        self.carregar()
        self.status_label.setText("Regra de quantidade atualizada.")

    def alternar_ativo(self) -> None:
        """Toggle the active flag of the selected rule."""
        registo = self._registo_selecionado()
        if registo is None:
            self.status_label.setText("Selecione uma regra para ativar/desativar.")
            return

        try:
            with SessionLocal() as session:
                DefRegraQuantidadeService(session).definir_ativo(
                    registo.id, not registo.ativo
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível alterar a regra.")
            return

        self.carregar()
        estado = "desativada" if registo.ativo else "ativada"
        self.status_label.setText(f"Regra {estado}.")

    def _registo_selecionado(self) -> DefRegraQuantidadeResumo | None:
        """Return the selected rule, or None."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._registos_por_linha.get(row)

    def selecionar_regra_por_id(self, regra_id: int) -> None:
        """Reload and select one rule from the audit page."""
        self.carregar()
        for row, regra in self._registos_por_linha.items():
            if regra.id == regra_id:
                self.table.selectRow(row)
                self.table.scrollToItem(self.table.item(row, 0))
                return
        self.status_label.setText("A regra indicada já não existe.")
