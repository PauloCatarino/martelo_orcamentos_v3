"""Dialog for creating a simple Orcamento."""

from __future__ import annotations

from dataclasses import dataclass

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
class NovoOrcamentoDialogData:
    """Data collected by the new budget dialog."""

    nome_cliente: str
    email_cliente: str | None
    telefone_cliente: str | None
    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None


class NovoOrcamentoDialog(QDialog):
    """Simple modal dialog for creating a budget."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Novo Or\u00e7amento")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.nome_cliente_input = QLineEdit()
        self.email_cliente_input = QLineEdit()
        self.telefone_cliente_input = QLineEdit()
        self.obra_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.localizacao_input = QLineEdit()
        self.ref_cliente_input = QLineEdit()

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoOrcamentoError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Nome cliente", self.nome_cliente_input)
        form_layout.addRow("Email cliente", self.email_cliente_input)
        form_layout.addRow("Telefone cliente", self.telefone_cliente_input)
        form_layout.addRow("Obra", self.obra_input)
        form_layout.addRow("Descri\u00e7\u00e3o", self.descricao_input)
        form_layout.addRow("Localiza\u00e7\u00e3o", self.localizacao_input)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)

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

    def get_data(self) -> NovoOrcamentoDialogData:
        """Return normalized dialog data."""
        return NovoOrcamentoDialogData(
            nome_cliente=self.nome_cliente_input.text().strip(),
            email_cliente=self._empty_to_none(self.email_cliente_input.text()),
            telefone_cliente=self._empty_to_none(self.telefone_cliente_input.text()),
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        data = self.get_data()

        if not data.nome_cliente:
            self.error_label.setText("O nome do cliente e obrigatorio.")
            return

        if not data.obra:
            self.error_label.setText("A obra e obrigatoria.")
            return

        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
