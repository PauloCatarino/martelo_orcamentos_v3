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
    QVBoxLayout,
)

from app.domain.regra_operacao_types import get_regra_operacao_options, normalize_regra_operacao
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.repositories.def_peca_operacao_repository import DefPecaOperacaoResumo


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
    tempo_setup_minutos: Decimal | None
    tempo_por_unidade_minutos: Decimal | None
    unidade_tempo: str | None
    obrigatorio: bool
    ativo: bool
    observacoes: str | None


class DefPecaOperacaoDialog(QDialog):
    """Modal dialog for linking or editing an operation of a piece definition."""

    def __init__(
        self,
        operacoes_disponiveis: list[DefOperacaoResumo],
        ligacao: DefPecaOperacaoResumo | None = None,
        parent=None,
        on_save: Callable[[DefPecaOperacaoDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.ligacao = ligacao
        self.on_save = on_save
        self._is_edit = ligacao is not None

        self.setWindowTitle("Editar Operação da Peça" if self._is_edit else "Nova Operação da Peça")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.operacao_input = QComboBox()
        for operacao in operacoes_disponiveis:
            self.operacao_input.addItem(f"{operacao.codigo} - {operacao.nome}", operacao.id)

        self.ordem_input = QSpinBox()
        self.ordem_input.setRange(1, 9999)
        self.ordem_input.setValue(1)

        self.regra_calculo_input = QComboBox()
        for code, label in get_regra_operacao_options():
            self.regra_calculo_input.addItem(label, code)

        self.quantidade_base_input = QLineEdit()
        self.quantidade_base_input.setPlaceholderText("Ex.: 1.5")

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
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Regra cálculo", self.regra_calculo_input)
        form.addRow("Quantidade base", self.quantidade_base_input)
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
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if ligacao is not None:
            self._load_ligacao(ligacao)

    def _load_ligacao(self, ligacao: DefPecaOperacaoResumo) -> None:
        """Populate the form with an existing link and lock the operation."""
        index = self.operacao_input.findData(ligacao.def_operacao_id)
        if index >= 0:
            self.operacao_input.setCurrentIndex(index)
        self.operacao_input.setEnabled(False)

        self.ordem_input.setValue(ligacao.ordem)
        self._select_regra(ligacao.regra_calculo)
        self.quantidade_base_input.setText(self._format_decimal(ligacao.quantidade_base))
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
            tempo_setup_minutos=self._parse_decimal_input(self.tempo_setup_input),
            tempo_por_unidade_minutos=self._parse_decimal_input(
                self.tempo_por_unidade_input
            ),
            unidade_tempo=self.unidade_tempo_input.currentData(),
            obrigatorio=self.obrigatorio_input.isChecked(),
            ativo=self.ativo_input.isChecked(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
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
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _parse_decimal_input(self, widget: QLineEdit) -> Decimal | None:
        text = widget.text().strip()
        if not text:
            return None

        normalized = text.replace(" ", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as error:
            raise ValueError("valor numerico invalido") from error

    def _format_decimal(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value, "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
