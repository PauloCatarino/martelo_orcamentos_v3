"""Dialog for creating or editing a budget item module."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)


@dataclass(frozen=True)
class NovoModuloDialogData:
    """Data collected by the module dialog."""

    nome: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal


class NovoModuloDialog(QDialog):
    """Simple modal dialog for creating or editing a module."""

    def __init__(self, parent=None, modulo_data: NovoModuloDialogData | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Editar M\u00f3dulo" if modulo_data is not None else "Novo M\u00f3dulo")
        self.setModal(True)
        self.setMinimumWidth(440)

        self.nome_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.altura_input = QLineEdit()
        self.largura_input = QLineEdit()
        self.profundidade_input = QLineEdit()
        self.quantidade_input = QLineEdit("1")

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoModuloError")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Nome", self.nome_input)
        form_layout.addRow("Descri\u00e7\u00e3o", self.descricao_input)
        form_layout.addRow("Altura", self.altura_input)
        form_layout.addRow("Largura", self.largura_input)
        form_layout.addRow("Profundidade", self.profundidade_input)
        form_layout.addRow("Quantidade", self.quantidade_input)

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

        if modulo_data is not None:
            self._fill_from_data(modulo_data)

    def get_data(self) -> NovoModuloDialogData:
        """Return normalized dialog data."""
        return NovoModuloDialogData(
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            altura=self._parse_optional_decimal(self.altura_input.text()),
            largura=self._parse_optional_decimal(self.largura_input.text()),
            profundidade=self._parse_optional_decimal(self.profundidade_input.text()),
            quantidade=self._parse_decimal(self.quantidade_input.text()),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        try:
            data = self.get_data()
        except ValueError as error:
            self.error_label.setText(str(error))
            return

        if not data.nome:
            self.error_label.setText("O nome e obrigatorio.")
            return

        if data.quantidade <= 0:
            self.error_label.setText("A quantidade deve ser maior que 0.")
            return

        self.accept()

    def _parse_optional_decimal(self, value: str) -> Decimal | None:
        """Parse an optional decimal text value."""
        if not value.strip():
            return None

        return self._parse_decimal(value)

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse a decimal accepting comma or dot separators."""
        normalized = value.strip().replace(",", ".")
        if not normalized:
            raise ValueError("Preencha os valores numericos obrigatorios.")

        try:
            return Decimal(normalized)
        except InvalidOperation as error:
            raise ValueError("Valores numericos invalidos.") from error

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None

    def _fill_from_data(self, modulo_data: NovoModuloDialogData) -> None:
        """Fill dialog fields from existing module data."""
        self.nome_input.setText(modulo_data.nome)
        self.descricao_input.setPlainText(modulo_data.descricao or "")
        self.altura_input.setText(self._format_decimal(modulo_data.altura))
        self.largura_input.setText(self._format_decimal(modulo_data.largura))
        self.profundidade_input.setText(self._format_decimal(modulo_data.profundidade))
        self.quantidade_input.setText(self._format_decimal(modulo_data.quantidade))

    def _format_decimal(self, value: Decimal | None) -> str:
        """Format decimal values for dialog fields."""
        if value is None:
            return ""

        return f"{value:g}"
