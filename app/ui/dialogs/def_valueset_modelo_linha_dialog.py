"""Dialog for creating and editing a ValueSet model line."""

from __future__ import annotations
from app.ui import tema

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.materia_prima_snapshot import (
    coresp_orla_0_4,
    coresp_orla_1_0,
    familia_materia_prima,
    tipo_materia_prima,
)
from app.domain.numeros import normalize_percentagem_humana, parse_decimal_humano
from app.domain.valueset_precos import calcular_preco_liquido
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.services.def_valueset_modelo_linha_operacao_service import (
    CriarDefValuesetModeloLinhaOperacaoData,
    DefValuesetModeloLinhaOperacaoService,
    EditarDefValuesetModeloLinhaOperacaoData,
)
from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog
from app.ui.helpers.orla_picker import obter_precos_orlas_m2
from app.ui.widgets.campo_valor_unidade import CampoValorComUnidade
from app.ui.widgets.orla_line_edit import OrlaLineEdit
from app.ui.dialogs.valueset_linha_operacoes_dialog import (
    ValuesetLinhaOperacoesDialog,
    carregar_configuracoes_para_sugestoes,
)
from app.ui.helpers.valueset_combo_helper import (
    carregar_chaves_valueset_combo,
    natureza_peca_da_chave,
    obter_valor_chave_combo,
)

ORIGEM_DADOS_OPCOES = ("MATERIA_PRIMA", "LIVRE", "EDITADO_LOCALMENTE")

PRIORIDADE_TOOLTIP = (
    "Prioridade dentro da chave: a linha ativa com o número mais baixo é a "
    "escolhida automaticamente no custeio (1 = primeira escolha). "
    "Vazio = nunca escolhida automaticamente. "
    "Não confundir com Ordem, que é apenas a posição na lista."
)
ORDEM_TOOLTIP = (
    "Ordem: apenas a posição de exibição na lista. "
    "Não decide a escolha automática no custeio — isso é a Prioridade."
)
PRECO_LIQUIDO_TOOLTIP = (
    "Calculado automaticamente (campo protegido, não editável):\n"
    "Preço líquido = Preço tabela × (1 − Desconto %) × (1 + Margem %)"
)


@dataclass(frozen=True)
class DefValuesetModeloLinhaDialogData:
    """Data collected by the ValueSet model line dialog."""

    chave: str | None
    codigo_opcao: str
    nome_opcao: str
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    valor_texto: str | None
    prioridade: int | None
    ordem: int
    observacoes: str | None
    ativo: bool
    ref_le: str | None
    descricao_no_orcamento: str | None
    preco_tabela: Decimal | None
    margem_percentagem: Decimal | None
    desconto_percentagem: Decimal | None
    preco_liquido: Decimal | None
    unidade: str | None
    desperdicio_percentagem: Decimal | None
    tipo_materia_prima: str | None
    familia_materia_prima: str | None
    coresp_orla_0_4: str | None
    coresp_orla_1_0: str | None
    preco_orla_0_4_m2: Decimal | None
    preco_orla_1_0_m2: Decimal | None
    comp_mp: Decimal | None
    larg_mp: Decimal | None
    esp_mp: Decimal | None
    origem_dados: str | None
    editado_localmente: bool


