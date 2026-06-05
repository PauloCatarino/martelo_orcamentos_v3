"""Dialog for creating and editing a composite piece component."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.domain.componente_types import (
    PECA,
    get_componente_type_options,
    normalize_componente_type,
)
from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.repositories.def_peca_repository import DefPecaResumo


@dataclass(frozen=True)
class DefPecaComponenteDialogData:
    """Data collected by the component dialog."""

    tipo_componente: str
    def_peca_componente_id: int | None
    referencia_componente: str | None
    descricao: str | None
    ordem: int
    quantidade: Decimal
    regra_quantidade: str
    obrigatorio: bool
    ativo: bool


class DefPecaComponenteDialog(QDialog):
    """Modal dialog for creating or editing a composite piece component."""

    def __init__(
        self,
        pecas_disponiveis: list[DefPecaResumo],
        componente: DefPecaComponenteResumo | None = None,
        parent=None,
        on_save: Callable[[DefPecaComponenteDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.componente = componente
        self.on_save = on_save
        self._is_edit = componente is not None

        self.setWindowTitle("Editar Componente" if self._is_edit else "Novo Componente")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.tipo_componente_input = QComboBox()
        for code, label in get_componente_type_options():
            self.tipo_componente_input.addItem(label, code)

        self.peca_componente_input = QComboBox()
        for peca in pecas_disponiveis:
            self.peca_componente_input.addItem(f"{peca.codigo} - {peca.nome}", peca.id)

        self.referencia_input = QLineEdit()
        self.descricao_input = QLineEdit()

        self.ordem_input = QSpinBox()
        self.ordem_input.setRange(1, 9999)

        self.quantidade_input = QDoubleSpinBox()
        self.quantidade_input.setDecimals(3)
        self.quantidade_input.setRange(0.001, 1_000_000)
        self.quantidade_input.setValue(1)

        self.regra_quantidade_input = QLineEdit()
        self.regra_quantidade_input.setText("FIXA")

        self.obrigatorio_input = QCheckBox()
        self.obrigatorio_input.setChecked(True)
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("defPecaComponenteError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        self.peca_componente_label = QLabel("Peça componente")
        self.referencia_label = QLabel("Referência componente")
        self.ordem_label = QLabel("Ordem")

        form = QFormLayout()
        form.addRow("Tipo de componente", self.tipo_componente_input)
        form.addRow(self.peca_componente_label, self.peca_componente_input)
        form.addRow(self.referencia_label, self.referencia_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow(self.ordem_label, self.ordem_input)
        form.addRow("Quantidade", self.quantidade_input)
        form.addRow("Regra quantidade", self.regra_quantidade_input)
        form.addRow("Obrigatório", self.obrigatorio_input)
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

        self.tipo_componente_input.currentIndexChanged.connect(self._update_tipo_fields)

        if componente is not None:
            self._load_componente(componente)
        else:
            self.ordem_label.setVisible(False)
            self.ordem_input.setVisible(False)

        self._update_tipo_fields()

    def _load_componente(self, componente: DefPecaComponenteResumo) -> None:
        """Populate the form with an existing component."""
        self._select_combo_data(
            self.tipo_componente_input,
            normalize_componente_type(componente.tipo_componente),
        )
        if componente.def_peca_componente_id is not None:
            self._select_combo_data(
                self.peca_componente_input, componente.def_peca_componente_id
            )
        self.referencia_input.setText(componente.referencia_componente or "")
        self.descricao_input.setText(componente.descricao or "")
        self.ordem_input.setValue(componente.ordem)
        self.quantidade_input.setValue(float(componente.quantidade))
        self.regra_quantidade_input.setText(componente.regra_quantidade or "FIXA")
        self.obrigatorio_input.setChecked(componente.obrigatorio)
        self.ativo_input.setChecked(componente.ativo)

    def _update_tipo_fields(self) -> None:
        """Show the piece picker or the textual reference based on the type."""
        is_peca = self.tipo_componente_input.currentData() == PECA
        self.peca_componente_label.setVisible(is_peca)
        self.peca_componente_input.setVisible(is_peca)
        self.referencia_label.setVisible(not is_peca)
        self.referencia_input.setVisible(not is_peca)

    def _select_combo_data(self, combo: QComboBox, value: object) -> None:
        """Select the combo entry matching value when present."""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def get_data(self) -> DefPecaComponenteDialogData:
        """Return normalized dialog data."""
        tipo = self.tipo_componente_input.currentData() or PECA
        is_peca = tipo == PECA
        return DefPecaComponenteDialogData(
            tipo_componente=tipo,
            def_peca_componente_id=self.peca_componente_input.currentData() if is_peca else None,
            referencia_componente=(
                None if is_peca else self._empty_to_none(self.referencia_input.text())
            ),
            descricao=self._empty_to_none(self.descricao_input.text()),
            ordem=self.ordem_input.value(),
            quantidade=Decimal(str(self.quantidade_input.value())),
            regra_quantidade=self.regra_quantidade_input.text().strip() or "FIXA",
            obrigatorio=self.obrigatorio_input.isChecked(),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate the component before accepting."""
        data = self.get_data()

        if data.tipo_componente == PECA and not data.def_peca_componente_id:
            self.error_label.setText("Escolha a peça componente.")
            return

        if (
            data.tipo_componente != PECA
            and not data.referencia_componente
            and not data.descricao
        ):
            self.error_label.setText("Indique a referência ou a descrição do componente.")
            return

        if data.quantidade <= 0:
            self.error_label.setText("A quantidade deve ser maior que 0.")
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
