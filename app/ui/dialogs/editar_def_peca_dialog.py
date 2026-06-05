"""Dialog for editing a reusable piece definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from app.domain.orla_types import (
    format_orla_code,
    get_orla_type_options,
    normalize_orla_type,
)
from app.domain.peca_types import SIMPLES, get_peca_type_options, normalize_peca_type
from app.repositories.def_peca_repository import DefPecaResumo


@dataclass(frozen=True)
class EditarDefPecaDialogData:
    """Data collected by the edit piece definition dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo_peca: str
    grupo: str | None
    orla_c1: int
    orla_c2: int
    orla_l1: int
    orla_l2: int
    ativo: bool


class EditarDefPecaDialog(QDialog):
    """Modal dialog for editing an existing reusable piece definition."""

    def __init__(
        self,
        peca: DefPecaResumo,
        parent=None,
        on_save: Callable[[EditarDefPecaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.peca = peca
        self.on_save = on_save

        self.setWindowTitle("Editar Peça")
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

        self.orla_c1_input = QComboBox()
        self.orla_c2_input = QComboBox()
        self.orla_l1_input = QComboBox()
        self.orla_l2_input = QComboBox()
        orla_combos = (
            self.orla_c1_input,
            self.orla_c2_input,
            self.orla_l1_input,
            self.orla_l2_input,
        )
        for combo in orla_combos:
            for code, label in get_orla_type_options():
                combo.addItem(label, code)

        self.orla_preview_label = QLabel()
        self.orla_preview_label.setObjectName("editarDefPecaOrlaPreview")

        for combo in orla_combos:
            combo.currentIndexChanged.connect(self._update_orla_preview)

        self.error_label = QLabel("")
        self.error_label.setObjectName("editarDefPecaError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Código", self.codigo_input)
        form_layout.addRow("Nome", self.nome_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Tipo de peça", self.tipo_peca_input)
        form_layout.addRow("Grupo", self.grupo_input)
        form_layout.addRow("Ativo", self.ativo_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        orla_group = QGroupBox("Orlas")
        orla_form = QFormLayout()
        orla_form.addRow("C1 - Comprimento lado 1", self.orla_c1_input)
        orla_form.addRow("C2 - Comprimento lado 2", self.orla_c2_input)
        orla_form.addRow("L1 - Largura lado 1", self.orla_l1_input)
        orla_form.addRow("L2 - Largura lado 2", self.orla_l2_input)
        orla_form.addRow(self.orla_preview_label)
        orla_group.setLayout(orla_form)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(orla_group)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._load_peca()

    def _load_peca(self) -> None:
        """Populate the form with the current piece values."""
        self.codigo_input.setText(self.peca.codigo)
        self.nome_input.setText(self.peca.nome)
        self.descricao_input.setPlainText(self.peca.descricao or "")
        self._select_combo_data(self.tipo_peca_input, normalize_peca_type(self.peca.tipo_peca))
        self.grupo_input.setText(self.peca.grupo or "")
        self.ativo_input.setChecked(self.peca.ativo)
        self._select_combo_data(self.orla_c1_input, normalize_orla_type(self.peca.orla_c1))
        self._select_combo_data(self.orla_c2_input, normalize_orla_type(self.peca.orla_c2))
        self._select_combo_data(self.orla_l1_input, normalize_orla_type(self.peca.orla_l1))
        self._select_combo_data(self.orla_l2_input, normalize_orla_type(self.peca.orla_l2))
        self._update_orla_preview()

    def _select_combo_data(self, combo: QComboBox, value: object) -> None:
        """Select the combo entry matching value, falling back to the first."""
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def get_data(self) -> EditarDefPecaDialogData:
        """Return normalized dialog data."""
        return EditarDefPecaDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo_peca=self.tipo_peca_input.currentData() or SIMPLES,
            grupo=self._empty_to_none(self.grupo_input.text()),
            orla_c1=self.orla_c1_input.currentData(),
            orla_c2=self.orla_c2_input.currentData(),
            orla_l1=self.orla_l1_input.currentData(),
            orla_l2=self.orla_l2_input.currentData(),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        data = self.get_data()

        if not data.codigo:
            self.error_label.setText("O código é obrigatório.")
            return

        if not data.nome:
            self.error_label.setText("O nome é obrigatório.")
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def _update_orla_preview(self) -> None:
        """Refresh the edge banding code preview from the combo boxes."""
        code = format_orla_code(
            self.orla_c1_input.currentData(),
            self.orla_c2_input.currentData(),
            self.orla_l1_input.currentData(),
            self.orla_l2_input.currentData(),
        )
        self.orla_preview_label.setText(f"Código de orlas: {code}")

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
