"""Dialog for creating and editing a machine."""

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

from app.repositories.def_maquina_repository import DefMaquinaResumo

TIPO_OPCOES = ("CORTE", "ORLAGEM", "CNC", "MONTAGEM", "MANUAL", "OUTRO")


@dataclass(frozen=True)
class MaquinaDialogData:
    """Data collected by the machine dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    custo_hora: Decimal | None
    observacoes: str | None
    ativo: bool


class MaquinaDialog(QDialog):
    """Modal dialog for creating or editing a machine."""

    def __init__(
        self,
        maquina: DefMaquinaResumo | None = None,
        parent=None,
        on_save: Callable[[MaquinaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.maquina = maquina
        self.on_save = on_save
        self._is_edit = maquina is not None

        self.setWindowTitle("Editar Máquina" if self._is_edit else "Nova Máquina")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.nome_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(70)
        self.tipo_input = QComboBox()
        for opcao in TIPO_OPCOES:
            self.tipo_input.addItem(opcao, opcao)
        self.custo_hora_input = QLineEdit()
        self.custo_hora_input.setPlaceholderText("Ex.: 12.50")
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("maquinaDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Tipo", self.tipo_input)
        form.addRow("Custo/hora", self.custo_hora_input)
        form.addRow("Observações", self.observacoes_input)
        form.addRow("Ativo", self.ativo_input)

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

        if maquina is not None:
            self._load_maquina(maquina)

    def _load_maquina(self, maquina: DefMaquinaResumo) -> None:
        """Populate the form with an existing machine and lock the code."""
        self.codigo_input.setText(maquina.codigo)
        self.codigo_input.setReadOnly(True)
        self.nome_input.setText(maquina.nome)
        self.descricao_input.setPlainText(maquina.descricao or "")
        self._select_tipo(maquina.tipo)
        self.custo_hora_input.setText(self._format_custo_hora(maquina.custo_hora))
        self.observacoes_input.setText(maquina.observacoes or "")
        self.ativo_input.setChecked(maquina.ativo)

    def _select_tipo(self, tipo: str | None) -> None:
        """Select the machine type, keeping unknown values available."""
        if not tipo:
            return

        index = self.tipo_input.findData(tipo)
        if index < 0:
            self.tipo_input.addItem(tipo, tipo)
            index = self.tipo_input.findData(tipo)
        self.tipo_input.setCurrentIndex(index)

    def get_data(self) -> MaquinaDialogData:
        """Return normalized dialog data (raises ValueError on invalid cost)."""
        return MaquinaDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo=self.tipo_input.currentData(),
            custo_hora=self._parse_custo_hora(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields and the cost before accepting."""
        if not self.codigo_input.text().strip():
            self.set_error("O código é obrigatório.")
            return

        if not self.nome_input.text().strip():
            self.set_error("O nome é obrigatório.")
            return

        try:
            data = self.get_data()
        except ValueError:
            self.set_error("Custo/hora inválido. Use um número, por exemplo 12.50.")
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _parse_custo_hora(self) -> Decimal | None:
        text = self.custo_hora_input.text().strip()
        if not text:
            return None

        normalized = text.replace(" ", "").replace("€", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as error:
            raise ValueError("custo_hora invalido") from error

    def _format_custo_hora(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value, "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
