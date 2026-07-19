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
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.componente_types import get_componente_type_label
from app.domain.orla_types import format_orla_code, get_orla_type_label
from app.domain.peca_natureza_types import (
    get_peca_natureza_label,
    get_peca_orientacao_label,
)
from app.domain.associado_types import (
    DIMENSAO_REFERENCIA_LABELS,
    MODO_QUANTIDADE_LABELS,
    ZONA_APLICACAO_LABELS,
)
from app.domain.configuracao_sugestoes import ORIGEM_PECA
from app.domain.metodo_calculo_types import get_metodo_calculo_label
from app.domain.regra_operacao_types import get_regra_operacao_label
from app.domain.regra_quantidade_types import get_regra_quantidade_label
from app.domain.valueset_types import VALUESET_KEY_LABELS
from app.repositories.configuracao_sugestoes_repository import (
    listar_configuracoes_associado,
    listar_configuracoes_operacao,
)
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
from app.services.def_peca_service import DefPecaService, EditarDefPecaData
from app.services.def_peca_revisao_service import DefPecaRevisaoService
from app.services.def_regra_quantidade_service import DefRegraQuantidadeService
from app.ui.dialogs.criar_revisao_peca_dialog import CriarRevisaoPecaDialog
from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog
from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog
from app.ui.dialogs.def_peca_operacao_dialog import (
    DefPecaOperacaoDialog,
    UNIDADE_TEMPO_LABELS,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_quantity


class DefPecaDetailPage(QWidget):
    """Detail page for one reusable piece definition and its associates."""

    COMPONENTES_HEADERS = [
        "Ordem",
        "Tipo componente",
        "Componente / Refer\u00eancia",
        "Descri\u00e7\u00e3o",
        "Prioridade ValueSet",
        "Quantidade",
        "Regra quantidade",
        "Regra (auto)",
        "Zona",
        "Dimensão",
        "Topos",
        "Aplicação",
        "Obrigat\u00f3rio",
        "Ativo",
    ]

    OPERACOES_HEADERS = [
        "Ordem",
        "Operação",
        "Tipo",
        "Máquina",
        "Método",
        "Quantidade base",
        "Construção rasgo",
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
        on_revision_created: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__()

        self.peca = peca
        self.componentes = componentes or []
        self.component_labels = component_labels or {}
        self.on_back = on_back
        self.on_revision_created = on_revision_created
        self._componentes_by_row: dict[int, DefPecaComponenteResumo] = {}
        self.operacoes_peca: list[DefPecaOperacaoResumo] = []
        self._operacoes_by_row: dict[int, DefPecaOperacaoResumo] = {}
        self._operacao_resumos: dict[int, DefOperacaoResumo] = {}
        self._maquina_labels: dict[int, str] = {}

        title = QLabel(
            f"Defini\u00e7\u00e3o de Pe\u00e7a: {peca.codigo} · R{peca.revisao_numero}"
        )
        self.detail_title = title
        self.detail_title.setObjectName("defPecaDetailTitle")

        self.back_button = QPushButton("Voltar \u00e0 lista")
        self.back_button.clicked.connect(self._handle_back)
        self.criar_revisao_button = QPushButton("Criar nova revisão")
        self.criar_revisao_button.clicked.connect(self.criar_nova_revisao)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.detail_title, stretch=1)
        header_layout.addWidget(self.criar_revisao_button)
        header_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignRight)

        tabs = QTabWidget()
        tabs.addTab(self._create_dados_gerais_tab(), "Dados Gerais")
        tabs.addTab(self._create_componentes_tab(), "Associados")
        tabs.addTab(self._create_regras_tab(), "Regras")
        tabs.addTab(self._create_operacoes_tab(), "Opera\u00e7\u00f5es")
        tabs.addTab(self._create_revisoes_tab(), "Revisões")

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

    def _create_dados_gerais_readonly_tab(self) -> QWidget:
        """Legacy read-only rendering kept for compatibility."""
        tab = QWidget()
        form = QFormLayout()
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self._valueset_labels = self._carregar_valueset_labels()

        fields = [
            ("C\u00f3digo", self.peca.codigo),
            ("Revisão", f"R{self.peca.revisao_numero}"),
            ("Nome", self.peca.nome),
            ("Nome na biblioteca", self.peca.nome_biblioteca or ""),
            ("Descri\u00e7\u00e3o", self.peca.descricao or ""),
            ("Natureza", get_peca_natureza_label(self.peca.natureza)),
            ("Orientação", get_peca_orientacao_label(self.peca.orientacao)),
            ("Função", self.peca.funcao or ""),
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

    def _create_dados_gerais_tab(self) -> QWidget:
        """Create the editable general-data tab inside the detail page."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        ajuda = QLabel(
            "Edite aqui os dados gerais da peça. Associados, regras, operações "
            "e revisões permanecem nos separadores seguintes."
        )
        ajuda.setWordWrap(True)
        layout.addWidget(ajuda)

        self.dados_gerais_editor = EditarDefPecaDialog(
            self.peca,
            tab,
            on_save=self._guardar_dados_gerais,
            embedded=True,
        )
        # Keep the editor readable on wide monitors instead of stretching each
        # input across the entire application window.
        self.dados_gerais_editor.setMaximumWidth(500)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.dados_gerais_editor)
        layout.addWidget(scroll, stretch=1)

        # The embedded form contains the same orlas, ValueSets and fields that
        # were previously displayed read-only: format_orla_code, get_orla_type_label,
        # "Código de orlas", "Chave material ValueSet", "Permite acabamento",
        # "Chave acabamento face superior" and "Chave acabamento face inferior".
        return tab

    def _guardar_dados_gerais(self, form_data) -> bool:
        """Persist the embedded general-data form without leaving the detail page."""
        try:
            with SessionLocal() as session:
                self.peca = DefPecaService(session).editar_peca(
                    self.peca.id,
                    EditarDefPecaData(
                        codigo=form_data.codigo,
                        nome=form_data.nome,
                        nome_biblioteca=form_data.nome_biblioteca,
                        descricao=form_data.descricao,
                        grupo=form_data.grupo,
                        tipo_peca=form_data.tipo_peca,
                        natureza=form_data.natureza,
                        orientacao=form_data.orientacao,
                        funcao=form_data.funcao,
                        formula_comp=self.peca.formula_comp,
                        formula_larg=self.peca.formula_larg,
                        formula_esp=self.peca.formula_esp,
                        orla_c1=form_data.orla_c1,
                        orla_c2=form_data.orla_c2,
                        orla_l1=form_data.orla_l1,
                        orla_l2=form_data.orla_l2,
                        chave_valueset_material=form_data.chave_valueset_material,
                        permite_acabamento=form_data.permite_acabamento,
                        chave_valueset_acabamento_sup=form_data.chave_valueset_acabamento_sup,
                        chave_valueset_acabamento_inf=form_data.chave_valueset_acabamento_inf,
                        sem_material=form_data.sem_material,
                        ativo=form_data.ativo,
                    ),
                )
        except IntegrityError:
            self.dados_gerais_editor.set_error("Já existe uma peça com esse código.")
            return False
        except (SQLAlchemyError, ValueError):
            self.dados_gerais_editor.set_error("Não foi possível guardar a peça.")
            return False

        self.detail_title.setText(
            f"Definição de Peça: {self.peca.codigo} · R{self.peca.revisao_numero}"
        )
        self.dados_gerais_editor.peca = self.peca
        self.dados_gerais_editor.set_error("")
        return True

    def _create_revisoes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        ajuda = QLabel(
            "Cada revisão é uma definição independente. Orçamentos antigos mantêm "
            "o snapshot da revisão usada; apenas a revisão ativa aparece para novas inserções."
        )
        ajuda.setWordWrap(True)
        layout.addWidget(ajuda)

        self.revisoes_table = QTableWidget(0, 5)
        self.revisoes_table.setHorizontalHeaderLabels(
            ["Revisão", "Código", "Nome", "Estado", "Criada em"]
        )
        self.revisoes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.revisoes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.revisoes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.revisoes_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.revisoes_table, stretch=1)
        self.revisoes_status_label = QLabel("")
        layout.addWidget(self.revisoes_status_label)
        self.recarregar_revisoes()
        return tab

    def recarregar_revisoes(self) -> None:
        try:
            with SessionLocal() as session:
                revisoes = DefPecaRevisaoService(session).listar_revisoes(self.peca.id)
        except SQLAlchemyError:
            self.revisoes_status_label.setText("Não foi possível carregar as revisões.")
            return
        self.revisoes_table.setRowCount(len(revisoes))
        for row, revisao in enumerate(revisoes):
            valores = (
                f"R{revisao.revisao_numero}",
                revisao.codigo,
                revisao.nome,
                "Ativa" if revisao.ativo else "Inativa",
                self._format_datetime(revisao.created_at),
            )
            for coluna, valor in enumerate(valores):
                self.revisoes_table.setItem(row, coluna, QTableWidgetItem(valor))
        self.revisoes_status_label.setText(
            f"{len(revisoes)} revisão(ões) nesta série."
        )

    def criar_nova_revisao(self) -> None:
        try:
            with SessionLocal() as session:
                preparacao = DefPecaRevisaoService(session).preparar_revisao(
                    self.peca.id
                )
        except (SQLAlchemyError, ValueError) as error:
            QMessageBox.warning(self, "Criar nova revisão", str(error))
            return

        dialog = CriarRevisaoPecaDialog(self.peca, preparacao, self)
        if not dialog.exec():
            return
        dados = dialog.form_data()
        try:
            with SessionLocal() as session:
                resultado = DefPecaRevisaoService(session).criar_revisao(
                    self.peca.id,
                    novo_codigo=dados.codigo,
                    novo_nome=dados.nome,
                )
        except (SQLAlchemyError, ValueError) as error:
            QMessageBox.warning(self, "Criar nova revisão", str(error))
            return

        QMessageBox.information(
            self,
            "Nova revisão criada",
            f"{resultado.codigo} · R{resultado.revisao_numero} criada.\n"
            f"Operações copiadas: {resultado.operacoes_copiadas}\n"
            f"Associados copiados: {resultado.componentes_copiados}\n\n"
            "A revisão anterior ficou inativa. Orçamentos existentes não foram alterados.",
        )
        if self.on_revision_created is not None:
            self.on_revision_created(resultado.nova_peca_id)
        else:
            self.recarregar_revisoes()

    def _create_componentes_tab(self) -> QWidget:
        """Create the components tab with management actions."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.novo_componente_button = QPushButton("Novo Associado")
        self.novo_componente_button.clicked.connect(self.abrir_novo_componente)
        self.editar_componente_button = QPushButton("Editar Associado")
        self.editar_componente_button.clicked.connect(self.abrir_editar_componente)
        self.remover_componente_button = QPushButton("Remover Associado")
        self.remover_componente_button.clicked.connect(self.remover_componente)
        self.atualizar_componentes_button = QPushButton("Atualizar")
        self.atualizar_componentes_button.clicked.connect(self.recarregar_componentes)

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

    def _create_regras_tab(self) -> QWidget:
        """Edit catalog defaults without applying them to existing costing lines."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        ajuda = QLabel(
            "Fórmulas do cabeçalho: H/L/P são dimensões do item e HM/LM/PM da "
            "divisão ativa. As transformações dos associados podem também usar "
            "PAI_COMP, PAI_LARG e PAI_ESP. Nesta fase as regras são apenas guardadas "
            "no catálogo; a aplicação ao custeio entra na fase seguinte."
        )
        ajuda.setWordWrap(True)
        layout.addWidget(ajuda)

        form = QFormLayout()
        self.formula_comp_input = QLineEdit(self.peca.formula_comp or "")
        self.formula_larg_input = QLineEdit(self.peca.formula_larg or "")
        self.formula_esp_input = QLineEdit(self.peca.formula_esp or "")
        for input_widget in (
            self.formula_comp_input,
            self.formula_larg_input,
            self.formula_esp_input,
        ):
            input_widget.setMaximumWidth(620)
        form.addRow("Comp do cabeçalho", self.formula_comp_input)
        form.addRow("Larg do cabeçalho", self.formula_larg_input)
        form.addRow("Esp do cabeçalho", self.formula_esp_input)
        layout.addLayout(form)

        self.guardar_formulas_button = QPushButton("Guardar fórmulas do cabeçalho")
        self.guardar_formulas_button.clicked.connect(self.guardar_formulas_dimensionais)
        self.guardar_formulas_button.setMaximumWidth(280)
        self.formulas_status_label = QLabel("")
        layout.addWidget(
            self.guardar_formulas_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(self.formulas_status_label)

        layout.addWidget(QLabel("Transformações dimensionais dos associados"))
        self.regras_componentes_table = QTableWidget(0, 5)
        self.regras_componentes_table.setHorizontalHeaderLabels(
            ["Ordem", "Associado", "Comp", "Larg", "Esp"]
        )
        self.regras_componentes_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.regras_componentes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.regras_componentes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.regras_componentes_table.horizontalHeader().setStretchLastSection(False)
        ligar_persistencia_larguras(
            self.regras_componentes_table,
            "def_peca_regras_componentes",
        )
        self.regras_componentes_table.cellDoubleClicked.connect(
            self._editar_transformacao_componente
        )
        layout.addWidget(self.regras_componentes_table, stretch=1)
        self._preencher_regras_componentes()
        return tab

    def guardar_formulas_dimensionais(self) -> None:
        try:
            with SessionLocal() as session:
                self.peca = DefPecaService(session).atualizar_formulas_dimensionais(
                    self.peca.id,
                    formula_comp=self.formula_comp_input.text(),
                    formula_larg=self.formula_larg_input.text(),
                    formula_esp=self.formula_esp_input.text(),
                )
        except (SQLAlchemyError, ValueError) as error:
            self.formulas_status_label.setText(str(error))
            return
        self.formulas_status_label.setText("Fórmulas do cabeçalho guardadas.")

    def _preencher_regras_componentes(self) -> None:
        if not hasattr(self, "regras_componentes_table"):
            return
        self.regras_componentes_table.setRowCount(len(self.componentes))
        for row, componente in enumerate(self.componentes):
            valores = (
                str(componente.ordem),
                self._format_componente_ref(componente),
                componente.formula_comp or "",
                componente.formula_larg or "",
                componente.formula_esp or "",
            )
            for column, valor in enumerate(valores):
                self.regras_componentes_table.setItem(row, column, QTableWidgetItem(valor))

    def _editar_transformacao_componente(self, row: int, _column: int) -> None:
        self.componentes_table.selectRow(row)
        self.abrir_editar_componente()

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
                str(getattr(componente, "prioridade_valueset", 1) or 1),
                format_quantity(componente.quantidade),
                get_regra_quantidade_label(componente.regra_quantidade),
                componente.def_regra_quantidade_codigo or "—",
                ZONA_APLICACAO_LABELS.get(
                    componente.zona_aplicacao, componente.zona_aplicacao
                ),
                DIMENSAO_REFERENCIA_LABELS.get(
                    componente.dimensao_referencia, componente.dimensao_referencia
                ),
                str(componente.numero_topos),
                MODO_QUANTIDADE_LABELS.get(
                    componente.modo_quantidade, componente.modo_quantidade
                ),
                self._format_bool(componente.obrigatorio),
                self._format_bool(componente.ativo),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, componente.id)
                self.componentes_table.setItem(row_index, column_index, item)

        self.componentes_status_label.setText(self._componentes_status_text())
        self._preencher_regras_componentes()

    def _componentes_status_text(self) -> str:
        """Return the status line for the components table."""
        if not self.componentes:
            return "Sem associados. Use 'Novo Associado' para adicionar."
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
        self.componentes_table.selectRow(row)
        self.abrir_editar_componente()

    def abrir_novo_componente(self) -> None:
        """Open the dialog to create a new component."""
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
                            formula_comp=form_data.formula_comp,
                            formula_larg=form_data.formula_larg,
                            formula_esp=form_data.formula_esp,
                            quantidade=form_data.quantidade,
                            regra_quantidade=form_data.regra_quantidade,
                            def_regra_quantidade_id=form_data.def_regra_quantidade_id,
                            zona_aplicacao=form_data.zona_aplicacao,
                            dimensao_referencia=form_data.dimensao_referencia,
                            numero_topos=form_data.numero_topos,
                            modo_quantidade=form_data.modo_quantidade,
                            prioridade_valueset=form_data.prioridade_valueset,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                        )
                    )
            except ValueError as error:
                dialog.set_error(str(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("N\u00e3o foi poss\u00edvel guardar o associado.")
                return False

            saved = True
            return True

        dialog = DefPecaComponenteDialog(
            pecas_disponiveis,
            parent=self,
            on_save=handle_save,
            regras_disponiveis=self._carregar_regras_quantidade(),
            configuracoes_existentes=self._carregar_configuracoes_associado(),
        )
        if dialog.exec() and saved:
            self.recarregar_componentes()
            self.componentes_status_label.setText("Associado criado.")

    def abrir_editar_componente(self) -> None:
        """Open the dialog to edit the selected component."""
        componente = self._get_selected_componente()
        if componente is None:
            self.componentes_status_label.setText("Selecione um associado para editar.")
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
                            formula_comp=form_data.formula_comp,
                            formula_larg=form_data.formula_larg,
                            formula_esp=form_data.formula_esp,
                            quantidade=form_data.quantidade,
                            regra_quantidade=form_data.regra_quantidade,
                            def_regra_quantidade_id=form_data.def_regra_quantidade_id,
                            zona_aplicacao=form_data.zona_aplicacao,
                            dimensao_referencia=form_data.dimensao_referencia,
                            numero_topos=form_data.numero_topos,
                            modo_quantidade=form_data.modo_quantidade,
                            prioridade_valueset=form_data.prioridade_valueset,
                            obrigatorio=form_data.obrigatorio,
                            ativo=form_data.ativo,
                        ),
                    )
            except ValueError as error:
                dialog.set_error(str(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("N\u00e3o foi poss\u00edvel guardar o associado.")
                return False

            saved = True
            return True

        dialog = DefPecaComponenteDialog(
            pecas_disponiveis,
            componente=componente,
            parent=self,
            on_save=handle_save,
            regras_disponiveis=self._carregar_regras_quantidade(),
            configuracoes_existentes=self._carregar_configuracoes_associado(),
        )
        if dialog.exec() and saved:
            self.recarregar_componentes()
            self.componentes_status_label.setText("Associado atualizado.")

    def remover_componente(self) -> None:
        """Deactivate the selected component after confirmation."""
        componente = self._get_selected_componente()
        if componente is None:
            self.componentes_status_label.setText("Selecione um associado para remover.")
            return

        confirm = QMessageBox.question(
            self,
            "Remover associado",
            "Remover (desativar) o associado selecionado?",
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
        self.componentes_status_label.setText("Associado removido.")

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

    def _carregar_configuracoes_operacao(self) -> list:
        """Copy-suggestion sources (G4), excluding this piece's own links."""
        try:
            with SessionLocal() as session:
                configs = listar_configuracoes_operacao(session)
        except SQLAlchemyError:
            return []
        return [
            config
            for config in configs
            if not (
                config.origem_tipo == ORIGEM_PECA
                and config.origem_id == self.peca.id
            )
        ]

    def _carregar_configuracoes_associado(self) -> list:
        """Copy-suggestion sources (G4), excluding this piece's own components."""
        try:
            with SessionLocal() as session:
                configs = listar_configuracoes_associado(session)
        except SQLAlchemyError:
            return []
        return [
            config for config in configs if config.def_peca_pai_id != self.peca.id
        ]

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
                (
                    get_metodo_calculo_label(
                        getattr(ligacao, "metodo_calculo", None)
                    )
                    or get_regra_operacao_label(ligacao.regra_calculo)
                ),
                format_quantity(ligacao.quantidade_base),
                (
                    f"{ligacao.rasgo_qt_comp} × COMP + {ligacao.rasgo_qt_larg} × LARG"
                    if ligacao.rasgo_qt_comp or ligacao.rasgo_qt_larg
                    else ""
                ),
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
                            metodo_calculo=form_data.metodo_calculo,
                            regra_calculo=form_data.regra_calculo,
                            quantidade_base=form_data.quantidade_base,
                            rasgo_qt_comp=form_data.rasgo_qt_comp,
                            rasgo_qt_larg=form_data.rasgo_qt_larg,
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

        dialog = DefPecaOperacaoDialog(
            operacoes,
            parent=self,
            on_save=handle_save,
            natureza_peca=getattr(self.peca, "natureza", None),
            configuracoes_existentes=self._carregar_configuracoes_operacao(),
        )
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
                            metodo_calculo=form_data.metodo_calculo,
                            regra_calculo=form_data.regra_calculo,
                            quantidade_base=form_data.quantidade_base,
                            rasgo_qt_comp=form_data.rasgo_qt_comp,
                            rasgo_qt_larg=form_data.rasgo_qt_larg,
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

        dialog = DefPecaOperacaoDialog(
            operacoes,
            ligacao=ligacao,
            parent=self,
            on_save=handle_save,
            natureza_peca=getattr(self.peca, "natureza", None),
            configuracoes_existentes=self._carregar_configuracoes_operacao(),
        )
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
