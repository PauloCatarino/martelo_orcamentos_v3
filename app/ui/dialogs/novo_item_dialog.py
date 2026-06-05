"""Dialog for creating a simple budget item."""

from __future__ import annotations

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
class NovoItemDialogData:
    """Data collected by the new item dialog."""

    codigo: str | None
    item: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal
    unidade: str
    preco_unitario: Decimal


class NovoItemDialog(QDialog):
    """Simple modal dialog for creating a budget item."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Novo Item")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.item_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.altura_input = QLineEdit()
        self.largura_input = QLineEdit()
        self.profundidade_input = QLineEdit()
        self.quantidade_input = QLineEdit("1")
        self.unidade_input = QLineEdit("un")
        self.preco_unitario_input = QLineEdit("0")

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoItemError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("C\u00f3digo", self.codigo_input)
        form_layout.addRow("Item", self.item_input)
        form_layout.addRow("Descri\u00e7\u00e3o", self.descricao_input)
        form_layout.addRow("Altura", self.altura_input)
        form_layout.addRow("Largura", self.largura_input)
        form_layout.addRow("Profundidade", self.profundidade_input)
        form_layout.addRow("Quantidade", self.quantidade_input)
        form_layout.addRow("Unidade", self.unidade_input)
        form_layout.addRow("Pre\u00e7o unit\u00e1rio", self.preco_unitario_input)

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

    def get_data(self) -> NovoItemDialogData:
        """Return normalized dialog data."""
        return NovoItemDialogData(
            codigo=self._empty_to_none(self.codigo_input.text()),
            item=self.item_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            altura=self._parse_optional_decimal(self.altura_input.text()),
            largura=self._parse_optional_decimal(self.largura_input.text()),
            profundidade=self._parse_optional_decimal(self.profundidade_input.text()),
            quantidade=self._parse_decimal(self.quantidade_input.text()),
            unidade=self.unidade_input.text().strip() or "un",
            preco_unitario=self._parse_decimal(self.preco_unitario_input.text()),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        try:
            data = self.get_data()
        except ValueError as error:
            self.error_label.setText(str(error))
            return

        if not data.item:
            self.error_label.setText("O item e obrigatorio.")
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
