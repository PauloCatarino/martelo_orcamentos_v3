"""Dialog for editing an Orcamento's general data (phase 9.0)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from app.domain.orcamento_estados import ESTADOS_ORCAMENTO


@dataclass(frozen=True)
class EditarOrcamentoDialogData:
    """Data shown/collected by the edit budget dialog."""

    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    estado: str
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None


class EditarOrcamentoDialog(QDialog):
    """Simple modal dialog to edit a budget's general data."""

    def __init__(
        self, parent=None, dados: EditarOrcamentoDialogData | None = None
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Editar Orçamento")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.estado_combo = QComboBox()
        self.estado_combo.setEditable(False)
        self.estado_combo.addItems(list(ESTADOS_ORCAMENTO))
        self.obra_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.localizacao_input = QLineEdit()
        self.ref_cliente_input = QLineEdit()
        self.enc_phc_input = QLineEdit()
        self.info_1_input = QTextEdit()
        self.info_1_input.setFixedHeight(60)
        self.info_2_input = QTextEdit()
        self.info_2_input.setFixedHeight(60)

        # Pre-fill from the received data.
        if dados is not None:
            estado_atual = dados.estado or ""
            if estado_atual and self.estado_combo.findText(estado_atual) < 0:
                self.estado_combo.addItem(estado_atual)
            if estado_atual:
                self.estado_combo.setCurrentText(estado_atual)
            self.obra_input.setText(dados.obra or "")
            self.descricao_input.setPlainText(dados.descricao or "")
            self.localizacao_input.setText(dados.localizacao or "")
            self.ref_cliente_input.setText(dados.ref_cliente or "")
            self.enc_phc_input.setText(dados.enc_phc or "")
            self.info_1_input.setPlainText(dados.info_1 or "")
            self.info_2_input.setPlainText(dados.info_2 or "")

        self.error_label = QLabel("")
        self.error_label.setObjectName("editarOrcamentoError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Estado", self.estado_combo)
        form_layout.addRow("Obra", self.obra_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Localização", self.localizacao_input)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)
        form_layout.addRow("Enc. PHC", self.enc_phc_input)
        form_layout.addRow("Info 1", self.info_1_input)
        form_layout.addRow("Info 2", self.info_2_input)

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

    def get_data(self) -> EditarOrcamentoDialogData:
        """Return normalized dialog data."""
        return EditarOrcamentoDialogData(
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
            estado=self.estado_combo.currentText(),
            enc_phc=self._empty_to_none(self.enc_phc_input.text()),
            info_1=self._empty_to_none(self.info_1_input.toPlainText()),
            info_2=self._empty_to_none(self.info_2_input.toPlainText()),
        )

    def _validate_and_accept(self) -> None:
        """Accept edits; all fields in this dialog are optional."""
        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
