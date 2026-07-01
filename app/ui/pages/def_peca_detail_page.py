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
from app.domain.regra_operacao_types import get_regra_operacao_label
from app.domain.regra_quantidade_types import get_regra_quantidade_label
from app.domain.valueset_types import VALUESET_KEY_LABELS
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.repositories.def_peca_operacao_repository import DefPecaOperacaoResumo
from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_maquina_service import DefMaquinaService
from app.services.def_operacao_service import DefOperacaoService
from app.services.def_valueset_chave_service import DefValuesetChaveService
from app.services.def_peca_componente_service import (
    CriarDefPecaComponenteData,
    DefPecaComponenteService,
    EditarDefPecaComponenteData,
)
from app.services.def_peca_operacao_service import (
    CriarDefPecaOperacaoData,
    DefPecaOperacaoService,
    EditarDefPecaOperacaoData,
)
from app.services.def_peca_service import DefPecaService
from app.services.def_regra_quantidade_service import DefRegraQuantidadeService
from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog
from app.ui.dialogs.def_peca_operacao_dialog import (
    DefPecaOperacaoDialog,
    UNIDADE_TEMPO_LABELS,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
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
        "Regra (auto)",
        "Obrigat\u00f3rio",
        "Ativo",
    ]

    OPERACOES_HEADERS = [
        "Ordem",
        "Operação",
        "Tipo",
        "Máquina",
        "Regra cálculo",
        "Quantidade base",
        "Tempo setup",
        "Tempo por unidade",
        "Unidade tempo",
        "Obrigatório",
        "Ativo",
        "Observações",
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
        self.operacoes_peca: list[DefPecaOperacaoResumo] = []
        self._operacoes_by_row: dict[int, DefPecaOperacaoResumo] = {}
        self._operacao_resumos: dict[int, DefOperacaoResumo] = {}
        self._maquina_labels: dict[int, str] = {}

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
        tabs.addTab(self._create_operacoes_tab(), "Opera\u00e7\u00f5es")

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

        self._valueset_labels = self._carregar_valueset_labels()

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
            (
                "Chave material ValueSet",
                self._format_valueset_key(self.peca.chave_valueset_material),
            ),
            ("Permite acabamento", self._format_bool(self.peca.permite_acabamento)),
            (
                "Chave acabamento face superior",
                self._format_valueset_key(self.peca.chave_valueset_acabamento_sup),
            ),
            (
                "Chave acabamento face inferior",
                self._format_valueset_key(self.peca.chave_valueset_acabamento_inf),
            ),
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
        ligar_persistencia_larguras(self.componentes_table, "def_peca_componentes")

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
                componente.def_regra_quantidade_codigo or "—",
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
                            def_regra_quantidade_id=form_data.def_regra_quantidade_id,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                        )
                    )
            except (SQLAlchemyError, ValueError):
                dialog.set_error("N\u00e3o foi poss\u00edvel guardar o componente.")
                return False

            saved = True
            return True

        dialog = DefPecaComponenteDialog(
            pecas_disponiveis,
            parent=self,
            on_save=handle_save,
            regras_disponiveis=self._carregar_regras_quantidade(),
        )
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
                            def_regra_quantidade_id=form_data.def_regra_quantidade_id,
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
            pecas_disponiveis,
            componente=componente,
            parent=self,
            on_save=handle_save,
            regras_disponiveis=self._carregar_regras_quantidade(),
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

    def _carregar_regras_quantidade(self) -> list:
        """Return the active quantity rules for the component dialog (or [])."""
        try:
            with SessionLocal() as session:
                return DefRegraQuantidadeService(session).listar_ativas()
        except SQLAlchemyError:
            return []

    def _create_operacoes_tab(self) -> QWidget:
        """Create the operations tab with management actions."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        info = QLabel("Operações associadas a esta definição de peça.")
        info.setWordWrap(True)

        self.nova_operacao_button = QPushButton("Nova Operação")
        self.nova_operacao_button.clicked.connect(self.abrir_nova_operacao)
        self.editar_operacao_button = QPushButton("Editar Operação")
        self.editar_operacao_button.clicked.connect(self.abrir_editar_operacao)
        self.toggle_operacao_button = QPushButton("Ativar/Desativar")
        self.toggle_operacao_button.clicked.connect(self.alternar_operacao_ativa)
        self.atualizar_operacoes_button = QPushButton("Atualizar")
        self.atualizar_operacoes_button.clicked.connect(self.recarregar_operacoes)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.nova_operacao_button)
        buttons_layout.addWidget(self.editar_operacao_button)
        buttons_layout.addWidget(self.toggle_operacao_button)
        buttons_layout.addWidget(self.atualizar_operacoes_button)
        buttons_layout.addStretch()

        self.operacoes_status_label = QLabel("")
        self.operacoes_status_label.setObjectName("defPecaOperacoesStatus")

        self.operacoes_table = QTableWidget(0, len(self.OPERACOES_HEADERS))
        self.operacoes_table.setHorizontalHeaderLabels(self.OPERACOES_HEADERS)
        self.operacoes_table.verticalHeader().setVisible(False)
        self.operacoes_table.setAlternatingRowColors(True)
        self.operacoes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.operacoes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.operacoes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.operacoes_table.cellDoubleClicked.connect(self._handle_operacao_double_click)
        ligar_persistencia_larguras(self.operacoes_table, "def_peca_operacoes")

        layout.addWidget(info)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.operacoes_status_label)
        layout.addWidget(self.operacoes_table, stretch=1)

        self.recarregar_operacoes()
        tab.setLayout(layout)
        return tab

    def recarregar_operacoes(self) -> None:
        """Reload the piece operations and lookup labels from the database."""
        try:
            with SessionLocal() as session:
                self.operacoes_peca = DefPecaOperacaoService(session).listar_operacoes_da_peca(
                    self.peca.id
                )
                all_operacoes = DefOperacaoService(session).listar_operacoes()
                all_maquinas = DefMaquinaService(session).listar_maquinas()
        except SQLAlchemyError:
            self.operacoes_status_label.setText("Nao foi possivel carregar as operacoes.")
            return

        self._operacao_resumos = {operacao.id: operacao for operacao in all_operacoes}
        self._maquina_labels = {
            maquina.id: f"{maquina.codigo} - {maquina.nome}" for maquina in all_maquinas
        }
        self._preencher_operacoes()

    def _preencher_operacoes(self) -> None:
        """Fill the operations table from the current read models."""
        self._operacoes_by_row = {}
        self.operacoes_table.setRowCount(len(self.operacoes_peca))

        for row_index, ligacao in enumerate(self.operacoes_peca):
            self._operacoes_by_row[row_index] = ligacao
            operacao = self._operacao_resumos.get(ligacao.def_operacao_id)
            values = [
                str(ligacao.ordem),
                self._format_operacao_label(ligacao.def_operacao_id, operacao),
                (operacao.tipo_operacao or "") if operacao is not None else "",
                self._format_operacao_maquina(operacao),
                get_regra_operacao_label(ligacao.regra_calculo),
                format_quantity(ligacao.quantidade_base),
                format_quantity(ligacao.tempo_setup_minutos),
                format_quantity(ligacao.tempo_por_unidade_minutos),
                UNIDADE_TEMPO_LABELS.get(
                    ligacao.unidade_tempo,
                    ligacao.unidade_tempo or "",
                ),
                self._format_bool(ligacao.obrigatorio),
                self._format_bool(ligacao.ativo),
                ligacao.observacoes or "",
            ]

            for column_index, value in enumerate(values):
                self.operacoes_table.setItem(row_index, column_index, QTableWidgetItem(value))

        self.operacoes_status_label.setText(self._operacoes_status_text())

    def _operacoes_status_text(self) -> str:
        """Return the status line for the operations table."""
        if not self.operacoes_peca:
            return "Sem operacoes. Use 'Nova Operacao' para adicionar."
        return ""

    def _format_operacao_label(
        self, operacao_id: int, operacao: DefOperacaoResumo | None
    ) -> str:
        """Return the display label for one operation reference."""
        if operacao is not None:
            return f"{operacao.codigo} - {operacao.nome}"
        return f"#{operacao_id}"

    def _format_operacao_maquina(self, operacao: DefOperacaoResumo | None) -> str:
        """Return the machine label for one operation."""
        if operacao is None or operacao.maquina_id is None:
            return ""
        return self._maquina_labels.get(operacao.maquina_id, f"#{operacao.maquina_id}")

    def _get_selected_operacao(self) -> DefPecaOperacaoResumo | None:
        """Return the selected piece operation link."""
        row = self.operacoes_table.currentRow()
        if row < 0:
            return None
        return self._operacoes_by_row.get(row)

    def _handle_operacao_double_click(self, row: int, _column: int) -> None:
        """Edit a piece operation when the user double-clicks its row."""
        self.operacoes_table.selectRow(row)
        self.abrir_editar_operacao()

    def abrir_nova_operacao(self) -> None:
        """Open the dialog to link a new operation to the piece."""
        operacoes = self._carregar_operacoes_disponiveis()
        if operacoes is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefPecaOperacaoService(session).adicionar_operacao_a_peca(
                        CriarDefPecaOperacaoData(
                            def_peca_id=self.peca.id,
                            def_operacao_id=form_data.def_operacao_id,
                            ordem=form_data.ordem,
                            regra_calculo=form_data.regra_calculo,
                            quantidade_base=form_data.quantidade_base,
                            tempo_setup_minutos=form_data.tempo_setup_minutos,
                            tempo_por_unidade_minutos=form_data.tempo_por_unidade_minutos,
                            unidade_tempo=form_data.unidade_tempo,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                            observacoes=form_data.observacoes,
                        )
                    )
            except (SQLAlchemyError, ValueError) as error:
                dialog.set_error(self._operacao_error_message(error))
                return False

            saved = True
            return True

        dialog = DefPecaOperacaoDialog(operacoes, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.recarregar_operacoes()
            self.operacoes_status_label.setText("Operacao associada.")

    def abrir_editar_operacao(self) -> None:
        """Open the dialog to edit the selected piece operation."""
        ligacao = self._get_selected_operacao()
        if ligacao is None:
            self.operacoes_status_label.setText("Selecione uma operação para editar.")
            return

        operacoes = self._carregar_operacoes_disponiveis(ligacao)
        if operacoes is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefPecaOperacaoService(session).editar_operacao_da_peca(
                        ligacao.id,
                        EditarDefPecaOperacaoData(
                            def_peca_id=self.peca.id,
                            def_operacao_id=form_data.def_operacao_id,
                            ordem=form_data.ordem,
                            regra_calculo=form_data.regra_calculo,
                            quantidade_base=form_data.quantidade_base,
                            tempo_setup_minutos=form_data.tempo_setup_minutos,
                            tempo_por_unidade_minutos=form_data.tempo_por_unidade_minutos,
                            unidade_tempo=form_data.unidade_tempo,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                            observacoes=form_data.observacoes,
                        ),
                    )
            except (SQLAlchemyError, ValueError) as error:
                dialog.set_error(self._operacao_error_message(error))
                return False

            saved = True
            return True

        dialog = DefPecaOperacaoDialog(operacoes, ligacao=ligacao, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.recarregar_operacoes()
            self.operacoes_status_label.setText("Operacao atualizada.")

    def alternar_operacao_ativa(self) -> None:
        """Toggle the active state of the selected piece operation."""
        ligacao = self._get_selected_operacao()
        if ligacao is None:
            self.operacoes_status_label.setText("Selecione uma operação para ativar/desativar.")
            return

        acao = "desativar" if ligacao.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta operação associada?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefPecaOperacaoService(session)
                if ligacao.ativo:
                    service.desativar_operacao_da_peca(ligacao.id)
                else:
                    service.ativar_operacao_da_peca(ligacao.id)
        except SQLAlchemyError:
            self.operacoes_status_label.setText("Nao foi possivel atualizar o estado da operacao.")
            return

        estado = "desativada" if ligacao.ativo else "reativada"
        self.recarregar_operacoes()
        self.operacoes_status_label.setText(f"Operacao {estado}.")

    def _carregar_operacoes_disponiveis(
        self, ligacao: DefPecaOperacaoResumo | None = None
    ) -> list[DefOperacaoResumo] | None:
        """Return active operations for the combo, keeping the current one if inactive."""
        try:
            with SessionLocal() as session:
                service = DefOperacaoService(session)
                operacoes = service.listar_operacoes_ativas()
                atual = None
                if ligacao is not None:
                    if not any(op.id == ligacao.def_operacao_id for op in operacoes):
                        atual = service.obter_por_id(ligacao.def_operacao_id)
        except SQLAlchemyError:
            self.operacoes_status_label.setText("Nao foi possivel carregar as operacoes.")
            return None

        if atual is not None:
            return [atual, *operacoes]
        return operacoes

    def _operacao_error_message(self, error: Exception) -> str:
        """Return a friendly message for a piece operation service error."""
        if "associada" in str(error).lower():
            return "Esta operação já está associada a esta peça."
        return "Não foi possível guardar a operação."

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

    def _format_valueset_key(self, value: str | None) -> str:
        """Format an optional ValueSet key, preferring the configured label."""
        if value is None or not value.strip():
            return ""

        label = self._valueset_labels.get(value)
        if label:
            return label

        return VALUESET_KEY_LABELS.get(value, value)

    def _carregar_valueset_labels(self) -> dict[str, str]:
        """Load active ValueSet key labels (codigo -> nome) from the database."""
        try:
            with SessionLocal() as session:
                chaves = DefValuesetChaveService(session).listar_chaves_ativas()
        except SQLAlchemyError:
            return {}

        return {chave.codigo: chave.nome for chave in chaves}

    def _format_datetime(self, value: datetime | None) -> str:
        """Format a datetime value for display."""
        if value is None:
            return ""

        return value.strftime("%Y-%m-%d %H:%M")
