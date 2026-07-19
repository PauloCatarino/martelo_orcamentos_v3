"""Dialog for linking an operation to a piece definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from PySide6.QtGui import QColor, QFont

from app.domain.custo_producao import calcular_custo_por_minutos, calcular_tempo_operacao
from app.domain.custo_producao import calcular_comprimento_rasgo_ml, calcular_custo_rasgo_cnc
from app.domain.custo_producao import (
    calcular_custo_cnc,
    calcular_custo_corte,
    calcular_custo_orlagem_lados,
    selecionar_escalao_area,
)
from app.domain.medidas import normalizar_numero
from app.domain.peca_natureza_types import FERRAGEM
from app.domain.tempos_producao import classificar_operacao
from app.domain.operacao_guia import (
    CAMPO_QUANTIDADE_BASE,
    CAMPO_TEMPO_POR_UNIDADE,
    CAMPO_TEMPO_SETUP,
    CAMPO_UNIDADE_TEMPO,
    construir_guia_operacao,
)
# The recipe field keys for quantity/times/unit share the guide's values.
from app.domain.operacao_receitas import (
    CAMPO_METODO_CALCULO,
    CAMPO_RASGO_QT_COMP,
    CAMPO_RASGO_QT_LARG,
    CAMPO_REGRA_CALCULO,
    get_receitas_operacao,
)
from app.domain import metodo_calculo_types as metodo_types
from types import SimpleNamespace
from app.domain.configuracao_sugestoes import (
    ConfigOperacaoExistente,
    construir_sugestoes_operacao,
)
from app.domain.regra_operacao_types import FIXA, RASGO_CNC
from app.domain.regra_operacao_types import get_regra_operacao_options, normalize_regra_operacao
from app.domain.operacao_acao_types import (
    ADICIONAR,
    get_operacao_acao_options,
    normalize_operacao_acao,
)
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.repositories.def_peca_operacao_repository import DefPecaOperacaoResumo
from app.utils.formatters import format_currency, format_quantity


# Stored values are unchanged; only the visible labels are clearer for the user.
UNIDADE_TEMPO_OPCOES = ("", "PECA", "ML", "M2", "FURO", "UN", "HORA", "OPERACAO", "LOTE")
UNIDADE_TEMPO_LABELS = {
    "": "(nenhuma)",
    "PECA": "Por peça (multiplica pela QT)",
    "ML": "Por metro linear",
    "M2": "Por m2 de peça",
    "FURO": "Por furo (× QT)",
    "UN": "Por unidade (× QT)",
    "HORA": "Por hora (quantidade base em horas)",
    "OPERACAO": "Por operação (fixo, não multiplica pela QT)",
    "LOTE": "Por lote (fixo)",
}


@dataclass(frozen=True)
class DefPecaOperacaoDialogData:
    """Data collected by the piece operation dialog."""

    def_operacao_id: int | None
    ordem: int
    regra_calculo: str | None
    quantidade_base: Decimal | None
    rasgo_qt_comp: int
    rasgo_qt_larg: int
    tempo_setup_minutos: Decimal | None
    tempo_por_unidade_minutos: Decimal | None
    unidade_tempo: str | None
    obrigatorio: bool
    ativo: bool
    observacoes: str | None
    acao: str = ADICIONAR
    metodo_calculo: str | None = None


@dataclass(frozen=True)
class SimulacaoOperacaoResultado:
    """Result of a simulated operation time/cost calculation."""

    qt_total: Decimal
    setup_minutos: Decimal
    variavel_minutos: Decimal
    tempo_total_minutos: Decimal | None
    custo: Decimal | None


def calcular_simulacao_operacao(
    *,
    unidade_tempo: str | None,
    quantidade_base: Decimal | None,
    tempo_setup_minutos: Decimal | None,
    tempo_por_unidade_minutos: Decimal | None,
    area_m2: Decimal | None,
    ml: Decimal | None,
    qt_total: Decimal | None,
    custo_hora: Decimal | None,
) -> SimulacaoOperacaoResultado:
    """Calculate one simulator row using the production-cost pure helpers."""
    unidade = (unidade_tempo or "").strip().upper() or None
    base_calculo = ml if unidade == "ML" and ml is not None else quantidade_base
    area_calculo = area_m2 if unidade == "M2" else None
    qt = qt_total if qt_total is not None else Decimal("1")

    setup_min, variavel_min = calcular_tempo_operacao(
        unidade,
        base_calculo,
        tempo_setup_minutos,
        tempo_por_unidade_minutos,
        area_calculo,
        qt,
    )
    if setup_min is None and variavel_min is None:
        return SimulacaoOperacaoResultado(
            qt_total=qt,
            setup_minutos=Decimal("0"),
            variavel_minutos=Decimal("0"),
            tempo_total_minutos=None,
            custo=None,
        )

    setup = setup_min or Decimal("0")
    variavel = variavel_min or Decimal("0")
    total = setup + variavel
    return SimulacaoOperacaoResultado(
        qt_total=qt,
        setup_minutos=setup,
        variavel_minutos=variavel,
        tempo_total_minutos=total,
        custo=calcular_custo_por_minutos(total, custo_hora),
    )


class DefPecaOperacaoDialog(QDialog):
    """Modal dialog for linking or editing an operation of a piece definition."""

    def __init__(
        self,
        operacoes_disponiveis: list[DefOperacaoResumo],
        ligacao: DefPecaOperacaoResumo | None = None,
        parent=None,
        on_save: Callable[[DefPecaOperacaoDialogData], bool] | None = None,
        mostrar_acao: bool = False,
        natureza_peca: str | None = None,
        configuracoes_existentes: list[ConfigOperacaoExistente] | None = None,
    ) -> None:
        super().__init__(parent)

        self.ligacao = ligacao
        self.on_save = on_save
        self._is_edit = ligacao is not None
        self._mostrar_acao = mostrar_acao
        self._natureza_peca = natureza_peca
        self._configuracoes_existentes = configuracoes_existentes
        self._sugestoes_atual: list = []
        self._regra_rasgo_automatica = False
        self._operacoes_por_id = {
            operacao.id: operacao for operacao in operacoes_disponiveis
        }

        self.setWindowTitle("Editar Operação da Peça" if self._is_edit else "Nova Operação da Peça")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.operacao_input = QComboBox()
        for operacao in operacoes_disponiveis:
            self.operacao_input.addItem(f"{operacao.codigo} - {operacao.nome}", operacao.id)
        self.operacao_input.setToolTip(
            "Operação do catálogo a ligar à peça. Nas CNC a operação É a "
            "máquina; o método de cálculo escolhe-se a seguir."
        )

        # New CNC model: the method combo appears for CNC/coating operations
        # and only lists the methods the machine allows.
        self.metodo_input = QComboBox()
        self.metodo_input.setToolTip(
            "Como esta operação é custeada: escalões de área, tempo, furação, "
            "rasgo ou revestimento. A lista mostra apenas os métodos que a "
            "máquina permite."
        )

        self.ordem_input = QSpinBox()
        self.ordem_input.setRange(1, 9999)
        self.ordem_input.setValue(1)
        self.ordem_input.setToolTip(
            "Ordem de apresentação da operação na lista (não altera o custo)."
        )

        self.acao_input = QComboBox()
        for code, label in get_operacao_acao_options():
            self.acao_input.addItem(label, code)
        self.acao_input.setToolTip(
            "Adicionar mantém as operações base; Substituir troca a operação do "
            "mesmo tipo; Desativar remove a operação selecionada."
        )

        # G3: one-step presets that fill the right fields for a common intent.
        self.receita_input = QComboBox()
        self.receita_input.addItem("— escolher receita —", None)
        for receita in get_receitas_operacao():
            self.receita_input.addItem(receita.label, receita.key)
            self.receita_input.setItemData(
                self.receita_input.count() - 1,
                receita.descricao,
                Qt.ItemDataRole.ToolTipRole,
            )
        self.receita_input.setToolTip(
            "Preenche de uma vez os campos certos para o caso escolhido "
            "(regra, unidade, tempos). Os valores ficam editáveis."
        )
        self.receita_input.currentIndexChanged.connect(self._aplicar_receita_selecionada)

        # G4: deterministic copy suggestions from configurations that already
        # exist for the selected operation (other pieces / ValueSet lines).
        self.sugestao_input = QComboBox()
        self.sugestao_input.setToolTip(
            "Configurações já existentes desta operação noutras peças ou "
            "linhas ValueSet. Escolher uma copia os valores (regra, "
            "quantidade, tempos, unidade) para este formulário."
        )
        self.sugestao_input.currentIndexChanged.connect(
            self._aplicar_sugestao_selecionada
        )

        self.regra_calculo_input = QComboBox()
        for code, label in get_regra_operacao_options():
            sufixo = "" if code == RASGO_CNC else " (informativa)"
            self.regra_calculo_input.addItem(f"{label}{sufixo}", code)
        self.regra_calculo_input.setToolTip(
            "Informativa: documenta o critério mas não altera o custo. "
            "Exceção: 'Rasgo CNC por comprimento geométrico', que ativa o "
            "custeio do rasgo (selecionada automaticamente na operação "
            "CNC_RASGO)."
        )

        self.quantidade_base_input = QLineEdit()
        self.quantidade_base_input.setPlaceholderText("Ex.: 1.5")
        self.rasgo_qt_comp_input = QSpinBox()
        self.rasgo_qt_comp_input.setRange(0, 99)
        self.rasgo_qt_comp_input.setToolTip(
            "Quantos rasgos seguem o COMPRIMENTO da peça (cada um mede COMP)."
        )
        self.rasgo_qt_larg_input = QSpinBox()
        self.rasgo_qt_larg_input.setRange(0, 99)
        self.rasgo_qt_larg_input.setToolTip(
            "Quantos rasgos seguem a LARGURA da peça (cada um mede LARG)."
        )

        self.tempo_setup_input = QLineEdit()
        self.tempo_setup_input.setPlaceholderText("Ex.: 2 (minutos)")
        self.tempo_por_unidade_input = QLineEdit()
        self.tempo_por_unidade_input.setPlaceholderText("Ex.: 0.35 (min/unidade)")
        self.unidade_tempo_input = QComboBox()
        for opcao in UNIDADE_TEMPO_OPCOES:
            self.unidade_tempo_input.addItem(UNIDADE_TEMPO_LABELS[opcao], opcao or None)

        self.obrigatorio_input = QCheckBox()
        self.obrigatorio_input.setChecked(True)
        self.obrigatorio_input.setToolTip(
            "Marca a operação como obrigatória na definição da peça "
            "(informativo; não altera o custo)."
        )
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)
        self.ativo_input.setToolTip(
            "Só as operações ativas entram no custeio."
        )

        self.observacoes_input = QLineEdit()
        self.observacoes_input.setToolTip(
            "Notas livres sobre esta operação (não alteram o custo)."
        )

        # Base tooltips of the fields the guide enables/disables dynamically;
        # when a field is disabled, the reason is appended to its tooltip.
        self._tooltips_base_guia = {
            CAMPO_QUANTIDADE_BASE: (
                "Quantidade por peça (n.º de furos, unidades, metros…) "
                "multiplicada pelo tempo por unidade. Vazia conta como 1. "
                "Com a unidade 'Por hora' é a duração em horas."
            ),
            CAMPO_TEMPO_SETUP: (
                "Minutos de preparação, somados 1× por linha do orçamento "
                "(não multiplicam pela QT)."
            ),
            CAMPO_TEMPO_POR_UNIDADE: (
                "Minutos por unidade (ex.: 0,05 = 3 seg por furo). "
                "Multiplica pela quantidade calculada."
            ),
            CAMPO_UNIDADE_TEMPO: (
                "Decide a quantidade calculada: por peça/furo/unidade/ML "
                "(× QT), por m² (área × QT), por hora (base em horas) ou "
                "por lote/operação (fixo)."
            ),
        }

        self.guia_label = QLabel("")
        self.guia_label.setObjectName("defPecaOperacaoDialogGuia")
        self.guia_label.setWordWrap(True)
        self.guia_label.setTextFormat(Qt.TextFormat.RichText)
        self.guia_label.setStyleSheet(
            "background-color: #f1f5f9; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 8px; color: #0f172a;"
        )

        self.error_label = QLabel("")
        self.error_label.setObjectName("defPecaOperacaoDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Operação", self.operacao_input)
        self.metodo_label = QLabel("Método de cálculo")
        form.addRow(self.metodo_label, self.metodo_input)
        self.acao_label = QLabel("Ação da variante")
        form.addRow(self.acao_label, self.acao_input)
        self.acao_label.setVisible(mostrar_acao)
        self.acao_input.setVisible(mostrar_acao)
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Configurar como…", self.receita_input)
        self.sugestao_label = QLabel("Copiar configuração de…")
        form.addRow(self.sugestao_label, self.sugestao_input)
        if configuracoes_existentes is None:
            self.sugestao_label.setVisible(False)
            self.sugestao_input.setVisible(False)
        self.regra_label = QLabel("Regra cálculo")
        form.addRow(self.regra_label, self.regra_calculo_input)
        self.quantidade_base_label = QLabel("Quantidade base")
        form.addRow(self.quantidade_base_label, self.quantidade_base_input)
        self.rasgo_comp_label = QLabel("N.º comprimentos do rasgo")
        self.rasgo_larg_label = QLabel("N.º larguras do rasgo")
        form.addRow(self.rasgo_comp_label, self.rasgo_qt_comp_input)
        form.addRow(self.rasgo_larg_label, self.rasgo_qt_larg_input)
        form.addRow("Tempo setup (min)", self.tempo_setup_input)
        form.addRow("Tempo por unidade (min)", self.tempo_por_unidade_input)
        form.addRow("Unidade tempo", self.unidade_tempo_input)
        form.addRow("Obrigatório", self.obrigatorio_input)
        form.addRow("Ativo", self.ativo_input)
        form.addRow("Observações", self.observacoes_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.simular_button = self.button_box.addButton(
            "Simular cálculo…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.simular_button.clicked.connect(self._abrir_simulador)
        self.acao_input.currentIndexChanged.connect(self._update_acao_fields)
        self.operacao_input.currentIndexChanged.connect(self._on_operacao_changed)
        self.metodo_input.currentIndexChanged.connect(self._update_metodo_fields)
        self.regra_calculo_input.currentIndexChanged.connect(self._atualizar_guia)
        self.unidade_tempo_input.currentIndexChanged.connect(self._atualizar_guia)
        for widget in (
            self.quantidade_base_input,
            self.tempo_setup_input,
            self.tempo_por_unidade_input,
        ):
            widget.textChanged.connect(self._atualizar_guia)
        self.rasgo_qt_comp_input.valueChanged.connect(self._atualizar_guia)
        self.rasgo_qt_larg_input.valueChanged.connect(self._atualizar_guia)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.guia_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.operacao_input.currentIndexChanged.connect(self._atualizar_sugestoes)

        self._atualizar_metodos_disponiveis()
        if ligacao is not None:
            self._load_ligacao(ligacao)
        self._update_acao_fields()
        self._update_metodo_fields()
        self._atualizar_sugestoes()
        self._atualizar_receitas()

    def _load_ligacao(self, ligacao: DefPecaOperacaoResumo) -> None:
        """Populate the form with an existing link."""
        index = self.operacao_input.findData(ligacao.def_operacao_id)
        if index >= 0:
            self.operacao_input.setCurrentIndex(index)

        self.ordem_input.setValue(ligacao.ordem)
        acao_index = self.acao_input.findData(
            normalize_operacao_acao(getattr(ligacao, "acao", None))
        )
        if acao_index >= 0:
            self.acao_input.setCurrentIndex(acao_index)
        self._atualizar_metodos_disponiveis()
        self._select_metodo(self._metodo_da_ligacao(ligacao))
        self._select_regra(ligacao.regra_calculo)
        self.quantidade_base_input.setText(self._format_decimal(ligacao.quantidade_base))
        self.rasgo_qt_comp_input.setValue(getattr(ligacao, "rasgo_qt_comp", 0))
        self.rasgo_qt_larg_input.setValue(getattr(ligacao, "rasgo_qt_larg", 0))
        self.tempo_setup_input.setText(self._format_decimal(ligacao.tempo_setup_minutos))
        self.tempo_por_unidade_input.setText(
            self._format_decimal(ligacao.tempo_por_unidade_minutos)
        )
        indice_unidade = self.unidade_tempo_input.findData(ligacao.unidade_tempo)
        if indice_unidade >= 0:
            self.unidade_tempo_input.setCurrentIndex(indice_unidade)
        self.obrigatorio_input.setChecked(ligacao.obrigatorio)
        self.ativo_input.setChecked(ligacao.ativo)
        self.observacoes_input.setText(ligacao.observacoes or "")

    def _select_regra(self, regra: str | None) -> None:
        index = self.regra_calculo_input.findData(normalize_regra_operacao(regra))
        if index >= 0:
            self.regra_calculo_input.setCurrentIndex(index)

    def get_data(self) -> DefPecaOperacaoDialogData:
        """Return normalized dialog data (raises ValueError on invalid quantity)."""
        return DefPecaOperacaoDialogData(
            def_operacao_id=self.operacao_input.currentData(),
            ordem=self.ordem_input.value(),
            regra_calculo=self.regra_calculo_input.currentData(),
            quantidade_base=self._parse_decimal_input(self.quantidade_base_input),
            rasgo_qt_comp=self.rasgo_qt_comp_input.value(),
            rasgo_qt_larg=self.rasgo_qt_larg_input.value(),
            tempo_setup_minutos=self._parse_decimal_input(self.tempo_setup_input),
            tempo_por_unidade_minutos=self._parse_decimal_input(
                self.tempo_por_unidade_input
            ),
            unidade_tempo=self.unidade_tempo_input.currentData(),
            obrigatorio=self.obrigatorio_input.isChecked(),
            ativo=self.ativo_input.isChecked(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            acao=(
                self.acao_input.currentData() if self._mostrar_acao else ADICIONAR
            ),
            metodo_calculo=self._metodo_atual(),
        )

    def _validate_and_accept(self) -> None:
        """Validate the selected operation and quantity before accepting."""
        if self.operacao_input.currentData() is None:
            self.set_error("Selecione uma operação.")
            return

        try:
            data = self.get_data()
        except ValueError:
            self.set_error(
                "Valor numérico inválido (quantidade/tempos). Use um número, por exemplo 1.5."
            )
            return

        self.error_label.clear()
        operacao = self._operacao_selecionada()
        if data.metodo_calculo == metodo_types.RASGO:
            if data.rasgo_qt_comp + data.rasgo_qt_larg <= 0:
                self.set_error("Defina pelo menos um comprimento ou uma largura de rasgo.")
                return
            if not getattr(operacao, "maquina_permite_rasgos", False):
                self.set_error("A máquina associada não permite fresagem de rasgos.")
                return
        if data.metodo_calculo == metodo_types.FURACAO and (
            data.quantidade_base is None or data.quantidade_base <= 0
        ):
            self.set_error("Indique o n.º de furos por unidade (ex.: dobradiça = 3).")
            return
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _update_acao_fields(self) -> None:
        """Disable calculation inputs when the variant only removes an operation."""
        desativar = self._acao_desativar()
        for widget in (
            self.regra_calculo_input,
            self.quantidade_base_input,
            self.tempo_setup_input,
            self.tempo_por_unidade_input,
            self.unidade_tempo_input,
            self.obrigatorio_input,
        ):
            widget.setEnabled(not desativar)
        self.simular_button.setEnabled(not desativar)
        self.receita_input.setEnabled(not desativar)
        self.sugestao_input.setEnabled(not desativar and bool(self._sugestoes_atual))
        self._atualizar_guia()

    # ---------------------------------------------------------- método (CNC)
    def _metodos_da_operacao(self, operacao) -> tuple[str, ...]:
        """Methods the selected operation's machine allows (empty = non-CNC)."""
        if operacao is None:
            return ()
        tipo_operacao = (getattr(operacao, "tipo_operacao", "") or "").strip().upper()
        maquina = SimpleNamespace(
            tipo=(
                metodo_types.REVESTIMENTO
                if tipo_operacao == metodo_types.REVESTIMENTO
                else getattr(operacao, "maquina_tipo", None)
                or ("CNC" if tipo_operacao == "CNC" else None)
            ),
            permite_escaloes_area=getattr(
                operacao, "maquina_permite_escaloes_area", False
            ),
            permite_furacao=getattr(operacao, "maquina_permite_furacao", False),
            permite_rasgos=getattr(operacao, "maquina_permite_rasgos", False),
            permite_pocket=getattr(operacao, "maquina_permite_pocket", False),
        )
        return metodo_types.metodos_disponiveis_para_maquina(maquina)

    def _metodo_atual(self) -> str | None:
        if not self.metodo_input.isVisible() and self.metodo_input.count() == 0:
            return None
        return self.metodo_input.currentData()

    def _metodo_da_ligacao(self, ligacao) -> str | None:
        """Stored method, or the legacy inference for old CNC links."""
        metodo = metodo_types.normalize_metodo_calculo(
            getattr(ligacao, "metodo_calculo", None)
        )
        if metodo is not None:
            return metodo
        operacao = self._operacao_selecionada()
        if not self._metodos_da_operacao(operacao):
            return None
        tem_tempos = (
            getattr(ligacao, "tempo_setup_minutos", None) is not None
            or getattr(ligacao, "tempo_por_unidade_minutos", None) is not None
        )
        natureza = (self._natureza_peca or "").strip().upper()
        return metodo_types.inferir_metodo_calculo_legado(
            getattr(operacao, "codigo", None),
            getattr(ligacao, "regra_calculo", None),
            getattr(ligacao, "rasgo_qt_comp", 0),
            getattr(ligacao, "rasgo_qt_larg", 0),
            tem_tempos and natureza == FERRAGEM,
        )

    def _select_metodo(self, metodo: str | None) -> None:
        if metodo is None:
            return
        index = self.metodo_input.findData(metodo)
        if index >= 0:
            self.metodo_input.setCurrentIndex(index)

    def _atualizar_metodos_disponiveis(self) -> None:
        """Rebuild the method combo for the selected operation's machine."""
        metodos = self._metodos_da_operacao(self._operacao_selecionada())
        atual = self.metodo_input.currentData()
        self.metodo_input.blockSignals(True)
        self.metodo_input.clear()
        for metodo in metodos:
            self.metodo_input.addItem(
                metodo_types.METODO_CALCULO_LABELS[metodo], metodo
            )
        indice = self.metodo_input.findData(atual)
        if indice >= 0:
            self.metodo_input.setCurrentIndex(indice)
        self.metodo_input.blockSignals(False)
        visivel = bool(metodos)
        self.metodo_label.setVisible(visivel)
        self.metodo_input.setVisible(visivel)
        # With a method the informative rule is redundant noise — hide it.
        self.regra_label.setVisible(not visivel)
        self.regra_calculo_input.setVisible(not visivel)

    def _on_operacao_changed(self) -> None:
        self._atualizar_metodos_disponiveis()
        self._atualizar_receitas()
        self._update_metodo_fields()

    def _update_metodo_fields(self) -> None:
        """Adapt the visible fields to the selected calculation method."""
        metodo = self._metodo_atual()
        rasgo_visivel = metodo == metodo_types.RASGO
        for widget in (self.rasgo_comp_label, self.rasgo_qt_comp_input,
                       self.rasgo_larg_label, self.rasgo_qt_larg_input):
            widget.setVisible(rasgo_visivel)
        if metodo == metodo_types.FURACAO:
            self.quantidade_base_label.setText("N.º de furos por unidade")
        elif metodo == metodo_types.REVESTIMENTO:
            self.quantidade_base_label.setText("N.º de faces (1 ou 2)")
        else:
            self.quantidade_base_label.setText("Quantidade base")
        tempos_visiveis = metodo in (
            None,
            metodo_types.TEMPO,
            metodo_types.POCKET,
        )
        for widget in (
            self.tempo_setup_input,
            self.tempo_por_unidade_input,
            self.unidade_tempo_input,
        ):
            widget.setVisible(True)  # visibility keeps the layout stable
            widget.setEnabled(tempos_visiveis)
        if rasgo_visivel:
            self._select_regra(RASGO_CNC)
            self._regra_rasgo_automatica = True
        elif (
            self._regra_rasgo_automatica
            and self.regra_calculo_input.currentData() == RASGO_CNC
        ):
            # Undo only the rule THIS dialog forced for the groove method; a
            # RASGO_CNC rule stored deliberately elsewhere is left untouched.
            self._select_regra(FIXA)
            self._regra_rasgo_automatica = False
        self._atualizar_guia()

    def _atualizar_receitas(self) -> None:
        """Rebuild the recipes combo, filtered by the machine capabilities."""
        operacao = self._operacao_selecionada()
        metodos = self._metodos_da_operacao(operacao)
        permite_pocket = bool(getattr(operacao, "maquina_permite_pocket", False))
        self.receita_input.blockSignals(True)
        self.receita_input.clear()
        self.receita_input.addItem("— escolher receita —", None)
        for receita in get_receitas_operacao():
            metodo_receita = receita.valores.get(CAMPO_METODO_CALCULO)
            if metodo_receita is not None:
                if not metodos or metodo_receita not in metodos:
                    continue
                if receita.key == "POCKET_CNC_TEMPO" and not permite_pocket:
                    continue
            elif metodos:
                # Method-less (manual/lote) recipes only make sense outside CNC.
                continue
            self.receita_input.addItem(receita.label, receita.key)
            self.receita_input.setItemData(
                self.receita_input.count() - 1,
                receita.descricao,
                Qt.ItemDataRole.ToolTipRole,
            )
        self.receita_input.blockSignals(False)

    def _acao_desativar(self) -> bool:
        return self._mostrar_acao and self.acao_input.currentData() == "DESATIVAR"

    def _aplicar_receita_selecionada(self) -> None:
        """Fill the form from the chosen 'Configurar como…' preset."""
        key = self.receita_input.currentData()
        if key is None:
            return
        receita = next(
            (r for r in get_receitas_operacao() if r.key == key), None
        )
        # Reset to the placeholder so the same recipe can be re-applied later.
        self.receita_input.blockSignals(True)
        self.receita_input.setCurrentIndex(0)
        self.receita_input.blockSignals(False)
        if receita is None:
            return

        if receita.operacao_codigo is not None:
            indice = next(
                (
                    i
                    for i in range(self.operacao_input.count())
                    if getattr(
                        self._operacoes_por_id.get(self.operacao_input.itemData(i)),
                        "codigo",
                        "",
                    )
                    == receita.operacao_codigo
                ),
                None,
            )
            if indice is None:
                self.set_error(
                    f"A receita «{receita.label}» precisa da operação "
                    f"{receita.operacao_codigo}, que não está disponível."
                )
                return
            self.operacao_input.setCurrentIndex(indice)

        self._preencher_valores(receita.valores)

        self.error_label.clear()
        foco = self._campos_texto_valores().get(receita.foco) or {
            CAMPO_RASGO_QT_COMP: self.rasgo_qt_comp_input,
            CAMPO_RASGO_QT_LARG: self.rasgo_qt_larg_input,
        }.get(receita.foco)
        if foco is not None:
            foco.setFocus()
            if isinstance(foco, QLineEdit):
                foco.selectAll()

    def _campos_texto_valores(self) -> dict:
        """Map recipe/suggestion text-field keys to the dialog widgets."""
        return {
            CAMPO_QUANTIDADE_BASE: self.quantidade_base_input,
            CAMPO_TEMPO_SETUP: self.tempo_setup_input,
            CAMPO_TEMPO_POR_UNIDADE: self.tempo_por_unidade_input,
        }

    def _preencher_valores(self, valores: dict) -> None:
        """Fill the form fields present in a recipe/suggestion values dict."""
        if CAMPO_METODO_CALCULO in valores:
            self._select_metodo(valores[CAMPO_METODO_CALCULO])
        if CAMPO_REGRA_CALCULO in valores:
            self._select_regra(valores[CAMPO_REGRA_CALCULO])
        if CAMPO_UNIDADE_TEMPO in valores:
            indice_unidade = self.unidade_tempo_input.findData(
                valores[CAMPO_UNIDADE_TEMPO]
            )
            if indice_unidade >= 0:
                self.unidade_tempo_input.setCurrentIndex(indice_unidade)
        for campo, widget in self._campos_texto_valores().items():
            if campo in valores:
                widget.setText(str(valores[campo]))
        if CAMPO_RASGO_QT_COMP in valores:
            self.rasgo_qt_comp_input.setValue(int(valores[CAMPO_RASGO_QT_COMP]))
        if CAMPO_RASGO_QT_LARG in valores:
            self.rasgo_qt_larg_input.setValue(int(valores[CAMPO_RASGO_QT_LARG]))

    def _atualizar_sugestoes(self) -> None:
        """Rebuild the copy suggestions for the currently selected operation."""
        if self._configuracoes_existentes is None:
            return
        self._sugestoes_atual = construir_sugestoes_operacao(
            self._configuracoes_existentes, self.operacao_input.currentData()
        )
        combo = self.sugestao_input
        combo.blockSignals(True)
        combo.clear()
        if self._sugestoes_atual:
            combo.addItem("— escolher configuração a copiar —", None)
            for indice, sugestao in enumerate(self._sugestoes_atual):
                combo.addItem(sugestao.label, indice)
                combo.setItemData(
                    combo.count() - 1,
                    sugestao.detalhe,
                    Qt.ItemDataRole.ToolTipRole,
                )
        else:
            combo.addItem("— sem configurações desta operação para copiar —", None)
        combo.blockSignals(False)
        combo.setEnabled(bool(self._sugestoes_atual) and not self._acao_desativar())

    def _aplicar_sugestao_selecionada(self) -> None:
        """Copy the chosen existing configuration into the form."""
        indice = self.sugestao_input.currentData()
        # Reset to the placeholder so the same suggestion can be re-applied.
        self.sugestao_input.blockSignals(True)
        self.sugestao_input.setCurrentIndex(0)
        self.sugestao_input.blockSignals(False)
        if indice is None or indice >= len(self._sugestoes_atual):
            return

        self._preencher_valores(self._sugestoes_atual[indice].valores)
        self.error_label.clear()
        if self.quantidade_base_input.isEnabled():
            self.quantidade_base_input.setFocus()
            self.quantidade_base_input.selectAll()

    def _widgets_guia(self) -> dict:
        """Map the guide's field keys to the dialog widgets."""
        return {
            CAMPO_QUANTIDADE_BASE: self.quantidade_base_input,
            CAMPO_TEMPO_SETUP: self.tempo_setup_input,
            CAMPO_TEMPO_POR_UNIDADE: self.tempo_por_unidade_input,
            CAMPO_UNIDADE_TEMPO: self.unidade_tempo_input,
        }

    def _atualizar_guia(self) -> None:
        """Refresh the always-visible formula panel and the dynamic fields."""
        if self._acao_desativar():
            self.guia_label.setText(
                "<b>Variante: desativar operação</b><br>"
                "Esta variante remove a operação base do mesmo tipo — os "
                "restantes campos não se aplicam."
            )
            return

        operacao = self._operacao_selecionada()
        guia = construir_guia_operacao(
            tipo_operacao=getattr(operacao, "tipo_operacao", None),
            codigo=getattr(operacao, "codigo", None),
            regra_calculo=self.regra_calculo_input.currentData(),
            unidade_tempo=self.unidade_tempo_input.currentData(),
            quantidade_base=self._parse_decimal_input_tolerante(
                self.quantidade_base_input
            ),
            tempo_setup_minutos=self._parse_decimal_input_tolerante(
                self.tempo_setup_input
            ),
            tempo_por_unidade_minutos=self._parse_decimal_input_tolerante(
                self.tempo_por_unidade_input
            ),
            rasgo_qt_comp=self.rasgo_qt_comp_input.value(),
            rasgo_qt_larg=self.rasgo_qt_larg_input.value(),
            custo_hora=self._custo_hora_da_operacao(operacao),
            preco_rasgo_ml=getattr(operacao, "maquina_preco_rasgo_ml_std", None),
            natureza_peca=self._natureza_peca,
            metodo_calculo=self._metodo_atual(),
            preco_furo=getattr(operacao, "maquina_preco_furo_std", None),
            preco_m2_face=getattr(operacao, "maquina_preco_m2_face_std", None),
        )

        linhas = "<br>".join(escape(linha) for linha in guia.linhas)
        self.guia_label.setText(f"<b>{escape(guia.titulo)}</b><br>{linhas}")

        for campo, widget in self._widgets_guia().items():
            motivo = guia.campos_inativos.get(campo)
            widget.setEnabled(motivo is None)
            tooltip = self._tooltips_base_guia[campo]
            if motivo is not None:
                tooltip = f"{tooltip}\n\n{motivo}"
            widget.setToolTip(tooltip)

    def _abrir_simulador(self) -> None:
        """Open the simulator matching how the operation is actually costed."""
        operacao = self._operacao_selecionada()
        metodo = self._metodo_atual()
        if metodo is not None:
            # New CNC model: open the full simulator prefilled with this
            # machine, method and the fields already typed in the form.
            self._abrir_simulador_cnc(operacao, metodo)
            return
        bucket = classificar_operacao(
            getattr(operacao, "tipo_operacao", None), getattr(operacao, "codigo", None)
        )
        natureza = (self._natureza_peca or "").strip().upper() or None
        if bucket in ("corte", "orlagem", "cnc") and natureza != FERRAGEM:
            SimuladorTarifaPainelDialog(
                bucket=bucket,
                operacao=operacao,
                escaloes=self._escaloes_da_operacao(operacao) if bucket == "cnc" else [],
                parent=self,
            ).exec()
            return
        dialog = SimuladorOperacaoDialog(
            unidade_tempo=self.unidade_tempo_input.currentData(),
            quantidade_base=self._parse_decimal_input_tolerante(
                self.quantidade_base_input
            ),
            tempo_setup_minutos=self._parse_decimal_input_tolerante(
                self.tempo_setup_input
            ),
            tempo_por_unidade_minutos=self._parse_decimal_input_tolerante(
                self.tempo_por_unidade_input
            ),
            custo_hora=self._custo_hora_da_operacao(operacao),
            operacao_codigo=getattr(operacao, "codigo", None),
            operacao_nome=getattr(operacao, "nome", None),
            parent=self,
        )
        dialog.exec()

    def _abrir_simulador_cnc(self, operacao, metodo: str) -> None:
        """Open the CNC simulator dialog prefilled from this form."""
        from app.ui.widgets.simulador_cnc_widget import SimuladorCncDialog

        dialog = SimuladorCncDialog(parent=self)
        maquina_codigo = getattr(operacao, "maquina_codigo", None)
        if maquina_codigo:
            params: dict = {}
            quantidade = self._parse_decimal_input_tolerante(
                self.quantidade_base_input
            )
            if metodo == metodo_types.FURACAO:
                params = {"furos": int(quantidade or 3)}
            elif metodo == metodo_types.RASGO:
                params = {
                    "n_comp": self.rasgo_qt_comp_input.value(),
                    "n_larg": self.rasgo_qt_larg_input.value(),
                }
            elif metodo in (metodo_types.TEMPO, metodo_types.POCKET):
                params = {
                    "setup": self._parse_decimal_input_tolerante(
                        self.tempo_setup_input
                    )
                    or Decimal("0"),
                    "min_unidade": self._parse_decimal_input_tolerante(
                        self.tempo_por_unidade_input
                    )
                    or Decimal("0"),
                    "unidades": int(quantidade or 1),
                }
            elif metodo == metodo_types.REVESTIMENTO:
                params = {"faces": int(quantidade or 1)}
            dialog.widget.limpar_operacoes()
            dialog.widget.adicionar_operacao(maquina_codigo, metodo, **params)
        dialog.exec()

    def _operacao_selecionada(self):
        """Return the selected operation resumo, when available."""
        return self._operacoes_por_id.get(self.operacao_input.currentData())

    def _custo_hora_da_operacao(self, operacao) -> Decimal | None:
        """Best-effort hourly cost from operation or embedded machine info."""
        if operacao is None:
            return None
        custo = getattr(operacao, "custo_hora", None)
        if custo is not None:
            return custo
        maquina = getattr(operacao, "maquina", None)
        if maquina is not None:
            custo = getattr(maquina, "custo_hora", None)
            if custo is not None:
                return custo
        custo = getattr(operacao, "maquina_custo_hora", None)
        if custo is not None:
            return custo
        # Real machine STD tariff embedded in the read model (phase G2).
        return getattr(operacao, "maquina_custo_hora_std", None)

    def _escaloes_da_operacao(self, operacao) -> list:
        """Load the machine's active area tiers for the CNC simulator."""
        maquina_id = getattr(operacao, "maquina_id", None)
        if maquina_id is None:
            return []
        try:
            from app.db.session import SessionLocal
            from app.repositories.def_maquina_escalao_area_repository import (
                DefMaquinaEscalaoAreaRepository,
            )

            with SessionLocal() as session:
                return DefMaquinaEscalaoAreaRepository(session).list_active_by_maquina(
                    maquina_id
                )
        except Exception:  # noqa: BLE001 - simulator must open even without DB
            return []

    def _parse_decimal_input(self, widget: QLineEdit) -> Decimal | None:
        text = widget.text().strip()
        if not text:
            return None

        normalized = text.replace(" ", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as error:
            raise ValueError("valor numerico invalido") from error

    def _parse_decimal_input_tolerante(self, widget: QLineEdit) -> Decimal | None:
        """Parse while editing; invalid partial input is treated as empty."""
        try:
            return self._parse_decimal_input(widget)
        except ValueError:
            return None

    def _format_decimal(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value.normalize(), "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None


class SimuladorRasgoCncDialog(QDialog):
    """Live geometric-length and price simulator for a CNC groove."""

    def __init__(self, *, rasgo_qt_comp: int, rasgo_qt_larg: int,
                 preco_ml: Decimal | None, maquina_codigo: str | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simular rasgo CNC")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.rasgo_qt_comp = rasgo_qt_comp
        self.rasgo_qt_larg = rasgo_qt_larg
        self.comp_input = QLineEdit()
        self.larg_input = QLineEdit()
        self.qt_input = QLineEdit("1")
        self.preco_input = QLineEdit(self._format_decimal(preco_ml))
        self.resultado = QLabel()
        self.resultado.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Máquina", QLabel(maquina_codigo or "—"))
        form.addRow("Construção", QLabel(f"{rasgo_qt_comp} × COMP + {rasgo_qt_larg} × LARG"))
        form.addRow("COMP real (mm)", self.comp_input)
        form.addRow("LARG real (mm)", self.larg_input)
        form.addRow("QT peças", self.qt_input)
        form.addRow("Preço rasgo (€/ML)", self.preco_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _button: self.accept())
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("O comprimento é geométrico; a ida e volta da fresa não duplica os ML."))
        layout.addWidget(self.resultado)
        layout.addWidget(buttons)
        for widget in (self.comp_input, self.larg_input, self.qt_input, self.preco_input):
            widget.textChanged.connect(self._recalcular)
        self._recalcular()

    def _recalcular(self) -> None:
        comp = self._parse(self.comp_input.text())
        larg = self._parse(self.larg_input.text())
        qt = self._parse(self.qt_input.text()) or Decimal("1")
        preco = self._parse(self.preco_input.text())
        ml = calcular_comprimento_rasgo_ml(
            comp, larg, self.rasgo_qt_comp, self.rasgo_qt_larg
        )
        custo, _ = calcular_custo_rasgo_cnc(
            comp, larg, qt, self.rasgo_qt_comp, self.rasgo_qt_larg, preco
        )
        if ml is None:
            self.resultado.setText("Preencha as medidas necessárias para simular.")
            return
        self.resultado.setText(
            f"Rasgo por peça: {format_quantity(ml)} ML\n"
            f"Rasgo total: {format_quantity(ml * qt)} ML\n"
            f"Custo: {format_currency(custo) if custo is not None else 'sem tarifa'}"
        )

    @staticmethod
    def _parse(text: str) -> Decimal | None:
        try:
            return Decimal(text.strip().replace(",", ".")) if text.strip() else None
        except InvalidOperation:
            return None

    @staticmethod
    def _format_decimal(value: Decimal | None) -> str:
        return "" if value is None else format(value.normalize(), "f")


class SimuladorTarifaPainelDialog(QDialog):
    """Live € decomposition of a panel tariff operation (corte/orlagem/CNC).

    Uses the REAL machine tariffs embedded in the operation read model and the
    same pure cost helpers as the costing engine, so the simulated value always
    matches the production cost of a panel line with these measures.
    """

    def __init__(self, *, bucket: str, operacao, escaloes: list, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Simular custo por tarifa da máquina")
        self.setModal(True)
        self.setMinimumWidth(560)

        self._bucket = bucket
        self._escaloes = list(escaloes or [])
        self._preco_ml = getattr(operacao, "maquina_preco_ml_std", None)
        self._preco_lado_curto = getattr(operacao, "maquina_preco_lado_curto_std", None)
        self._preco_lado_longo = getattr(operacao, "maquina_preco_lado_longo_std", None)
        self._limite_lado_mm = getattr(operacao, "maquina_limite_lado_mm", None)
        self._custo_setup_peca = getattr(operacao, "maquina_custo_setup_peca_std", None)

        operacao_texto = " - ".join(
            parte
            for parte in (
                getattr(operacao, "codigo", None),
                getattr(operacao, "nome", None),
            )
            if parte
        )
        titulo = QLabel(f"Operação: {operacao_texto or '—'}")
        maquina = QLabel(self._texto_tarifas(getattr(operacao, "maquina_codigo", None)))
        maquina.setWordWrap(True)
        maquina.setStyleSheet("color: #666; font-size: 11px;")

        self.comp_input = QLineEdit("600")
        self.comp_input.setToolTip("Comprimento real da peça em milímetros.")
        self.larg_input = QLineEdit("400")
        self.larg_input.setToolTip("Largura real da peça em milímetros.")
        self.qt_input = QLineEdit("1")
        self.qt_input.setToolTip("Quantidade total de peças da linha.")
        self.orlas_input = QLineEdit("1111")
        self.orlas_input.setToolTip(
            "Código de orlas C1 C2 L1 L2 (0 = sem orla, 1 = fina, 2 = grossa). "
            "Só os lados com 1/2 são orlados."
        )

        self.resultado = QLabel("")
        self.resultado.setWordWrap(True)

        form = QFormLayout()
        form.addRow("COMP real (mm)", self.comp_input)
        form.addRow("LARG real (mm)", self.larg_input)
        form.addRow("QT peças", self.qt_input)
        if bucket == "orlagem":
            form.addRow("Código orlas", self.orlas_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Fechar")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _button: self.accept())

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(maquina)
        layout.addLayout(form)
        layout.addWidget(self.resultado)
        layout.addWidget(buttons)

        for widget in (self.comp_input, self.larg_input, self.qt_input, self.orlas_input):
            widget.textChanged.connect(self._recalcular)
        self._recalcular()

    def _texto_tarifas(self, maquina_codigo: str | None) -> str:
        nome = maquina_codigo or "—"
        if self._bucket == "corte":
            return (
                f"Máquina {nome} — €/ML: {self._fmt_tarifa(self._preco_ml)} • "
                f"setup/peça: {self._fmt_tarifa(self._custo_setup_peca)} €"
            )
        if self._bucket == "orlagem":
            limite = self._limite_lado_mm
            return (
                f"Máquina {nome} — lado curto: {self._fmt_tarifa(self._preco_lado_curto)} € • "
                f"lado longo: {self._fmt_tarifa(self._preco_lado_longo)} € • "
                f"limite: {format_quantity(limite) if limite is not None else '1500'} mm • "
                f"setup/peça: {self._fmt_tarifa(self._custo_setup_peca)} €"
            )
        return (
            f"Máquina {nome} — {len(self._escaloes)} escalão(ões) de área ativos"
        )

    def _recalcular(self) -> None:
        comp = self._parse(self.comp_input.text())
        larg = self._parse(self.larg_input.text())
        qt = self._parse(self.qt_input.text()) or Decimal("1")
        if comp is None or larg is None:
            self.resultado.setText("Preencha COMP e LARG para simular.")
            return

        if self._bucket == "corte":
            self.resultado.setText(self._simular_corte(comp, larg, qt))
        elif self._bucket == "orlagem":
            self.resultado.setText(self._simular_orlagem(comp, larg, qt))
        else:
            self.resultado.setText(self._simular_cnc(comp, larg, qt))

    def _simular_corte(self, comp: Decimal, larg: Decimal, qt: Decimal) -> str:
        perimetro = (comp + larg) * Decimal("2") / Decimal("1000")
        custo, _motivo = calcular_custo_corte(
            perimetro, qt, self._preco_ml, self._custo_setup_peca
        )
        texto = (
            f"Perímetro = 2 × ({format_quantity(comp)} + {format_quantity(larg)}) "
            f"/ 1000 = {format_quantity(perimetro)} ML por peça"
        )
        if custo is None:
            return f"{texto}\nSem custo: tarifa €/ML em falta na máquina."
        setup = normalizar_numero(self._custo_setup_peca)
        detalhe = (
            f"{format_quantity(perimetro)} ML × QT {format_quantity(qt)} × "
            f"{format_quantity(self._preco_ml)} €/ML"
        )
        if setup is not None:
            detalhe += f" + QT × {format_quantity(setup)} € setup"
        return f"{texto}\nCusto = {detalhe} = {format_currency(custo)}"

    def _simular_orlagem(self, comp: Decimal, larg: Decimal, qt: Decimal) -> str:
        codigo = self.orlas_input.text().strip()
        custo, motivo = calcular_custo_orlagem_lados(
            codigo,
            comp,
            larg,
            qt,
            self._preco_lado_curto,
            self._preco_lado_longo,
            self._limite_lado_mm,
            self._custo_setup_peca,
        )
        linhas = [self._detalhe_lados_orlados(codigo, comp, larg)]
        if custo is None:
            if motivo == "SEM_TARIFA":
                linhas.append("Sem custo: tarifas por lado orlado em falta na máquina.")
            else:
                linhas.append("Sem custo: dados em falta.")
            return "\n".join(linhas)
        if custo == 0:
            return "Sem lados orlados (código 0000 ou inválido) → custo 0,00 €."
        linhas.append(
            f"Custo = soma dos lados × QT {format_quantity(qt)}"
            + (
                f" + QT × {format_quantity(self._custo_setup_peca)} € setup"
                if normalizar_numero(self._custo_setup_peca) is not None
                else ""
            )
            + f" = {format_currency(custo)}"
        )
        return "\n".join(linhas)

    def _detalhe_lados_orlados(self, codigo: str, comp: Decimal, larg: Decimal) -> str:
        from app.domain.orlas import digitos_orla

        digitos = digitos_orla(codigo)
        if digitos is None:
            return "Código de orlas inválido."
        limite = normalizar_numero(self._limite_lado_mm) or Decimal("1500")
        nomes = ("C1", "C2", "L1", "L2")
        medidas = (comp, comp, larg, larg)
        partes = []
        for nome, digito, medida in zip(nomes, digitos, medidas, strict=True):
            if digito == 0:
                continue
            lado_curto = medida <= limite
            tarifa = self._preco_lado_curto if lado_curto else self._preco_lado_longo
            partes.append(
                f"{nome} ({format_quantity(medida)} mm "
                f"{'≤' if lado_curto else '>'} {format_quantity(limite)}) → "
                f"lado {'curto' if lado_curto else 'longo'} "
                f"{format_quantity(tarifa) if tarifa is not None else '—'} €"
            )
        if not partes:
            return "Sem lados orlados no código indicado."
        return "Lados orlados: " + "; ".join(partes)

    def _simular_cnc(self, comp: Decimal, larg: Decimal, qt: Decimal) -> str:
        area = comp * larg / Decimal("1000000")
        custo, motivo = calcular_custo_cnc(area, qt, self._escaloes)
        texto = (
            f"Área = {format_quantity(comp)} × {format_quantity(larg)} / 1 000 000 "
            f"= {format_quantity(area)} m² por peça"
        )
        if custo is None:
            return (
                f"{texto}\nSem custo: escalões de área em falta (ou nenhum escalão "
                "cobre esta área) na máquina."
            )
        escalao = selecionar_escalao_area(self._escaloes, area)
        limite = getattr(escalao, "area_max_m2", None)
        preco = getattr(escalao, "preco_peca_std", None)
        texto += (
            f"\nEscalão nível {getattr(escalao, 'nivel', '—')} "
            f"({'≤ ' + format_quantity(limite) + ' m²' if limite is not None else 'sem limite'}) "
            f"→ {format_quantity(preco)} € por peça"
        )
        return (
            f"{texto}\nCusto = {format_quantity(preco)} € × QT {format_quantity(qt)} "
            f"= {format_currency(custo)}"
        )

    @staticmethod
    def _fmt_tarifa(valor: Decimal | None) -> str:
        return format_quantity(valor) if valor is not None else "—"

    @staticmethod
    def _parse(text: str) -> Decimal | None:
        try:
            return Decimal(text.strip().replace(",", ".")) if text.strip() else None
        except InvalidOperation:
            return None


class SimuladorOperacaoDialog(QDialog):
    """Live simulator for an operation's time and hourly cost."""

    CENARIOS_QT = (Decimal("1"), Decimal("2"), Decimal("5"), Decimal("10"))
    COR_QT_ATUAL = QColor("#f1f5f9")

    def __init__(
        self,
        *,
        unidade_tempo: str | None,
        quantidade_base: Decimal | None,
        tempo_setup_minutos: Decimal | None,
        tempo_por_unidade_minutos: Decimal | None,
        custo_hora: Decimal | None = None,
        operacao_codigo: str | None = None,
        operacao_nome: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Simular cálculo da operação")
        self.setModal(True)
        self.setMinimumWidth(620)

        operacao_texto = " - ".join(
            parte for parte in (operacao_codigo, operacao_nome) if parte
        )
        self.operacao_label = QLabel(
            f"Operação: {operacao_texto}" if operacao_texto else "Operação"
        )

        self.unidade_tempo_input = QComboBox()
        for opcao in UNIDADE_TEMPO_OPCOES:
            self.unidade_tempo_input.addItem(UNIDADE_TEMPO_LABELS[opcao], opcao or None)

        self.quantidade_base_input = QLineEdit()
        self.tempo_setup_input = QLineEdit()
        self.tempo_por_unidade_input = QLineEdit()
        self.custo_hora_input = QLineEdit()
        self.qt_total_input = QLineEdit("1")
        self.area_m2_input = QLineEdit()
        self.ml_input = QLineEdit()
        self.tempo_setup_segundos_label = self._criar_nota_contexto()
        self.tempo_por_unidade_segundos_label = self._criar_nota_contexto()

        self.quantidade_base_input.setText(self._format_decimal(quantidade_base))
        self.tempo_setup_input.setText(self._format_decimal(tempo_setup_minutos))
        self.tempo_por_unidade_input.setText(
            self._format_decimal(tempo_por_unidade_minutos)
        )
        self.custo_hora_input.setText(self._format_decimal(custo_hora))
        indice_unidade = self.unidade_tempo_input.findData(unidade_tempo)
        if indice_unidade >= 0:
            self.unidade_tempo_input.setCurrentIndex(indice_unidade)

        ajuda = QLabel(
            "Tempos em minutos (ex.: 0,05 = 3 seg). Custo/hora em €. "
            "Setup soma 1× por linha; Tempo por unidade multiplica pela QT."
        )
        ajuda.setWordWrap(True)
        ajuda.setStyleSheet("color: #666; font-size: 11px;")

        self.resultado_label = QLabel("")
        self.resultado_label.setWordWrap(True)

        self.cenarios_table = QTableWidget(len(self.CENARIOS_QT), 3)
        self.cenarios_table.setHorizontalHeaderLabels(
            ["QT", "Tempo total (min)", "Custo (€)"]
        )
        self.cenarios_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        form = QFormLayout()
        form.addRow("Unidade tempo", self.unidade_tempo_input)
        form.addRow("Quantidade base", self.quantidade_base_input)
        form.addRow("Tempo setup (min)", self.tempo_setup_input)
        form.addRow("", self.tempo_setup_segundos_label)
        form.addRow("Tempo por unidade (min)", self.tempo_por_unidade_input)
        form.addRow("", self.tempo_por_unidade_segundos_label)
        form.addRow("Custo/hora (€/h)", self.custo_hora_input)
        form.addRow("QT total", self.qt_total_input)
        form.addRow("Área m²", self.area_m2_input)
        form.addRow("ML", self.ml_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText("Fechar")
        self.button_box.clicked.connect(lambda _button: self.accept())

        layout = QVBoxLayout()
        layout.addWidget(self.operacao_label)
        layout.addLayout(form)
        layout.addWidget(ajuda)
        layout.addWidget(self.resultado_label)
        layout.addWidget(self.cenarios_table)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._ligar_recalculo()
        self._atualizar_estado_contexto()
        self._recalcular()

    def _ligar_recalculo(self) -> None:
        """Connect input changes to live recalculation."""
        for widget in (
            self.quantidade_base_input,
            self.tempo_setup_input,
            self.tempo_por_unidade_input,
            self.custo_hora_input,
            self.qt_total_input,
            self.area_m2_input,
            self.ml_input,
        ):
            widget.textChanged.connect(self._recalcular)
        self.unidade_tempo_input.currentIndexChanged.connect(
            lambda _index: self._on_unidade_changed()
        )

    def _on_unidade_changed(self) -> None:
        self._atualizar_estado_contexto()
        self._recalcular()

    def _atualizar_estado_contexto(self) -> None:
        unidade = (self.unidade_tempo_input.currentData() or "").upper()
        self.area_m2_input.setEnabled(unidade == "M2")
        self.ml_input.setEnabled(unidade == "ML")

    def _criar_nota_contexto(self) -> QLabel:
        label = QLabel("")
        label.setStyleSheet("color: #666; font-size: 11px;")
        label.setWordWrap(True)
        return label

    def _atualizar_notas_segundos(self) -> None:
        self._atualizar_nota_segundos(
            self.tempo_setup_segundos_label,
            self._parse_decimal_text(self.tempo_setup_input.text()),
        )
        self._atualizar_nota_segundos(
            self.tempo_por_unidade_segundos_label,
            self._parse_decimal_text(self.tempo_por_unidade_input.text()),
        )

    def _atualizar_nota_segundos(self, label: QLabel, minutos: Decimal | None) -> None:
        if minutos is None:
            label.clear()
            label.setVisible(False)
            return
        segundos = minutos * Decimal("60")
        label.setText(f"{format_quantity(minutos)} min = {format_quantity(segundos)} seg")
        label.setVisible(True)

    def _cenarios_qt(self, qt_atual: Decimal | None) -> list[Decimal]:
        valores = set(self.CENARIOS_QT)
        if qt_atual is not None:
            valores.add(qt_atual)
        return sorted(valores)

    def _item_cenario(self, texto: str, destaque: bool) -> QTableWidgetItem:
        item = QTableWidgetItem(texto)
        if destaque:
            fonte = QFont(item.font())
            fonte.setBold(True)
            item.setFont(fonte)
            item.setBackground(self.COR_QT_ATUAL)
        return item

    def _recalcular(self) -> None:
        """Refresh the live result and all scenario rows."""
        self._atualizar_notas_segundos()
        parametros = self._parametros()
        resultado = calcular_simulacao_operacao(**parametros)
        self.resultado_label.setText(
            self._formatar_resultado(resultado, parametros["custo_hora"])
        )

        cenarios = self._cenarios_qt(parametros["qt_total"])
        self.cenarios_table.setRowCount(len(cenarios))
        for row, qt in enumerate(cenarios):
            resultado_linha = calcular_simulacao_operacao(
                **{**parametros, "qt_total": qt}
            )
            valores = (
                format_quantity(qt),
                (
                    format_quantity(resultado_linha.tempo_total_minutos)
                    if resultado_linha.tempo_total_minutos is not None
                    else "—"
                ),
                (
                    format_currency(resultado_linha.custo)
                    if resultado_linha.custo is not None
                    else "—"
                ),
            )
            destaque = qt == parametros["qt_total"]
            for col, valor in enumerate(valores):
                self.cenarios_table.setItem(
                    row, col, self._item_cenario(valor, destaque)
                )
        self.cenarios_table.resizeColumnsToContents()

    def _parametros(self) -> dict:
        unidade = self.unidade_tempo_input.currentData()
        return {
            "unidade_tempo": unidade,
            "quantidade_base": self._parse_decimal_text(
                self.quantidade_base_input.text()
            ),
            "tempo_setup_minutos": self._parse_decimal_text(
                self.tempo_setup_input.text()
            ),
            "tempo_por_unidade_minutos": self._parse_decimal_text(
                self.tempo_por_unidade_input.text()
            ),
            "area_m2": self._parse_decimal_text(self.area_m2_input.text())
            if unidade == "M2"
            else None,
            "ml": self._parse_decimal_text(self.ml_input.text())
            if unidade == "ML"
            else None,
            "qt_total": self._parse_decimal_text(self.qt_total_input.text())
            or Decimal("1"),
            "custo_hora": self._parse_decimal_text(self.custo_hora_input.text()),
        }

    def _formatar_resultado(
        self, resultado: SimulacaoOperacaoResultado, custo_hora: Decimal | None
    ) -> str:
        if resultado.tempo_total_minutos is None:
            return "Tempo total: sem tempos configurados."

        texto = (
            "tempo total = setup "
            f"{format_quantity(resultado.setup_minutos)} + variável "
            f"{format_quantity(resultado.variavel_minutos)} = "
            f"{format_quantity(resultado.tempo_total_minutos)} min"
        )
        if custo_hora is None:
            return f"{texto}\nsem custo/hora não há custo"

        if resultado.custo is None:
            return f"{texto}\nsem custo/hora não há custo"

        return (
            f"{texto}\n"
            f"custo = {format_quantity(resultado.tempo_total_minutos)} / 60 × "
            f"{format_currency(custo_hora)}/h = {format_currency(resultado.custo)}"
        )

    @staticmethod
    def _parse_decimal_text(text: str) -> Decimal | None:
        normalized = text.strip().replace(" ", "").replace(",", ".")
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    @staticmethod
    def _format_decimal(value: Decimal | None) -> str:
        if value is None:
            return ""
        return format(value.normalize(), "f")