class DefValuesetModeloLinhaDialog(QDialog):
    """Modal dialog for creating or editing a ValueSet model line."""

    def __init__(
        self,
        linha: DefValuesetModeloLinhaResumo | None = None,
        parent=None,
        on_save: Callable[[DefValuesetModeloLinhaDialogData], bool] | None = None,
        on_save_as: Callable[[DefValuesetModeloLinhaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.linha = linha
        self.on_save = on_save
        self.on_save_as = on_save_as
        self._is_edit = linha is not None
        self._codigo_opcao_original = linha.codigo_opcao if linha is not None else None
        self._suppress = False
        self.operacoes_alteradas = False

        self.setWindowTitle(
            "Editar Linha do Modelo" if self._is_edit else "Nova Linha do Modelo"
        )
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(680)
        # Open as tall as the screen comfortably allows (more fields visible
        # without scrolling), while never overflowing smaller screens.
        ecra = QGuiApplication.primaryScreen()
        altura_disponivel = (
            ecra.availableGeometry().height() if ecra is not None else 900
        )
        self.resize(620, max(780, min(altura_disponivel - 80, 1000)))

        self.chave_input = QComboBox()
        carregar_chaves_valueset_combo(
            self.chave_input,
            valor_atual=linha.chave if linha is not None else None,
        )

        self.codigo_opcao_input = QLineEdit()
        self.codigo_opcao_input.setVisible(False)
        self.nome_opcao_input = QLineEdit()
        self.nome_opcao_input.setPlaceholderText("Nome amigável da opção")
        self.ref_materia_prima_input = QLineEdit()
        self.descricao_materia_prima_input = QLineEdit()
        self.valor_texto_input = QLineEdit()
        self.valor_texto_input.setPlaceholderText("Ex.: Aglomerado 19mm standard")
        self.prioridade_input = QLineEdit()
        self.prioridade_input.setPlaceholderText("Ex.: 1 (vazio = nunca escolhida)")
        self.prioridade_input.setToolTip(PRIORIDADE_TOOLTIP)
        self.ordem_input = QLineEdit()
        self.ordem_input.setText("1")
        self.ordem_input.setToolTip(ORDEM_TOOLTIP)
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        # Materia-prima snapshot fields.
        self.ref_le_input = QLineEdit()
        self.descricao_no_orcamento_input = QLineEdit()
        self.preco_tabela_input = CampoValorComUnidade("€")
        self.margem_input = CampoValorComUnidade("%")
        self.desconto_input = CampoValorComUnidade("%")
        self.preco_liquido_input = CampoValorComUnidade("€")
        self.preco_liquido_input.marcar_como_resultado(PRECO_LIQUIDO_TOOLTIP)
        self.unidade_input = QLineEdit()
        self.desperdicio_input = CampoValorComUnidade("%")
        self.tipo_mp_input = QLineEdit()
        self.familia_mp_input = QLineEdit()
        self.orla_0_4_input = OrlaLineEdit()
        self.orla_1_0_input = OrlaLineEdit()
        self.preco_orla_0_4_input = CampoValorComUnidade("€/m²")
        self.preco_orla_1_0_input = CampoValorComUnidade("€/m²")
        for widget in (self.preco_orla_0_4_input, self.preco_orla_1_0_input):
            widget.setToolTip(
                "Snapshot local da orla. Unidade obrigatória: euros por metro quadrado (€/m²)."
            )
        self.comp_mp_input = QLineEdit()
        self.larg_mp_input = QLineEdit()
        self.esp_mp_input = QLineEdit()
        self.origem_dados_input = QComboBox()
        self.origem_dados_input.setEditable(True)
        for origem in ORIGEM_DADOS_OPCOES:
            self.origem_dados_input.addItem(origem)
        self.origem_dados_input.setCurrentText("LIVRE")
        self.editado_localmente_input = QCheckBox()

        self.selecionar_mp_button = QPushButton("Selecionar Matéria-Prima")
        self.selecionar_mp_button.clicked.connect(self.abrir_picker_materia_prima)

        self.error_label = QLabel("")
        self.error_label.setObjectName("defValuesetModeloLinhaError")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Chave ValueSet", self.chave_input)
        form.addRow("Opção", self.nome_opcao_input)
        form.addRow("", self.selecionar_mp_button)
        form.addRow("Ref LE", self.ref_le_input)
        form.addRow("Descrição no orçamento", self.descricao_no_orcamento_input)
        form.addRow("Ref. matéria-prima", self.ref_materia_prima_input)
        form.addRow("Descrição matéria-prima", self.descricao_materia_prima_input)
        form.addRow("Valor texto", self.valor_texto_input)
        form.addRow("Preço tabela", self.preco_tabela_input)
        form.addRow("Margem", self.margem_input)
        form.addRow("Desconto", self.desconto_input)
        form.addRow("Preço líquido", self.preco_liquido_input)
        form.addRow("Unidade", self.unidade_input)
        form.addRow("Desperdício", self.desperdicio_input)
        form.addRow("Tipo matéria-prima", self.tipo_mp_input)
        form.addRow("Família matéria-prima", self.familia_mp_input)
        form.addRow("Orla 0.4 (duplo clique para selecionar)", self.orla_0_4_input)
        form.addRow("Preço orla 0.4", self.preco_orla_0_4_input)
        form.addRow("Orla 1.0 (duplo clique para selecionar)", self.orla_1_0_input)
        form.addRow("Preço orla 1.0", self.preco_orla_1_0_input)
        form.addRow("Comp MP", self.comp_mp_input)
        form.addRow("Larg MP", self.larg_mp_input)
        form.addRow("Esp MP", self.esp_mp_input)
        form.addRow("Origem dados", self.origem_dados_input)
        form.addRow("Editado localmente", self.editado_localmente_input)
        form.addRow("Prioridade", self.prioridade_input)
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Observações", self.observacoes_input)
        form.addRow("Ativo", self.ativo_input)

        form_widget = QWidget()
        form_widget.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_widget)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.operacoes_button = self.button_box.addButton(
            "Operações da linha…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.operacoes_button.setToolTip(
            "Operações específicas desta variante, com ação explícita para "
            "adicionar, substituir ou desativar operações base."
        )
        self.operacoes_button.setEnabled(self._is_edit)
        if not self._is_edit:
            self.operacoes_button.setToolTip(
                "Grave a linha primeiro para poder associar operações."
            )
        self.save_as_button = self.button_box.addButton(
            "Gravar como…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.save_as_button.setToolTip(
            "Grava estes dados como um registo novo, sem alterar o original."
        )
        self.save_as_button.setVisible(self._is_edit)
        self.button_box.accepted.connect(self._validate_and_accept)
        self.operacoes_button.clicked.connect(self.abrir_operacoes_da_linha)
        self.save_as_button.clicked.connect(self._validate_and_save_as)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._connect_recalculo()
        self.orla_0_4_input.doubleClicked.connect(lambda: self._abrir_picker_orla("0_4"))
        self.orla_1_0_input.doubleClicked.connect(lambda: self._abrir_picker_orla("1_0"))

        if linha is not None:
            self._load_linha(linha)

    def abrir_operacoes_da_linha(self) -> None:
        """Open the operation manager for this existing ValueSet model line."""
        if self.linha is None:
            return

        linha_id = self.linha.id

        def listar_operacoes():
            with SessionLocal() as session:
                return DefValuesetModeloLinhaOperacaoService(
                    session
                ).listar_operacoes_da_linha(linha_id)

        def criar_operacao(form_data) -> None:
            with SessionLocal() as session:
                DefValuesetModeloLinhaOperacaoService(session).adicionar_operacao_a_linha(
                    CriarDefValuesetModeloLinhaOperacaoData(
                        def_valueset_modelo_linha_id=linha_id,
                        def_operacao_id=form_data.def_operacao_id,
                        ordem=form_data.ordem,
                        acao=form_data.acao,
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

        def editar_operacao(ligacao_id: int, form_data) -> None:
            with SessionLocal() as session:
                DefValuesetModeloLinhaOperacaoService(session).editar_operacao_da_linha(
                    ligacao_id,
                    EditarDefValuesetModeloLinhaOperacaoData(
                        def_valueset_modelo_linha_id=linha_id,
                        def_operacao_id=form_data.def_operacao_id,
                        ordem=form_data.ordem,
                        acao=form_data.acao,
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

        def alternar_operacao(ligacao) -> None:
            with SessionLocal() as session:
                service = DefValuesetModeloLinhaOperacaoService(session)
                if ligacao.ativo:
                    service.desativar_operacao_da_linha(ligacao.id)
                else:
                    service.ativar_operacao_da_linha(ligacao.id)

        dialog = ValuesetLinhaOperacoesDialog(
            titulo="Operações da linha ValueSet",
            listar_operacoes=listar_operacoes,
            criar_operacao=criar_operacao,
            editar_operacao=editar_operacao,
            alternar_operacao=alternar_operacao,
            parent=self,
            natureza_peca=natureza_peca_da_chave(
                obter_valor_chave_combo(self.chave_input)
            ),
            configuracoes_existentes=carregar_configuracoes_para_sugestoes(
                excluir_modelo_linha_id=linha_id
            ),
        )
        dialog.exec()
        if dialog.alterado:
            self.operacoes_alteradas = True

    def _connect_recalculo(self) -> None:
        """Wire price recompute and local-edit detection to the input fields."""
        for widget in (self.preco_tabela_input, self.margem_input, self.desconto_input):
            widget.textChanged.connect(self._recalcular_preco_liquido)

        for widget in (
            self.ref_le_input,
            self.descricao_no_orcamento_input,
            self.ref_materia_prima_input,
            self.descricao_materia_prima_input,
            self.valor_texto_input,
            self.preco_tabela_input,
            self.margem_input,
            self.desconto_input,
            self.preco_liquido_input,
            self.unidade_input,
            self.desperdicio_input,
            self.tipo_mp_input,
            self.familia_mp_input,
            self.orla_0_4_input,
            self.orla_1_0_input,
            self.preco_orla_0_4_input,
            self.preco_orla_1_0_input,
            self.comp_mp_input,
            self.larg_mp_input,
            self.esp_mp_input,
        ):
            widget.textChanged.connect(self._marcar_editado_se_necessario)

    def _recalcular_preco_liquido(self, *_args) -> None:
        """Recompute preco_liquido from table price, margin and discount."""
        if self._suppress:
            return

        try:
            preco_tabela = parse_decimal_humano(self.preco_tabela_input.text())
            margem = parse_decimal_humano(self.margem_input.text())
            desconto = parse_decimal_humano(self.desconto_input.text())
        except ValueError:
            return

        resultado = self._calcular_preco_liquido(preco_tabela, margem, desconto)
        if resultado is None:
            return

        self._suppress = True
        try:
            self.preco_liquido_input.setText(self._format_decimal(resultado))
        finally:
            self._suppress = False

    def _marcar_editado_se_necessario(self, *_args) -> None:
        """Flag a previously imported line as locally edited when changed."""
        if self._suppress:
            return

        if self.origem_dados_input.currentText().strip().upper() == "MATERIA_PRIMA":
            self._suppress = True
            try:
                self.origem_dados_input.setCurrentText("EDITADO_LOCALMENTE")
                self.editado_localmente_input.setChecked(True)
            finally:
                self._suppress = False

    def _load_linha(self, linha: DefValuesetModeloLinhaResumo) -> None:
        """Populate the form with an existing model line."""
        self._suppress = True
        try:
            self._fill_from_linha(linha)
        finally:
            self._suppress = False

    def _fill_from_linha(self, linha: DefValuesetModeloLinhaResumo) -> None:
        self._codigo_opcao_original = linha.codigo_opcao
        self.codigo_opcao_input.setText(linha.codigo_opcao or "")
        self.nome_opcao_input.setText(linha.nome_opcao or "")
        self.ref_materia_prima_input.setText(linha.ref_materia_prima or "")
        self.descricao_materia_prima_input.setText(linha.descricao_materia_prima or "")
        self.valor_texto_input.setText(linha.valor_texto or "")
        self.prioridade_input.setText(
            "" if linha.prioridade is None else str(linha.prioridade)
        )
        self.ordem_input.setText(str(linha.ordem))
        self.observacoes_input.setText(linha.observacoes or "")
        self.ativo_input.setChecked(linha.ativo)

        self.ref_le_input.setText(linha.ref_le or "")
        self.descricao_no_orcamento_input.setText(linha.descricao_no_orcamento or "")
        self.preco_tabela_input.setText(self._format_decimal(linha.preco_tabela))
        self.margem_input.setText(self._format_decimal(linha.margem_percentagem))
        self.desconto_input.setText(self._format_decimal(linha.desconto_percentagem))
        self.preco_liquido_input.setText(self._format_decimal(linha.preco_liquido))
        self.unidade_input.setText(linha.unidade or "")
        self.desperdicio_input.setText(self._format_decimal(linha.desperdicio_percentagem))
        self.tipo_mp_input.setText(linha.tipo_materia_prima or "")
        self.familia_mp_input.setText(linha.familia_materia_prima or "")
        self.orla_0_4_input.setText(linha.coresp_orla_0_4 or "")
        self.orla_1_0_input.setText(linha.coresp_orla_1_0 or "")
        self.preco_orla_0_4_input.setText(self._format_decimal(linha.preco_orla_0_4_m2))
        self.preco_orla_1_0_input.setText(self._format_decimal(linha.preco_orla_1_0_m2))
        self.comp_mp_input.setText(self._format_decimal(linha.comp_mp))
        self.larg_mp_input.setText(self._format_decimal(linha.larg_mp))
        self.esp_mp_input.setText(self._format_decimal(linha.esp_mp))
        self.origem_dados_input.setCurrentText(linha.origem_dados or "")
        self.editado_localmente_input.setChecked(linha.editado_localmente)

    def abrir_picker_materia_prima(self) -> None:
        """Open the raw material picker and copy the selection into the line."""
        picker = MateriaPrimaPickerDialog(parent=self)
        if picker.exec() and picker.selected_materia is not None:
            self._preencher_de_materia_prima(picker.selected_materia)

    def _abrir_picker_orla(self, espessura: str) -> None:
        """Select one ORL reference and snapshot its EUR/m² price."""
        picker = MateriaPrimaPickerDialog(
            parent=self, initial_familia="ORLA", apenas_orlas=True
        )
        if not picker.exec() or picker.selected_materia is None:
            return
        materia = picker.selected_materia
        ref_input = self.orla_0_4_input if espessura == "0_4" else self.orla_1_0_input
        preco_input = (
            self.preco_orla_0_4_input if espessura == "0_4" else self.preco_orla_1_0_input
        )
        ref_input.setText(materia.ref_le or "")
        preco_input.setText(self._format_decimal(materia.preco_liquido))

    def _preencher_de_materia_prima(self, materia) -> None:
        """Copy the raw material snapshot into the line fields (still editable)."""
        self._suppress = True
        try:
            margem = normalize_percentagem_humana(materia.margem)
            desconto = normalize_percentagem_humana(materia.desconto)

            self.ref_le_input.setText(materia.ref_le or "")
            self.descricao_no_orcamento_input.setText(materia.descricao or "")
            self.ref_materia_prima_input.setText(materia.ref_le or "")
            self.descricao_materia_prima_input.setText(materia.descricao or "")
            self.preco_tabela_input.setText(self._format_decimal(materia.preco_tabela))
            self.margem_input.setText(self._format_decimal(margem))
            self.desconto_input.setText(self._format_decimal(desconto))
            self.preco_liquido_input.setText(
                self._format_decimal(
                    self._calcular_preco_liquido(materia.preco_tabela, margem, desconto)
                    if materia.preco_tabela is not None
                    else materia.preco_liquido
                )
            )
            self.unidade_input.setText(materia.unidade or "")
            self.desperdicio_input.setText(
                self._format_decimal(
                    normalize_percentagem_humana(materia.desperdicio_percentagem)
                )
            )
            self.tipo_mp_input.setText(tipo_materia_prima(materia) or "")
            self.familia_mp_input.setText(familia_materia_prima(materia) or "")
            self.orla_0_4_input.setText(coresp_orla_0_4(materia) or "")
            self.orla_1_0_input.setText(coresp_orla_1_0(materia) or "")
            preco_fina, preco_grossa = obter_precos_orlas_m2(materia)
            self.preco_orla_0_4_input.setText(self._format_decimal(preco_fina))
            self.preco_orla_1_0_input.setText(self._format_decimal(preco_grossa))
            self.comp_mp_input.setText(self._format_decimal(materia.comprimento))
            self.larg_mp_input.setText(self._format_decimal(materia.largura))
            self.esp_mp_input.setText(self._format_decimal(materia.espessura))
            self.origem_dados_input.setCurrentText("MATERIA_PRIMA")
            self.editado_localmente_input.setChecked(False)

            self.nome_opcao_input.setText(materia.descricao or materia.ref_le or "")
            if not self.valor_texto_input.text().strip():
                self.valor_texto_input.setText(materia.descricao or "")
        finally:
            self._suppress = False

    def _calcular_preco_liquido(
        self, preco_tabela: Decimal | None, margem: Decimal | None, desconto: Decimal | None
    ) -> Decimal | None:
        """Return the shared ValueSet liquid price calculation."""
        return calcular_preco_liquido(preco_tabela, margem, desconto)

    def get_data(self) -> DefValuesetModeloLinhaDialogData:
        """Return dialog data (raises ValueError on invalid numbers)."""
        return DefValuesetModeloLinhaDialogData(
            chave=obter_valor_chave_combo(self.chave_input),
            codigo_opcao=(self._codigo_opcao_original or "") if self._is_edit else "",
            nome_opcao=self.nome_opcao_input.text().strip(),
            ref_materia_prima=self._empty_to_none(self.ref_materia_prima_input.text()),
            descricao_materia_prima=self._empty_to_none(
                self.descricao_materia_prima_input.text()
            ),
            valor_texto=self._empty_to_none(self.valor_texto_input.text()),
            prioridade=self._parse_prioridade(),
            ordem=self._parse_ordem(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
            ref_le=self._empty_to_none(self.ref_le_input.text()),
            descricao_no_orcamento=self._empty_to_none(
                self.descricao_no_orcamento_input.text()
            ),
            preco_tabela=self._parse_optional_decimal(self.preco_tabela_input, "Preço tabela"),
            margem_percentagem=self._parse_optional_decimal(self.margem_input, "Margem %"),
            desconto_percentagem=self._parse_optional_decimal(self.desconto_input, "Desconto %"),
            preco_liquido=self._parse_optional_decimal(self.preco_liquido_input, "Preço líquido"),
            unidade=self._empty_to_none(self.unidade_input.text()),
            desperdicio_percentagem=self._parse_optional_decimal(
                self.desperdicio_input, "Desperdício %"
            ),
            tipo_materia_prima=self._empty_to_none(self.tipo_mp_input.text()),
            familia_materia_prima=self._empty_to_none(self.familia_mp_input.text()),
            coresp_orla_0_4=self._empty_to_none(self.orla_0_4_input.text()),
            coresp_orla_1_0=self._empty_to_none(self.orla_1_0_input.text()),
            preco_orla_0_4_m2=self._parse_optional_decimal(
                self.preco_orla_0_4_input, "Preço orla 0.4 (€/m²)"
            ),
            preco_orla_1_0_m2=self._parse_optional_decimal(
                self.preco_orla_1_0_input, "Preço orla 1.0 (€/m²)"
            ),
            comp_mp=self._parse_optional_decimal(self.comp_mp_input, "Comp MP"),
            larg_mp=self._parse_optional_decimal(self.larg_mp_input, "Larg MP"),
            esp_mp=self._parse_optional_decimal(self.esp_mp_input, "Esp MP"),
            origem_dados=self._empty_to_none(self.origem_dados_input.currentText()),
            editado_localmente=self.editado_localmente_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields and save before accepting."""
        self._validate_and_run(self.on_save)

    def _validate_and_save_as(self) -> None:
        """Validate required fields and save as a new record before accepting."""
        self._validate_and_run(self.on_save_as)

    def _validate_and_run(
        self,
        callback: Callable[[DefValuesetModeloLinhaDialogData], bool] | None,
    ) -> None:
        """Run validation, then delegate to the requested save callback."""
        if obter_valor_chave_combo(self.chave_input) is None:
            self.set_error("Selecione uma chave ValueSet.")
            return

        if not self.nome_opcao_input.text().strip():
            self.set_error("A opção é obrigatória.")
            return

        self._recalcular_preco_liquido()

        try:
            data = self.get_data()
        except ValueError as error:
            self.set_error(str(error))
            return

        self.error_label.clear()
        if callback is not None and not callback(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _parse_ordem(self) -> int:
        text = self.ordem_input.text().strip()
        if not text:
            return 1

        try:
            return int(text)
        except ValueError as error:
            raise ValueError("Ordem inválida. Use um número inteiro.") from error

    def _parse_prioridade(self) -> int | None:
        text = self.prioridade_input.text().strip()
        if not text:
            return None

        try:
            prioridade = int(text)
        except ValueError as error:
            raise ValueError(
                "Prioridade inválida. Use um número inteiro (1 = primeira escolha)."
            ) from error

        if prioridade < 1:
            raise ValueError("Prioridade inválida. Use um número inteiro maior ou igual a 1.")

        return prioridade

    def _parse_optional_decimal(self, widget: QLineEdit, label: str) -> Decimal | None:
        try:
            return parse_decimal_humano(widget.text())
        except ValueError as error:
            raise ValueError(f"{label} inválido. Use um número, por exemplo 1.5.") from error

    def _format_decimal(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value.normalize(), "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
