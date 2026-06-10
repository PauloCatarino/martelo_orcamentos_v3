"""Dialog for creating and editing a CNC area price tier (phase 8S.0)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from app.repositories.def_maquina_escalao_area_repository import (
    DefMaquinaEscalaoAreaResumo,
)

# Spin-box sentinel for "not set" (kept as None when saving).
_SEM_VALOR = -1.0


@dataclass(frozen=True)
class EscalaoAreaDialogData:
    """Data collected by the area tier dialog."""

    nivel: int
    area_max_m2: Decimal | None
    preco_peca_std: Decimal | None
    preco_peca_serie: Decimal | None
    ativo: bool


class EscalaoAreaDialog(QDialog):
    """Modal dialog for creating or editing a CNC area price tier."""

    def __init__(
        self,
        escalao: DefMaquinaEscalaoAreaResumo | None = None,
        proximo_nivel: int = 1,
        parent=None,
        on_save: Callable[[EscalaoAreaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.escalao = escalao
        self.on_save = on_save
        self._is_edit = escalao is not None

        self.setWindowTitle("Editar Escalão" if self._is_edit else "Novo Escalão")
        self.setModal(True)
        self.setMinimumWidth(420)

        self.nivel_input = QSpinBox()
        self.nivel_input.setRange(1, 9999)
        self.nivel_input.setValue(proximo_nivel)

        # Unit suffixes shown inside the field; Decimal kept on save (2 decimals).
        self.area_max_input = self._criar_spin(" m2")
        self.preco_std_input = self._criar_spin(" €/peça")
        self.preco_serie_input = self._criar_spin(" €/peça")
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("escalaoAreaDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        info = QLabel(
            "O escalão aplica-se a peças com área até ao limite indicado. Deixe a "
            "área máxima vazia no último escalão (sem limite)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666666; font-size: 11px;")

        form = QFormLayout()
        form.addRow("Nível", self.nivel_input)
        form.addRow("Área máx.", self.area_max_input)
        form.addRow("Preço/peça STD", self.preco_std_input)
        form.addRow("Preço/peça SERIE", self.preco_serie_input)
        form.addRow("Ativo", self.ativo_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if escalao is not None:
            self._load_escalao(escalao)

    def _criar_spin(self, suffix: str) -> QDoubleSpinBox:
        """Build a 2-decimal spin box that shows ``suffix`` and an empty special value."""
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(_SEM_VALOR, 9_999_999.0)
        spin.setSpecialValueText("")  # blank when "not set" (value == minimum)
        spin.setSuffix(suffix)
        spin.setValue(_SEM_VALOR)
        return spin

    def _load_escalao(self, escalao: DefMaquinaEscalaoAreaResumo) -> None:
        """Populate the form with an existing tier."""
        self.nivel_input.setValue(escalao.nivel)
        self._set_spin(self.area_max_input, escalao.area_max_m2)
        self._set_spin(self.preco_std_input, escalao.preco_peca_std)
        self._set_spin(self.preco_serie_input, escalao.preco_peca_serie)
        self.ativo_input.setChecked(escalao.ativo)

    def get_data(self) -> EscalaoAreaDialogData:
        """Return normalized dialog data (empty area = no limit)."""
        return EscalaoAreaDialogData(
            nivel=self.nivel_input.value(),
            area_max_m2=self._spin_to_decimal(self.area_max_input),
            preco_peca_std=self._spin_to_decimal(self.preco_std_input),
            preco_peca_serie=self._spin_to_decimal(self.preco_serie_input),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Accept the tier (spin boxes never raise)."""
        data = self.get_data()

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _set_spin(self, spin: QDoubleSpinBox, value: Decimal | None) -> None:
        """Load a Decimal into a spin box (None -> empty special value)."""
        if value is None:
            spin.setValue(spin.minimum())
        else:
            spin.setValue(float(value))

    def _spin_to_decimal(self, spin: QDoubleSpinBox) -> Decimal | None:
        """Return the spin box value as Decimal, or None when "not set"."""
        valor = spin.value()
        if valor < 0:
            return None

        return Decimal(str(round(valor, spin.decimals())))
