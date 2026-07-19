"""Operations / machines catalog page (read-only)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.def_maquina_repository import DefMaquinaResumo
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.services.def_maquina_service import (
    CriarDefMaquinaData,
    DefMaquinaService,
    EditarDefMaquinaData,
)
from app.services.def_operacao_service import (
    CriarDefOperacaoData,
    DefOperacaoService,
    EditarDefOperacaoData,
)
from app.ui.dialogs.escaloes_area_dialog import EscaloesAreaDialog
from app.ui.dialogs.maquina_dialog import MaquinaDialog
from app.ui.dialogs.operacao_dialog import OperacaoDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.ui.widgets.simulador_cnc_widget import (
    SimuladorCncWidget,
    carregar_maquinas_simulacao,
)
from app.utils.formatters import format_currency, format_quantity


class OperacoesMaquinasPage(QWidget):
    """Read-only page listing production operations and machines."""

    OPERACOES_HEADERS = [
        "Código",
        "Nome",
        "Tipo",
        "Unidade cálculo",
        "Máquina",
        "Tempo base",
        "Tempo setup",
        "Custo/hora",
        "Custo mínimo",
        "Ativo",
    ]

    MAQUINAS_HEADERS = [
        "Código",
        "Nome",
        "Tipo",
        "Métodos",
        "Custo/hora STD",
        "Custo/hora SERIE",
        "€/ML STD",
        "€/ML SERIE",
        "€/ML rasgo STD",
        "€/ML rasgo SERIE",
        "€/furo STD",
        "€/furo SERIE",
        "€/m² face STD",
        "€/m² face SERIE",
        "€/lado STD",
        "€/lado SERIE",
        "Ativo",
    ]

    def __init__(self, on_back=None) -> None:
        super().__init__()

        self.on_back = on_back

        self.cabecalho = BarraCabecalho(
            "Operações / Máquinas / Simulador",
            [
                "Catálogo de operações e máquinas usado no custeio de corte, "
                "orlagem, CNC, revestimento, montagem e mão de obra. Cada "
                "máquina CNC declara os métodos de cálculo que permite; o "
                "separador Simulador mostra o custo de cada método com as "
                "tarifas reais."
            ],
        )

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(
            lambda _state=0: self.carregar()
        )
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.mostrar_inativas_check)
        actions_layout.addStretch()
        actions_layout.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("operacoesMaquinasStatus")

        self._operacoes_by_row: dict[int, DefOperacaoResumo] = {}
        self._maquinas_by_row: dict[int, DefMaquinaResumo] = {}

        self.operacoes_table = self._create_table(self.OPERACOES_HEADERS)
        self.maquinas_table = self._create_table(self.MAQUINAS_HEADERS)
        ligar_persistencia_larguras(self.operacoes_table, "operacoes")
        ligar_persistencia_larguras(self.maquinas_table, "maquinas")

        self.simulador_widget = SimuladorCncWidget()

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_operacoes_tab(), "Operações")
        self.tabs.addTab(self._create_maquinas_tab(), "Máquinas")
        self.tabs.addTab(self.simulador_widget, "Simulador")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Reload both operations and machines from the database."""
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                operacoes = DefOperacaoService(session).listar_operacoes()
                maquinas = DefMaquinaService(session).listar_maquinas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar operacoes e maquinas.")
            return

        if not self.mostrar_inativas_check.isChecked():
            operacoes = [operacao for operacao in operacoes if operacao.ativo]
            maquinas = [maquina for maquina in maquinas if maquina.ativo]

        maquina_labels = {maquina.id: f"{maquina.codigo} - {maquina.nome}" for maquina in maquinas}
        self._preencher_operacoes(operacoes, maquina_labels)
        self._preencher_maquinas(maquinas)
        self._atualizar_simulador()

    def _atualizar_simulador(self) -> None:
        """Refresh the simulator tab with the real machine tariffs."""
        try:
            self.simulador_widget.definir_maquinas(carregar_maquinas_simulacao())
        except SQLAlchemyError:
            pass  # the catalog tabs already reported the load problem

    def _preencher_operacoes(
        self,
        operacoes: list[DefOperacaoResumo],
        maquina_labels: dict[int, str],
    ) -> None:
        """Fill the operations table."""
        self._operacoes_by_row = {}
        self.operacoes_table.setRowCount(len(operacoes))

        for row_index, operacao in enumerate(operacoes):
            self._operacoes_by_row[row_index] = operacao
            values = [
                operacao.codigo,
                operacao.nome,
                operacao.tipo_operacao or "",
                operacao.unidade_calculo or "",
                self._format_maquina(operacao.maquina_id, maquina_labels),
                format_quantity(operacao.tempo_base),
                format_quantity(operacao.tempo_setup),
                format_currency(operacao.custo_hora),
                format_currency(operacao.custo_minimo),
                self._format_bool(operacao.ativo),
            ]

            for column_index, value in enumerate(values):
                self.operacoes_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _preencher_maquinas(self, maquinas: list[DefMaquinaResumo]) -> None:
        """Fill the machines table."""
        self._maquinas_by_row = {}
        self.maquinas_table.setRowCount(len(maquinas))

        for row_index, maquina in enumerate(maquinas):
            self._maquinas_by_row[row_index] = maquina
            values = [
                maquina.codigo,
                maquina.nome,
                maquina.tipo or "",
                self._format_metodos(maquina),
                format_currency(maquina.custo_hora),
                format_currency(maquina.custo_hora_serie),
                format_currency(maquina.preco_ml_std),
                format_currency(maquina.preco_ml_serie),
                format_currency(maquina.preco_rasgo_ml_std),
                format_currency(maquina.preco_rasgo_ml_serie),
                format_currency(maquina.preco_furo_std),
                format_currency(maquina.preco_furo_serie),
                format_currency(maquina.preco_m2_face_std),
                format_currency(maquina.preco_m2_face_serie),
                self._format_lados(
                    maquina.preco_lado_curto_std, maquina.preco_lado_longo_std
                ),
                self._format_lados(
                    maquina.preco_lado_curto_serie, maquina.preco_lado_longo_serie
                ),
                self._format_bool(maquina.ativo),
            ]

            for column_index, value in enumerate(values):
                self.maquinas_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _create_operacoes_tab(self) -> QWidget:
        """Create the operations tab with management actions."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.nova_operacao_button = QPushButton("Nova Operação")
        self.nova_operacao_button.clicked.connect(self.abrir_nova_operacao)
        self.editar_operacao_button = QPushButton("Editar Operação")
        self.editar_operacao_button.clicked.connect(self.abrir_editar_operacao)
        self.toggle_operacao_button = QPushButton("Ativar/Desativar")
        self.toggle_operacao_button.clicked.connect(self.alternar_operacao_ativa)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.nova_operacao_button)
        buttons_layout.addWidget(self.editar_operacao_button)
        buttons_layout.addWidget(self.toggle_operacao_button)
        buttons_layout.addStretch()

        self.operacoes_table.cellDoubleClicked.connect(self._handle_operacao_double_click)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.operacoes_table, stretch=1)
        tab.setLayout(layout)
        return tab

    def _get_selected_operacao(self) -> DefOperacaoResumo | None:
        """Return the selected operation read model."""
        row = self.operacoes_table.currentRow()
        if row < 0:
            return None

        return self._operacoes_by_row.get(row)

    def abrir_operacao_por_id(self, operacao_id: int) -> None:
        """Show and select one operation, including inactive operations."""
        self.mostrar_inativas_check.setChecked(True)
        self.carregar()
        self.tabs.setCurrentIndex(0)
        for row, operacao in self._operacoes_by_row.items():
            if operacao.id == operacao_id:
                self.operacoes_table.selectRow(row)
                self.operacoes_table.scrollToItem(
                    self.operacoes_table.item(row, 0)
                )
                return
        self.status_label.setText("A operação indicada já não existe.")

    def _handle_operacao_double_click(self, row: int, _column: int) -> None:
        """Edit an operation when the user double-clicks its row."""
        self.operacoes_table.selectRow(row)
        self.abrir_editar_operacao()

    def abrir_nova_operacao(self) -> None:
        """Open the dialog to create a new operation."""
        maquinas = self._carregar_maquinas_disponiveis()
        if maquinas is None:
            return

        created_codigo: str | None = None

        def handle_save(form_data) -> bool:
            nonlocal created_codigo

            try:
                with SessionLocal() as session:
                    DefOperacaoService(session).criar_operacao(
                        CriarDefOperacaoData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            tipo_operacao=form_data.tipo_operacao,
                            unidade_calculo=form_data.unidade_calculo,
                            tempo_base=form_data.tempo_base,
                            tempo_setup=form_data.tempo_setup,
                            custo_hora=form_data.custo_hora,
                            custo_minimo=form_data.custo_minimo,
                            maquina_id=form_data.maquina_id,
                            ativo=form_data.ativo,
                            observacoes=form_data.observacoes,
                        )
                    )
            except IntegrityError:
                dialog.set_error("Já existe uma operação com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._operacao_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a operação.")
                return False

            created_codigo = form_data.codigo
            return True

        dialog = OperacaoDialog(maquinas, parent=self, on_save=handle_save)
        if dialog.exec() and created_codigo is not None:
            self.carregar()
            self.status_label.setText(f"Operação {created_codigo} criada.")

    def abrir_editar_operacao(self) -> None:
        """Open the dialog to edit the selected operation."""
        operacao = self._get_selected_operacao()
        if operacao is None:
            self.status_label.setText("Selecione uma operação para editar.")
            return

        maquinas = self._carregar_maquinas_disponiveis(operacao)
        if maquinas is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefOperacaoService(session).editar_operacao(
                        operacao.id,
                        EditarDefOperacaoData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            tipo_operacao=form_data.tipo_operacao,
                            unidade_calculo=form_data.unidade_calculo,
                            tempo_base=form_data.tempo_base,
                            tempo_setup=form_data.tempo_setup,
                            custo_hora=form_data.custo_hora,
                            custo_minimo=form_data.custo_minimo,
                            maquina_id=form_data.maquina_id,
                            ativo=form_data.ativo,
                            observacoes=form_data.observacoes,
                        ),
                    )
            except IntegrityError:
                dialog.set_error("Já existe uma operação com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._operacao_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a operação.")
                return False

            saved = True
            return True

        dialog = OperacaoDialog(maquinas, operacao=operacao, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText(f"Operação {operacao.codigo} atualizada.")

    def alternar_operacao_ativa(self) -> None:
        """Toggle the active state of the selected operation after confirmation."""
        operacao = self._get_selected_operacao()
        if operacao is None:
            self.status_label.setText("Selecione uma operação para ativar/desativar.")
            return

        acao = "desativar" if operacao.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} a operação {operacao.codigo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefOperacaoService(session)
                if operacao.ativo:
                    service.desativar_operacao(operacao.id)
                else:
                    service.ativar_operacao(operacao.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado da operação.")
            return

        estado = "desativada" if operacao.ativo else "reativada"
        self.carregar()
        self.status_label.setText(f"Operação {operacao.codigo} {estado}.")

    def _operacao_error_message(self, error: ValueError) -> str:
        """Return a friendly message for an operation service error."""
        if "existe" in str(error).lower():
            return "Já existe uma operação com esse código."

        return "Não foi possível guardar a operação."

    def _carregar_maquinas_disponiveis(
        self, operacao: DefOperacaoResumo | None = None
    ) -> list[DefMaquinaResumo] | None:
        """Return active machines for the combo, keeping the current one if inactive."""
        try:
            with SessionLocal() as session:
                service = DefMaquinaService(session)
                maquinas = service.listar_maquinas_ativas()
                atual = None
                if operacao is not None and operacao.maquina_id is not None:
                    if not any(maquina.id == operacao.maquina_id for maquina in maquinas):
                        atual = service.obter_por_id(operacao.maquina_id)
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as maquinas.")
            return None

        if atual is not None:
            return [atual, *maquinas]

        return maquinas

    def _create_maquinas_tab(self) -> QWidget:
        """Create the machines tab with management actions."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.nova_maquina_button = QPushButton("Nova Máquina")
        self.nova_maquina_button.clicked.connect(self.abrir_nova_maquina)
        self.editar_maquina_button = QPushButton("Editar Máquina")
        self.editar_maquina_button.clicked.connect(self.abrir_editar_maquina)
        self.toggle_maquina_button = QPushButton("Ativar/Desativar")
        self.toggle_maquina_button.clicked.connect(self.alternar_maquina_ativa)
        self.escaloes_maquina_button = QPushButton("Escalões de área (CNC)…")
        self.escaloes_maquina_button.clicked.connect(self.abrir_escaloes_maquina)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.nova_maquina_button)
        buttons_layout.addWidget(self.editar_maquina_button)
        buttons_layout.addWidget(self.toggle_maquina_button)
        buttons_layout.addWidget(self.escaloes_maquina_button)
        buttons_layout.addStretch()

        self.maquinas_table.cellDoubleClicked.connect(self._handle_maquina_double_click)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.maquinas_table, stretch=1)
        tab.setLayout(layout)
        return tab

    def _get_selected_maquina(self) -> DefMaquinaResumo | None:
        """Return the selected machine read model."""
        row = self.maquinas_table.currentRow()
        if row < 0:
            return None

        return self._maquinas_by_row.get(row)

    def _handle_maquina_double_click(self, row: int, _column: int) -> None:
        """Edit a machine when the user double-clicks its row."""
        self.maquinas_table.selectRow(row)
        self.abrir_editar_maquina()

    def abrir_nova_maquina(self) -> None:
        """Open the dialog to create a new machine."""
        created_codigo: str | None = None

        def handle_save(form_data) -> bool:
            nonlocal created_codigo

            try:
                with SessionLocal() as session:
                    DefMaquinaService(session).criar_maquina(
                        CriarDefMaquinaData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            tipo=form_data.tipo,
                            custo_hora=form_data.custo_hora,
                            custo_hora_serie=form_data.custo_hora_serie,
                            preco_ml_std=form_data.preco_ml_std,
                            preco_ml_serie=form_data.preco_ml_serie,
                            permite_rasgos=form_data.permite_rasgos,
                            preco_rasgo_ml_std=form_data.preco_rasgo_ml_std,
                            preco_rasgo_ml_serie=form_data.preco_rasgo_ml_serie,
                            preco_lado_curto_std=form_data.preco_lado_curto_std,
                            preco_lado_curto_serie=form_data.preco_lado_curto_serie,
                            preco_lado_longo_std=form_data.preco_lado_longo_std,
                            preco_lado_longo_serie=form_data.preco_lado_longo_serie,
                            limite_lado_mm=form_data.limite_lado_mm,
                            custo_setup_peca_std=form_data.custo_setup_peca_std,
                            custo_setup_peca_serie=form_data.custo_setup_peca_serie,
                            permite_furacao=form_data.permite_furacao,
                            permite_pocket=form_data.permite_pocket,
                            permite_escaloes_area=form_data.permite_escaloes_area,
                            preco_furo_std=form_data.preco_furo_std,
                            preco_furo_serie=form_data.preco_furo_serie,
                            preco_m2_face_std=form_data.preco_m2_face_std,
                            preco_m2_face_serie=form_data.preco_m2_face_serie,
                            ativo=form_data.ativo,
                            observacoes=form_data.observacoes,
                        )
                    )
            except IntegrityError:
                dialog.set_error("Já existe uma máquina com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._maquina_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a máquina.")
                return False

            created_codigo = form_data.codigo
            return True

        dialog = MaquinaDialog(parent=self, on_save=handle_save)
        if dialog.exec() and created_codigo is not None:
            self.carregar()
            self.status_label.setText(f"Máquina {created_codigo} criada.")

    def abrir_editar_maquina(self) -> None:
        """Open the dialog to edit the selected machine."""
        maquina = self._get_selected_maquina()
        if maquina is None:
            self.status_label.setText("Selecione uma máquina para editar.")
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefMaquinaService(session).editar_maquina(
                        maquina.id,
                        EditarDefMaquinaData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            tipo=form_data.tipo,
                            custo_hora=form_data.custo_hora,
                            custo_hora_serie=form_data.custo_hora_serie,
                            preco_ml_std=form_data.preco_ml_std,
                            preco_ml_serie=form_data.preco_ml_serie,
                            permite_rasgos=form_data.permite_rasgos,
                            preco_rasgo_ml_std=form_data.preco_rasgo_ml_std,
                            preco_rasgo_ml_serie=form_data.preco_rasgo_ml_serie,
                            preco_lado_curto_std=form_data.preco_lado_curto_std,
                            preco_lado_curto_serie=form_data.preco_lado_curto_serie,
                            preco_lado_longo_std=form_data.preco_lado_longo_std,
                            preco_lado_longo_serie=form_data.preco_lado_longo_serie,
                            limite_lado_mm=form_data.limite_lado_mm,
                            custo_setup_peca_std=form_data.custo_setup_peca_std,
                            custo_setup_peca_serie=form_data.custo_setup_peca_serie,
                            permite_furacao=form_data.permite_furacao,
                            permite_pocket=form_data.permite_pocket,
                            permite_escaloes_area=form_data.permite_escaloes_area,
                            preco_furo_std=form_data.preco_furo_std,
                            preco_furo_serie=form_data.preco_furo_serie,
                            preco_m2_face_std=form_data.preco_m2_face_std,
                            preco_m2_face_serie=form_data.preco_m2_face_serie,
                            ativo=form_data.ativo,
                            observacoes=form_data.observacoes,
                        ),
                    )
            except IntegrityError:
                dialog.set_error("Já existe uma máquina com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._maquina_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a máquina.")
                return False

            saved = True
            return True

        dialog = MaquinaDialog(maquina=maquina, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText(f"Máquina {maquina.codigo} atualizada.")

    def alternar_maquina_ativa(self) -> None:
        """Toggle the active state of the selected machine after confirmation."""
        maquina = self._get_selected_maquina()
        if maquina is None:
            self.status_label.setText("Selecione uma máquina para ativar/desativar.")
            return

        acao = "desativar" if maquina.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} a máquina {maquina.codigo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefMaquinaService(session)
                if maquina.ativo:
                    service.desativar_maquina(maquina.id)
                else:
                    service.ativar_maquina(maquina.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado da máquina.")
            return

        estado = "desativada" if maquina.ativo else "reativada"
        self.carregar()
        self.status_label.setText(f"Máquina {maquina.codigo} {estado}.")

    def abrir_escaloes_maquina(self) -> None:
        """Open the CNC area-tier manager for the selected machine."""
        maquina = self._get_selected_maquina()
        if maquina is None:
            self.status_label.setText("Selecione uma máquina para gerir escalões.")
            return

        rotulo = f"Máquina: {maquina.codigo} - {maquina.nome}"
        dialog = EscaloesAreaDialog(maquina.id, maquina_label=rotulo, parent=self)
        dialog.exec()
        self.status_label.setText(f"Escalões da máquina {maquina.codigo} geridos.")

    def _maquina_error_message(self, error: ValueError) -> str:
        """Return a friendly message for a machine service error."""
        if "existe" in str(error).lower():
            return "Já existe uma máquina com esse código."

        return "Não foi possível guardar a máquina."

    def _create_table(self, headers: list[str]) -> QTableWidget:
        """Create a read-only table with the given headers."""
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def _wrap_table(self, table: QTableWidget) -> QWidget:
        """Wrap one table in a tab container widget."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(table, stretch=1)
        tab.setLayout(layout)
        return tab

    def _format_maquina(self, maquina_id: int | None, maquina_labels: dict[int, str]) -> str:
        """Return the display label for one machine reference."""
        if maquina_id is None:
            return ""

        return maquina_labels.get(maquina_id, f"#{maquina_id}")

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"

    def _format_metodos(self, maquina: DefMaquinaResumo) -> str:
        """Summarize the calculation methods one machine allows."""
        tipo = (maquina.tipo or "").strip().upper()
        if tipo == "REVESTIMENTO":
            return "Revestimento"
        if tipo != "CNC":
            return ""
        partes: list[str] = []
        if maquina.permite_escaloes_area:
            partes.append("Área")
        partes.append("Tempo")
        if maquina.permite_furacao:
            partes.append("Furos")
        if maquina.permite_rasgos:
            partes.append("Rasgo")
        if maquina.permite_pocket:
            partes.append("Pocket")
        return " · ".join(partes)

    def _format_lados(self, curto, longo) -> str:
        """Format ORLAGEM short/long side tariffs."""
        curto_txt = format_quantity(curto)
        longo_txt = format_quantity(longo)
        if not curto_txt and not longo_txt:
            return ""
        return f"{curto_txt or '-'} / {longo_txt or '-'}"
