"""Dialog for creating and editing an operation."""

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
    QTextEdit,
    QVBoxLayout,
)

from app.domain.operacao_types import get_operacao_type_options, normalize_operacao_type
from app.repositories.def_maquina_repository import DefMaquinaResumo
from app.repositories.def_operacao_repository import DefOperacaoResumo

UNIDADE_OPCOES = ("PECA", "ML", "M2", "HORA", "MINUTO", "LOTE", "SETUP", "FIXO", "OUTRO")


@dataclass(frozen=True)
class OperacaoDialogData:
    """Data collected by the operation dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo_operacao: str | None
    unidade_calculo: str | None
    maquina_id: int | None
    tempo_base: Decimal | None
    tempo_setup: Decimal | None
    custo_hora: Decimal | None
    custo_minimo: Decimal | None
    observacoes: str | None
    ativo: bool


class OperacaoDialog(QDialog):
    """Modal dialog for creating or editing an operation."""

    def __init__(
        self,
        maquinas_disponiveis: list[DefMaquinaResumo],
        operacao: DefOperacaoResumo | None = None,
        parent=None,
        on_save: Callable[[OperacaoDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.operacao = operacao
        self.on_save = on_save
        self._is_edit = operacao is not None

        self.setWindowTitle("Editar Operação" if self._is_edit else "Nova Operação")
        self.setModal(True)
        self.setMinimumWidth(480)

        self.codigo_input = QLineEdit()
        self.nome_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(60)

        self.tipo_operacao_input = QComboBox()
        for code, label in get_operacao_type_options():
            self.tipo_operacao_input.addItem(label, code)

        self.unidade_calculo_input = QComboBox()
        for opcao in UNIDADE_OPCOES:
            self.unidade_calculo_input.addItem(opcao, opcao)

        self.maquina_input = QComboBox()
        self.maquina_input.addItem("(sem máquina)", None)
        for maquina in maquinas_disponiveis:
            self.maquina_input.addItem(f"{maquina.codigo} - {maquina.nome}", maquina.id)

        self.tempo_base_input = QLineEdit()
        self.tempo_setup_input = QLineEdit()
        self.custo_hora_input = QLineEdit()
        self.custo_minimo_input = QLineEdit()
        self.observacoes_input = QLineEdit()

        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("operacaoDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Tipo operação", self.tipo_operacao_input)
        form.addRow("Unidade cálculo", self.unidade_calculo_input)
        form.addRow("Máquina associada", self.maquina_input)
        self.tempo_base_label = QLabel("Tempo base")
        form.addRow(self.tempo_base_label, self.tempo_base_input)
        self.tempo_setup_label = QLabel("Tempo setup")
        form.addRow(self.tempo_setup_label, self.tempo_setup_input)
        self.custo_hora_label = QLabel("Custo/hora")
        form.addRow(self.custo_hora_label, self.custo_hora_input)
        self.custo_minimo_label = QLabel("Custo mínimo")
        form.addRow(self.custo_minimo_label, self.custo_minimo_input)
        self.nota_cnc_label = QLabel(
            "Operação CNC/Revestimento: os custos vêm todos da MÁQUINA "
            "(capacidades, tarifas e escalões) e o método de cálculo "
            "escolhe-se ao associar a operação à peça — por isso os campos "
            "de tempo/custo desta ficha não se aplicam."
        )
        self.nota_cnc_label.setWordWrap(True)
        self.nota_cnc_label.setStyleSheet("color: #666666; font-size: 11px;")
        form.addRow("", self.nota_cnc_label)
        form.addRow("Observações", self.observacoes_input)
        form.addRow("Ativo", self.ativo_input)
        self.tipo_operacao_input.currentIndexChanged.connect(
            self._update_campos_tipo
        )

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if operacao is not None:
            self._load_operacao(operacao)
        self._update_campos_tipo()

    def _update_campos_tipo(self) -> None:
        """Hide the per-operation time/cost fields for CNC/coating types."""
        tipo = (self.tipo_operacao_input.currentData() or "").strip().upper()
        maquina_manda = tipo in ("CNC", "REVESTIMENTO")
        for widget in (
            self.tempo_base_label,
            self.tempo_base_input,
            self.tempo_setup_label,
            self.tempo_setup_input,
            self.custo_hora_label,
            self.custo_hora_input,
            self.custo_minimo_label,
            self.custo_minimo_input,
        ):
            widget.setVisible(not maquina_manda)
        self.nota_cnc_label.setVisible(maquina_manda)

    def _load_operacao(self, operacao: DefOperacaoResumo) -> None:
        """Populate the form with an existing operation and lock the code."""
        self.codigo_input.setText(operacao.codigo)
        self.codigo_input.setReadOnly(True)
        self.nome_input.setText(operacao.nome)
        self.descricao_input.setPlainText(operacao.descricao or "")
        self._select_data(
            self.tipo_operacao_input, normalize_operacao_type(operacao.tipo_operacao)
        )
        self._select_unidade(operacao.unidade_calculo)
        self._select_data(self.maquina_input, operacao.maquina_id)
        self.tempo_base_input.setText(self._format_decimal(operacao.tempo_base))
        self.tempo_setup_input.setText(self._format_decimal(operacao.tempo_setup))
        self.custo_hora_input.setText(self._format_decimal(operacao.custo_hora))
        self.custo_minimo_input.setText(self._format_decimal(operacao.custo_minimo))
        self.observacoes_input.setText(operacao.observacoes or "")
        self.ativo_input.setChecked(operacao.ativo)

    def _select_data(self, combo: QComboBox, value: object) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _select_unidade(self, unidade: str | None) -> None:
        if not unidade:
            return

        index = self.unidade_calculo_input.findData(unidade)
        if index < 0:
            self.unidade_calculo_input.addItem(unidade, unidade)
            index = self.unidade_calculo_input.findData(unidade)
        self.unidade_calculo_input.setCurrentIndex(index)

    def get_data(self) -> OperacaoDialogData:
        """Return normalized dialog data (raises ValueError on invalid numbers)."""
        return OperacaoDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo_operacao=self.tipo_operacao_input.currentData(),
            unidade_calculo=self.unidade_calculo_input.currentData(),
            maquina_id=self.maquina_input.currentData(),
            tempo_base=self._parse_decimal(self.tempo_base_input, "Tempo base"),
            tempo_setup=self._parse_decimal(self.tempo_setup_input, "Tempo setup"),
            custo_hora=self._parse_decimal(self.custo_hora_input, "Custo/hora"),
            custo_minimo=self._parse_decimal(self.custo_minimo_input, "Custo mínimo"),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields and numbers before accepting."""
        if not self.codigo_input.text().strip():
            self.set_error("O código é obrigatório.")
            return

        if not self.nome_input.text().strip():
            self.set_error("O nome é obrigatório.")
            return

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

    def _parse_decimal(self, widget: QLineEdit, label: str) -> Decimal | None:
        text = widget.text().strip()
        if not text:
            return None

        normalized = text.replace(" ", "").replace("€", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as error:
            raise ValueError(f"{label} inválido. Use um número, por exemplo 1.5.") from error

    def _format_decimal(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value, "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
