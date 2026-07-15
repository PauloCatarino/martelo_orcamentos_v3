"""Dialog for editing one ValueSet line of a budget item."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

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

from app.db.session import SessionLocal
from app.domain.materia_prima_snapshot import (
    coresp_orla_0_4,
    coresp_orla_1_0,
    familia_materia_prima,
    tipo_materia_prima,
)
from app.domain.numeros import normalize_percentagem_humana, parse_decimal_humano
from app.domain.valueset_precos import calcular_preco_liquido
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaResumo,
)
from app.services.orcamento_item_valueset_linha_operacao_service import (
    CriarOrcamentoItemValuesetLinhaOperacaoData,
    EditarOrcamentoItemValuesetLinhaOperacaoData,
    OrcamentoItemValuesetLinhaOperacaoService,
)
from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog
from app.ui.helpers.orla_picker import obter_precos_orlas_m2
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

ORIGEM_DADOS_OPCOES = (
    "VALUESET_ORCAMENTO",
    "MODELO_VALUESET",
    "MATERIA_PRIMA",
    "LIVRE",
    "EDITADO_LOCALMENTE",
)

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


@dataclass(frozen=True)
class OrcamentoItemValuesetLinhaDialogData:
    """Data collected by the budget item ValueSet line dialog."""

    chave: str | None
    codigo_opcao: str
    nome_opcao: str
    ref_le: str | None
    descricao_no_orcamento: str | None
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    valor_texto: str | None
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
    prioridade: int | None
    ordem: int
    observacoes: str | None
    ativo: bool


class OrcamentoItemValuesetLinhaDialog(QDialog):
    """Modal dialog for editing one budget item ValueSet line locally."""

    def __init__(
        self,
        linha: OrcamentoItemValuesetLinhaResumo,
        parent=None,
        on_save: Callable[[OrcamentoItemValuesetLinhaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.linha = linha
        self.on_save = on_save
        self._suppress = False
        self.operacoes_alteradas = False

        self.setWindowTitle("Editar Linha ValueSet do Item")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.chave_input = QComboBox()
        carregar_chaves_valueset_combo(self.chave_input, valor_atual=linha.chave)
        self.chave_input.setEnabled(False)

        self.codigo_opcao_input = QLineEdit()
        self.nome_opcao_input = QLineEdit()
        self.ref_le_input = QLineEdit()
        self.descricao_no_orcamento_input = QLineEdit()
        self.ref_materia_prima_input = QLineEdit()
        self.descricao_materia_prima_input = QLineEdit()
        self.valor_texto_input = QLineEdit()
        self.preco_tabela_input = QLineEdit()
        self.margem_input = QLineEdit()
        self.desconto_input = QLineEdit()
        self.preco_liquido_input = QLineEdit()
        self.unidade_input = QLineEdit()
        self.desperdicio_input = QLineEdit()
        self.tipo_mp_input = QLineEdit()
        self.familia_mp_input = QLineEdit()
        self.orla_0_4_input = OrlaLineEdit()
        self.orla_1_0_input = OrlaLineEdit()
        self.preco_orla_0_4_input = QLineEdit()
        self.preco_orla_1_0_input = QLineEdit()
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
        self.editado_localmente_input = QCheckBox()
        self.prioridade_input = QLineEdit()
        self.prioridade_input.setPlaceholderText("Ex.: 1 (vazio = nunca escolhida)")
        self.prioridade_input.setToolTip(PRIORIDADE_TOOLTIP)
        self.ordem_input = QLineEdit()
        self.ordem_input.setText("1")
        self.ordem_input.setToolTip(ORDEM_TOOLTIP)
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.selecionar_mp_button = QPushButton("Selecionar Matéria-Prima")
        self.selecionar_mp_button.clicked.connect(self.abrir_picker_materia_prima)

        self.error_label = QLabel("")
        self.error_label.setObjectName("orcamentoItemValuesetLinhaError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Chave ValueSet", self.chave_input)
        form.addRow("Código opção", self.codigo_opcao_input)
        form.addRow("Nome opção", self.nome_opcao_input)
        form.addRow("", self.selecionar_mp_button)
        form.addRow("Ref LE", self.ref_le_input)
        form.addRow("Descrição no orçamento", self.descricao_no_orcamento_input)
        form.addRow("Ref. matéria-prima", self.ref_materia_prima_input)
        form.addRow("Descrição matéria-prima", self.descricao_materia_prima_input)
        form.addRow("Valor texto", self.valor_texto_input)
        form.addRow("Preço tabela", self.preco_tabela_input)
        form.addRow("Margem %", self.margem_input)
        form.addRow("Desconto %", self.desconto_input)
        form.addRow("Preço líquido", self.preco_liquido_input)
        form.addRow("Unidade", self.unidade_input)
        form.addRow("Desperdício %", self.desperdicio_input)
        form.addRow("Tipo matéria-prima", self.tipo_mp_input)
        form.addRow("Família matéria-prima", self.familia_mp_input)
        form.addRow("Orla 0.4 (duplo clique para selecionar)", self.orla_0_4_input)
        form.addRow("Preço orla 0.4 (€/m²)", self.preco_orla_0_4_input)
        form.addRow("Orla 1.0 (duplo clique para selecionar)", self.orla_1_0_input)
        form.addRow("Preço orla 1.0 (€/m²)", self.preco_orla_1_0_input)
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
        self.button_box.accepted.connect(self._validate_and_accept)
        self.operacoes_button.clicked.connect(self.abrir_operacoes_da_linha)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._load_linha(linha)
        self._connect_recalculo()
        self.orla_0_4_input.doubleClicked.connect(lambda: self._abrir_picker_orla("0_4"))
        self.orla_1_0_input.doubleClicked.connect(lambda: self._abrir_picker_orla("1_0"))

    def abrir_operacoes_da_linha(self) -> None:
        """Open the operation manager for this budget item ValueSet line."""
        linha_id = self.linha.id

        def listar_operacoes():
            with SessionLocal() as session:
                return OrcamentoItemValuesetLinhaOperacaoService(
                    session
                ).listar_operacoes_da_linha(linha_id)

        def criar_operacao(form_data) -> None:
            with SessionLocal() as session:
                OrcamentoItemValuesetLinhaOperacaoService(session).adicionar_operacao_a_linha(
                    CriarOrcamentoItemValuesetLinhaOperacaoData(
                        orcamento_item_valueset_linha_id=linha_id,
                        def_operacao_id=form_data.def_operacao_id,
                        ordem=form_data.ordem,
                        acao=form_data.acao,
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
                OrcamentoItemValuesetLinhaOperacaoService(session).editar_operacao_da_linha(
                    ligacao_id,
                    EditarOrcamentoItemValuesetLinhaOperacaoData(
                        orcamento_item_valueset_linha_id=linha_id,
                        def_operacao_id=form_data.def_operacao_id,
                        ordem=form_data.ordem,
                        acao=form_data.acao,
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
                service = OrcamentoItemValuesetLinhaOperacaoService(session)
                if ligacao.ativo:
                    service.desativar_operacao_da_linha(ligacao.id)
                else:
                    service.ativar_operacao_da_linha(ligacao.id)

        dialog = ValuesetLinhaOperacoesDialog(
            titulo="Operações da linha ValueSet do item",
            listar_operacoes=listar_operacoes,
            criar_operacao=criar_operacao,
            editar_operacao=editar_operacao,
            alternar_operacao=alternar_operacao,
            parent=self,
            natureza_peca=natureza_peca_da_chave(
                obter_valor_chave_combo(self.chave_input)
            ),
            configuracoes_existentes=carregar_configuracoes_para_sugestoes(),
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
            self.codigo_opcao_input,
            self.nome_opcao_input,
        ):
            widget.textChanged.connect(self._marcar_editado_se_necessario)

    def _load_linha(self, linha: OrcamentoItemValuesetLinhaResumo) -> None:
        """Populate the form with the line values."""
        self._suppress = True
        try:
            self.codigo_opcao_input.setText(linha.codigo_opcao or "")
            self.nome_opcao_input.setText(linha.nome_opcao or "")
            self.ref_le_input.setText(linha.ref_le or "")
            self.descricao_no_orcamento_input.setText(linha.descricao_no_orcamento or "")
            self.ref_materia_prima_input.setText(linha.ref_materia_prima or "")
            self.descricao_materia_prima_input.setText(linha.descricao_materia_prima or "")
            self.valor_texto_input.setText(linha.valor_texto or "")
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
            self.prioridade_input.setText(
                "" if linha.prioridade is None else str(linha.prioridade)
            )
            self.ordem_input.setText(str(linha.ordem))
            self.observacoes_input.setText(linha.observacoes or "")
            self.ativo_input.setChecked(linha.ativo)
        finally:
            self._suppress = False

    def abrir_picker_materia_prima(self) -> None:
        """Open the raw material picker and copy the selection into the line."""
        picker = MateriaPrimaPickerDialog(parent=self)
        if picker.exec() and picker.selected_materia is not None:
            self._preencher_de_materia_prima(picker.selected_materia)

    def _abrir_picker_orla(self, espessura: str) -> None:
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
        """Copy the raw material snapshot into the line (marks it locally chosen)."""
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
            self.editado_localmente_input.setChecked(True)
        finally:
            self._suppress = False

    def _calcular_preco_liquido(
        self, preco_tabela: Decimal | None, margem: Decimal | None, desconto: Decimal | None
    ) -> Decimal | None:
        """Return the shared ValueSet liquid price calculation."""
        return calcular_preco_liquido(preco_tabela, margem, desconto)

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
        """Flag the line as locally edited when a relevant field changes."""
        if self._suppress:
            return

        if self.origem_dados_input.currentText().strip().upper() != "EDITADO_LOCALMENTE":
            self._suppress = True
            try:
                self.origem_dados_input.setCurrentText("EDITADO_LOCALMENTE")
                self.editado_localmente_input.setChecked(True)
            finally:
                self._suppress = False

    def get_data(self) -> OrcamentoItemValuesetLinhaDialogData:
        """Return dialog data (raises ValueError on invalid numbers)."""
        return OrcamentoItemValuesetLinhaDialogData(
            chave=obter_valor_chave_combo(self.chave_input),
            codigo_opcao=self.codigo_opcao_input.text().strip(),
            nome_opcao=self.nome_opcao_input.text().strip(),
            ref_le=self._empty_to_none(self.ref_le_input.text()),
            descricao_no_orcamento=self._empty_to_none(
                self.descricao_no_orcamento_input.text()
            ),
            ref_materia_prima=self._empty_to_none(self.ref_materia_prima_input.text()),
            descricao_materia_prima=self._empty_to_none(
                self.descricao_materia_prima_input.text()
            ),
            valor_texto=self._empty_to_none(self.valor_texto_input.text()),
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
            prioridade=self._parse_prioridade(),
            ordem=self._parse_ordem(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        if not self.codigo_opcao_input.text().strip():
            self.set_error("O código da opção é obrigatório.")
            return

        if not self.nome_opcao_input.text().strip():
            self.set_error("O nome da opção é obrigatório.")
            return

        self._recalcular_preco_liquido()

        try:
            data = self.get_data()
        except ValueError as error:
            self.set_error(str(error))
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
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
