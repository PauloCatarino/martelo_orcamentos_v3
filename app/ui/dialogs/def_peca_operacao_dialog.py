"""Dialog for linking an operation to a piece definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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
from app.domain.regra_operacao_types import RASGO_CNC
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
    ) -> None:
        super().__init__(parent)

        self.ligacao = ligacao
        self.on_save = on_save
        self._is_edit = ligacao is not None
        self._mostrar_acao = mostrar_acao
        self._operacoes_por_id = {
            operacao.id: operacao for operacao in operacoes_disponiveis
        }

        self.setWindowTitle("Editar Operação da Peça" if self._is_edit else "Nova Operação da Peça")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.operacao_input = QComboBox()
        for operacao in operacoes_disponiveis:
            self.operacao_input.addItem(f"{operacao.codigo} - {operacao.nome}", operacao.id)

        self.ordem_input = QSpinBox()
        self.ordem_input.setRange(1, 9999)
        self.ordem_input.setValue(1)

        self.acao_input = QComboBox()
        for code, label in get_operacao_acao_options():
            self.acao_input.addItem(label, code)
        self.acao_input.setToolTip(
            "Adicionar mantém as operações base; Substituir troca a operação do "
            "mesmo tipo; Desativar remove a operação selecionada."
        )

        self.regra_calculo_input = QComboBox()
        for code, label in get_regra_operacao_options():
            self.regra_calculo_input.addItem(label, code)

        self.quantidade_base_input = QLineEdit()
        self.quantidade_base_input.setPlaceholderText("Ex.: 1.5")
        self.rasgo_qt_comp_input = QSpinBox()
        self.rasgo_qt_comp_input.setRange(0, 99)
        self.rasgo_qt_larg_input = QSpinBox()
        self.rasgo_qt_larg_input.setRange(0, 99)

        self.tempo_setup_input = QLineEdit()
        self.tempo_setup_input.setPlaceholderText("Ex.: 2 (minutos)")
        self.tempo_por_unidade_input = QLineEdit()
        self.tempo_por_unidade_input.setPlaceholderText("Ex.: 0.35 (min/unidade)")
        self.unidade_tempo_input = QComboBox()
        for opcao in UNIDADE_TEMPO_OPCOES:
            self.unidade_tempo_input.addItem(UNIDADE_TEMPO_LABELS[opcao], opcao or None)

        self.obrigatorio_input = QCheckBox()
        self.obrigatorio_input.setChecked(True)
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.observacoes_input = QLineEdit()

        self.error_label = QLabel("")
        self.error_label.setObjectName("defPecaOperacaoDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Operação", self.operacao_input)
        self.acao_label = QLabel("Ação da variante")
        form.addRow(self.acao_label, self.acao_input)
        self.acao_label.setVisible(mostrar_acao)
        self.acao_input.setVisible(mostrar_acao)
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Regra cálculo", self.regra_calculo_input)
        form.addRow("Quantidade base", self.quantidade_base_input)
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
        self.operacao_input.currentIndexChanged.connect(self._update_rasgo_fields)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if ligacao is not None:
            self._load_ligacao(ligacao)
        self._update_acao_fields()
        self._update_rasgo_fields()

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
        if getattr(operacao, "codigo", "") == "CNC_RASGO":
            if data.rasgo_qt_comp + data.rasgo_qt_larg <= 0:
                self.set_error("Defina pelo menos um comprimento ou uma largura de rasgo.")
                return
            if not getattr(operacao, "maquina_permite_rasgos", False):
                self.set_error("A máquina associada não permite fresagem de rasgos.")
                return
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _update_acao_fields(self) -> None:
        """Disable calculation inputs when the variant only removes an operation."""
        desativar = self._mostrar_acao and self.acao_input.currentData() == "DESATIVAR"
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

    def _update_rasgo_fields(self) -> None:
        visivel = getattr(self._operacao_selecionada(), "codigo", "") == "CNC_RASGO"
        for widget in (self.rasgo_comp_label, self.rasgo_qt_comp_input,
                       self.rasgo_larg_label, self.rasgo_qt_larg_input):
            widget.setVisible(visivel)
        if visivel:
            self._select_regra(RASGO_CNC)

    def _abrir_simulador(self) -> None:
        """Open the operation simulator using the current form values."""
        operacao = self._operacao_selecionada()
        if getattr(operacao, "codigo", "") == "CNC_RASGO":
            SimuladorRasgoCncDialog(
                rasgo_qt_comp=self.rasgo_qt_comp_input.value(),
                rasgo_qt_larg=self.rasgo_qt_larg_input.value(),
                preco_ml=getattr(operacao, "maquina_preco_rasgo_ml_std", None),
                maquina_codigo=getattr(operacao, "maquina_codigo", None),
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
        return getattr(operacao, "maquina_custo_hora", None)

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
