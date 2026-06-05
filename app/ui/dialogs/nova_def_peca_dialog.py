"""Dialog for creating a reusable piece definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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

from app.domain.peca_types import SIMPLES, get_peca_type_options


@dataclass(frozen=True)
class NovaDefPecaDialogData:
    """Data collected by the new piece definition dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo_peca: str
    grupo: str | None
    ativo: bool


class NovaDefPecaDialog(QDialog):
    """Simple modal dialog for creating a reusable piece definition."""

    def __init__(
        self,
        parent=None,
        on_save: Callable[[NovaDefPecaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save

        self.setWindowTitle("Nova Pe\u00e7a")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.nome_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.tipo_peca_input = QComboBox()
        for code, label in get_peca_type_options():
            self.tipo_peca_input.addItem(label, code)
        self.grupo_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("novaDefPecaError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("C\u00f3digo", self.codigo_input)
        form_layout.addRow("Nome", self.nome_input)
        form_layout.addRow("Descri\u00e7\u00e3o", self.descricao_input)
        form_layout.addRow("Tipo de pe\u00e7a", self.tipo_peca_input)
        form_layout.addRow("Grupo", self.grupo_input)
        form_layout.addRow("Ativo", self.ativo_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> NovaDefPecaDialogData:
        """Return normalized dialog data."""
        return NovaDefPecaDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo_peca=self.tipo_peca_input.currentData() or SIMPLES,
            grupo=self._empty_to_none(self.grupo_input.text()),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        data = self.get_data()

        if not data.codigo:
            self.error_label.setText("O c\u00f3digo \u00e9 obrigat\u00f3rio.")
            return

        if not data.nome:
            self.error_label.setText("O nome \u00e9 obrigat\u00f3rio.")
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
