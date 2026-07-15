"""Default margins settings page (phase 8T.1)."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.margens_padrao_types import AMBITO_CLIENTE, AMBITO_UTILIZADOR
from app.repositories.def_margem_padrao_repository import DefMargemPadraoResumo
from app.services.def_margem_padrao_service import (
    CriarMargemPadraoData,
    DefMargemPadraoService,
    EditarMargemPadraoData,
)
from app.ui.dialogs.margem_padrao_dialog import (
    TOOLTIP_VALOR_INICIAL,
    MargemPadraoDialog,
    MargemPadraoDialogData,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.utils.formatters import format_quantity

from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class MargensPadraoPage(QWidget):
    """Settings page for the default margins (Standard / customer / user)."""

    TABLE_HEADERS = [
        "Nome",
        "Margem Lucro",
        "Margem MP",
        "Margem Mão de Obra",
        "Margem Acabamentos",
        "Custos Admin.",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self.cabecalho = BarraCabecalho(
            "Margens por Defeito",
            [
                "Valores iniciais das margens dos novos orçamentos, por âmbito: "
                "Standard (geral), por cliente e por utilizador. "
                + TOOLTIP_VALOR_INICIAL
            ],
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("margensPadraoStatus")

        # Per-scope state: table + records of the visible rows.
        self._registos_por_ambito: dict[str, dict[int, DefMargemPadraoResumo]] = {
            AMBITO_CLIENTE: {},
        }
        self._tabelas: dict[str, QTableWidget] = {}
        self._mostrar_inativos: dict[str, QCheckBox] = {}

        tabs = QTabWidget()
        tabs.addTab(self._criar_tab_standard(), "Standard")
        tabs.addTab(self._criar_tab_cliente_final(), "Cliente Final")
        tabs.addTab(self._criar_tab_registos(AMBITO_CLIENTE), "Por Cliente")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addWidget(tabs, stretch=1)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self.carregar()

    # ----- Standard tab -----

    def _criar_tab_standard(self) -> QWidget:
        """Build the Standard tab (5 percent fields + Guardar)."""
        self.std_lucro_spin = self._criar_spin()
        self.std_mp_spin = self._criar_spin()
        self.std_mao_obra_spin = self._criar_spin()
        self.std_acabamentos_spin = self._criar_spin()
        self.std_administrativos_spin = self._criar_spin()

        form_layout = QFormLayout()
        form_layout.addRow("Margem Lucro", self.std_lucro_spin)
        form_layout.addRow("Margem Matérias-Primas", self.std_mp_spin)
        form_layout.addRow("Margem Mão de Obra", self.std_mao_obra_spin)
        form_layout.addRow("Margem Acabamentos", self.std_acabamentos_spin)
        form_layout.addRow("Custos Administrativos", self.std_administrativos_spin)

        self.guardar_standard_button = QPushButton("Guardar")
        self.guardar_standard_button.setToolTip(TOOLTIP_VALOR_INICIAL)
        self.guardar_standard_button.clicked.connect(self.guardar_standard)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.guardar_standard_button)
        buttons_layout.addStretch()

        tab = QWidget()
        tab_layout = QVBoxLayout()
        tab_layout.addLayout(form_layout)
        tab_layout.addLayout(buttons_layout)
        tab_layout.addStretch()
        tab.setLayout(tab_layout)
        return tab

    def guardar_standard(self) -> None:
        """Save the STANDARD record from the form."""
        try:
            with SessionLocal() as session:
                DefMargemPadraoService(session).guardar_standard(
                    EditarMargemPadraoData(
                        margem_lucro_pct=self._valor(self.std_lucro_spin),
                        margem_mp_pct=self._valor(self.std_mp_spin),
                        margem_mao_obra_pct=self._valor(self.std_mao_obra_spin),
                        margem_acabamentos_pct=self._valor(self.std_acabamentos_spin),
                        custos_administrativos_pct=self._valor(
                            self.std_administrativos_spin
                        ),
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível guardar as margens Standard.")
            return

        self.status_label.setText("Margens Standard guardadas.")

    def _criar_tab_cliente_final(self) -> QWidget:
        """Build the single shared Cliente Final margin profile."""
        self.cf_lucro_spin = self._criar_spin()
        self.cf_mp_spin = self._criar_spin()
        self.cf_mao_obra_spin = self._criar_spin()
        self.cf_acabamentos_spin = self._criar_spin()
        self.cf_administrativos_spin = self._criar_spin()
        form = QFormLayout()
        for label, spin in (
            ("Margem Lucro", self.cf_lucro_spin),
            ("Margem Matérias-Primas", self.cf_mp_spin),
            ("Margem Mão de Obra", self.cf_mao_obra_spin),
            ("Margem Acabamentos", self.cf_acabamentos_spin),
            ("Custos Administrativos", self.cf_administrativos_spin),
        ):
            form.addRow(label, spin)
        guardar = QPushButton("Guardar")
        guardar.clicked.connect(self.guardar_cliente_final)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Perfil único para orçamentos de Cliente Final."))
        layout.addLayout(form)
        layout.addWidget(guardar)
        layout.addStretch()
        tab = QWidget(); tab.setLayout(layout)
        return tab

    def guardar_cliente_final(self) -> None:
        try:
            with SessionLocal() as session:
                DefMargemPadraoService(session).guardar_cliente_final(
                    EditarMargemPadraoData(
                        margem_lucro_pct=self._valor(self.cf_lucro_spin),
                        margem_mp_pct=self._valor(self.cf_mp_spin),
                        margem_mao_obra_pct=self._valor(self.cf_mao_obra_spin),
                        margem_acabamentos_pct=self._valor(self.cf_acabamentos_spin),
                        custos_administrativos_pct=self._valor(self.cf_administrativos_spin),
                    )
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível guardar as margens Cliente Final.")
            return
        self.status_label.setText("Margens Cliente Final guardadas.")

    # ----- Per-customer / per-user tabs -----

    def _criar_tab_registos(self, ambito: str) -> QWidget:
        """Build one records tab (table + Novo/Editar/Ativar-Desativar)."""
        table = QTableWidget(0, len(self.TABLE_HEADERS))
        table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        table.horizontalHeader().setStretchLastSection(False)
        self._tabelas[ambito] = table
        ligar_persistencia_larguras(table, f"margens_{ambito}")

        novo_button = QPushButton("Novo")
        novo_button.clicked.connect(lambda: self.novo_registo(ambito))

        editar_button = QPushButton("Editar")
        editar_button.clicked.connect(lambda: self.editar_registo(ambito))

        ativar_button = QPushButton("Ativar/Desativar")
        ativar_button.clicked.connect(lambda: self.alternar_ativo(ambito))
        mostrar_inativos = QCheckBox("Mostrar inativos")
        mostrar_inativos.stateChanged.connect(lambda _=0: self.carregar())
        self._mostrar_inativos[ambito] = mostrar_inativos

        for botao in (novo_button, editar_button, ativar_button):
            botao.setToolTip(TOOLTIP_VALOR_INICIAL)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(novo_button)
        buttons_layout.addWidget(editar_button)
        buttons_layout.addWidget(ativar_button)
        buttons_layout.addWidget(mostrar_inativos)
        buttons_layout.addStretch()

        tab = QWidget()
        tab_layout = QVBoxLayout()
        tab_layout.addLayout(buttons_layout)
        tab_layout.addWidget(table, stretch=1)
        tab.setLayout(tab_layout)
        return tab

    def carregar(self) -> None:
        """Load the STANDARD form and both record tables."""
        try:
            with SessionLocal() as session:
                service = DefMargemPadraoService(session)
                standard = service.obter_standard()
                cliente_final = service.obter_cliente_final()
                clientes = service.listar_por_ambito(AMBITO_CLIENTE)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as margens por defeito.")
            return

        self._preencher_standard(standard)
        self._preencher_cliente_final(cliente_final)
        if not self._mostrar_inativos[AMBITO_CLIENTE].isChecked():
            clientes = [registo for registo in clientes if registo.ativo]
        self._preencher_tabela(AMBITO_CLIENTE, clientes)

    def _preencher_standard(self, registo: DefMargemPadraoResumo | None) -> None:
        """Reflect the STANDARD record on the form (zeros when missing)."""
        margens = registo.to_margens() if registo is not None else None
        self.std_lucro_spin.setValue(
            float(margens.margem_lucro_pct) if margens else 0.0
        )
        self.std_mp_spin.setValue(float(margens.margem_mp_pct) if margens else 0.0)
        self.std_mao_obra_spin.setValue(
            float(margens.margem_mao_obra_pct) if margens else 0.0
        )
        self.std_acabamentos_spin.setValue(
            float(margens.margem_acabamentos_pct) if margens else 0.0
        )
        self.std_administrativos_spin.setValue(
            float(margens.custos_administrativos_pct) if margens else 0.0
        )

    def _preencher_cliente_final(self, registo: DefMargemPadraoResumo | None) -> None:
        margens = registo.to_margens() if registo is not None else None
        for spin, valor in (
            (self.cf_lucro_spin, margens.margem_lucro_pct if margens else 0),
            (self.cf_mp_spin, margens.margem_mp_pct if margens else 0),
            (self.cf_mao_obra_spin, margens.margem_mao_obra_pct if margens else 0),
            (self.cf_acabamentos_spin, margens.margem_acabamentos_pct if margens else 0),
            (self.cf_administrativos_spin, margens.custos_administrativos_pct if margens else 0),
        ):
            spin.setValue(float(valor))

    def _preencher_tabela(
        self, ambito: str, registos: list[DefMargemPadraoResumo]
    ) -> None:
        """Fill one records table."""
        table = self._tabelas[ambito]
        self._registos_por_ambito[ambito] = {}
        table.setRowCount(len(registos))

        for row_index, registo in enumerate(registos):
            self._registos_por_ambito[ambito][row_index] = registo
            nome = (
                registo.cliente_nome
                if ambito == AMBITO_CLIENTE
                else registo.user_nome
            )
            values = [
                nome or "",
                self._format_pct(registo.margem_lucro_pct),
                self._format_pct(registo.margem_mp_pct),
                self._format_pct(registo.margem_mao_obra_pct),
                self._format_pct(registo.margem_acabamentos_pct),
                self._format_pct(registo.custos_administrativos_pct),
                "Sim" if registo.ativo else "Não",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, registo.id)
                table.setItem(row_index, column_index, item)

    def novo_registo(self, ambito: str) -> None:
        """Create a record for one customer/user through the dialog."""
        try:
            with SessionLocal() as session:
                service = DefMargemPadraoService(session)
                entidades = self._entidades_para_combo(service, ambito)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar a lista.")
            return

        if not entidades:
            self.status_label.setText("Sem registos disponíveis para este âmbito.")
            return

        dialog = MargemPadraoDialog(
            self,
            titulo="Novas Margens por Defeito",
            entidade_label=self._entidade_label(ambito),
            entidades=entidades,
        )
        if not dialog.exec():
            return

        dados = dialog.get_data()
        try:
            with SessionLocal() as session:
                DefMargemPadraoService(session).criar(
                    CriarMargemPadraoData(
                        ambito=ambito,
                        cliente_id=dados.entidade_id if ambito == AMBITO_CLIENTE else None,
                        user_id=dados.entidade_id if ambito == AMBITO_UTILIZADOR else None,
                        margem_lucro_pct=dados.margem_lucro_pct,
                        margem_mp_pct=dados.margem_mp_pct,
                        margem_mao_obra_pct=dados.margem_mao_obra_pct,
                        margem_acabamentos_pct=dados.margem_acabamentos_pct,
                        custos_administrativos_pct=dados.custos_administrativos_pct,
                    )
                )
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar o registo.")
            return

        self.carregar()
        self.status_label.setText("Registo de margens criado.")

    def editar_registo(self, ambito: str) -> None:
        """Edit the margins of the selected record."""
        registo = self._registo_selecionado(ambito)
        if registo is None:
            self.status_label.setText("Selecione um registo para editar.")
            return

        entidade_id = (
            registo.cliente_id if ambito == AMBITO_CLIENTE else registo.user_id
        )
        nome = (
            registo.cliente_nome if ambito == AMBITO_CLIENTE else registo.user_nome
        )
        dialog = MargemPadraoDialog(
            self,
            titulo="Editar Margens por Defeito",
            entidade_label=self._entidade_label(ambito),
            entidades=[(entidade_id, nome or str(entidade_id))],
            dados=MargemPadraoDialogData(
                entidade_id=entidade_id,
                margem_lucro_pct=registo.margem_lucro_pct,
                margem_mp_pct=registo.margem_mp_pct,
                margem_mao_obra_pct=registo.margem_mao_obra_pct,
                margem_acabamentos_pct=registo.margem_acabamentos_pct,
                custos_administrativos_pct=registo.custos_administrativos_pct,
            ),
        )
        if not dialog.exec():
            return

        dados = dialog.get_data()
        try:
            with SessionLocal() as session:
                DefMargemPadraoService(session).editar(
                    registo.id,
                    EditarMargemPadraoData(
                        margem_lucro_pct=dados.margem_lucro_pct,
                        margem_mp_pct=dados.margem_mp_pct,
                        margem_mao_obra_pct=dados.margem_mao_obra_pct,
                        margem_acabamentos_pct=dados.margem_acabamentos_pct,
                        custos_administrativos_pct=dados.custos_administrativos_pct,
                    ),
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível editar o registo.")
            return

        self.carregar()
        self.status_label.setText("Registo de margens atualizado.")

    def alternar_ativo(self, ambito: str) -> None:
        """Toggle the active flag of the selected record."""
        registo = self._registo_selecionado(ambito)
        if registo is None:
            self.status_label.setText("Selecione um registo para ativar/desativar.")
            return

        try:
            with SessionLocal() as session:
                DefMargemPadraoService(session).definir_ativo(
                    registo.id, not registo.ativo
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível alterar o registo.")
            return

        self.carregar()
        estado = "desativado" if registo.ativo else "ativado"
        self.status_label.setText(f"Registo {estado}.")

    def _registo_selecionado(self, ambito: str) -> DefMargemPadraoResumo | None:
        """Return the selected record of one tab."""
        table = self._tabelas[ambito]
        row = table.currentRow()
        if row < 0:
            return None

        return self._registos_por_ambito[ambito].get(row)

    def _entidades_para_combo(
        self, service: DefMargemPadraoService, ambito: str
    ) -> list[tuple[int, str]]:
        """List combo entries (id, label) for one scope."""
        if ambito == AMBITO_CLIENTE:
            return [
                (cliente.id, cliente.nome)
                for cliente in service.listar_clientes()
            ]

        return [
            (user.id, f"{user.nome} (@{user.username})" if user.username else user.nome)
            for user in service.listar_utilizadores_ativos()
        ]

    @staticmethod
    def _entidade_label(ambito: str) -> str:
        """Form label of the entity combo for one scope."""
        return "Cliente" if ambito == AMBITO_CLIENTE else "Utilizador"

    @staticmethod
    def _criar_spin() -> QDoubleSpinBox:
        """Build one percent field of the Standard form."""
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(-100.0, 999.99)
        spin.setSuffix(" %")
        spin.setToolTip(TOOLTIP_VALOR_INICIAL)
        return spin

    @staticmethod
    def _valor(spin: QDoubleSpinBox) -> Decimal:
        """Read one percent field as Decimal (2 dp)."""
        return Decimal(str(round(spin.value(), 2)))

    @staticmethod
    def _format_pct(valor: Decimal) -> str:
        """Format a percent value for the tables (e.g. 15 -> '15 %')."""
        return f"{format_quantity(valor)} %"
