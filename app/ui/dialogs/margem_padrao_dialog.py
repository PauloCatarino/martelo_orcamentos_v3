"""Dialog for creating/editing a per-customer or per-user default margin."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

TOOLTIP_VALOR_INICIAL = (
    "Estas margens são apenas o VALOR INICIAL dos novos orçamentos; dentro "
    "de cada orçamento o utilizador altera livremente."
)


@dataclass(frozen=True)
class MargemPadraoDialogData:
    """Data collected by the default-margin dialog."""

    entidade_id: int | None
    margem_lucro_pct: Decimal
    margem_mp_pct: Decimal
    margem_mao_obra_pct: Decimal
    margem_acabamentos_pct: Decimal
    custos_administrativos_pct: Decimal


class MargemPadraoDialog(QDialog):
    """Modal dialog with an entity combo (customer/user) and the 5 percents.

    ``entidades`` is a list of (id, label). In edit mode the combo is locked
    to the record's entity (the margins are the editable part).
    """

    def __init__(
        self,
        parent=None,
        *,
        titulo: str,
        entidade_label: str,
        entidades: list[tuple[int, str]],
        dados: MargemPadraoDialogData | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(420)

        self.entidade_combo = QComboBox()
        for entidade_id, label in entidades:
            self.entidade_combo.addItem(label, entidade_id)
        self.entidade_combo.setToolTip(TOOLTIP_VALOR_INICIAL)

        self.margem_lucro_spin = self._criar_spin()
        self.margem_mp_spin = self._criar_spin()
        self.margem_mao_obra_spin = self._criar_spin()
        self.margem_acabamentos_spin = self._criar_spin()
        self.custos_administrativos_spin = self._criar_spin()

        if dados is not None:
            if dados.entidade_id is not None:
                index = self.entidade_combo.findData(dados.entidade_id)
                if index >= 0:
                    self.entidade_combo.setCurrentIndex(index)
            # Editing margins of an existing record: the entity is fixed.
            self.entidade_combo.setEnabled(False)
            self.margem_lucro_spin.setValue(float(dados.margem_lucro_pct))
            self.margem_mp_spin.setValue(float(dados.margem_mp_pct))
            self.margem_mao_obra_spin.setValue(float(dados.margem_mao_obra_pct))
            self.margem_acabamentos_spin.setValue(
                float(dados.margem_acabamentos_pct)
            )
            self.custos_administrativos_spin.setValue(
                float(dados.custos_administrativos_pct)
            )

        info = QLabel(TOOLTIP_VALOR_INICIAL)
        info.setWordWrap(True)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow(entidade_label, self.entidade_combo)
        form_layout.addRow("Margem Lucro", self.margem_lucro_spin)
        form_layout.addRow("Margem Matérias-Primas", self.margem_mp_spin)
        form_layout.addRow("Margem Mão de Obra", self.margem_mao_obra_spin)
        form_layout.addRow("Margem Acabamentos", self.margem_acabamentos_spin)
        form_layout.addRow("Custos Administrativos", self.custos_administrativos_spin)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> MargemPadraoDialogData:
        """Return the dialog data."""

        def valor(spin: QDoubleSpinBox) -> Decimal:
            return Decimal(str(round(spin.value(), 2)))

        return MargemPadraoDialogData(
            entidade_id=self.entidade_combo.currentData(),
            margem_lucro_pct=valor(self.margem_lucro_spin),
            margem_mp_pct=valor(self.margem_mp_spin),
            margem_mao_obra_pct=valor(self.margem_mao_obra_spin),
            margem_acabamentos_pct=valor(self.margem_acabamentos_spin),
            custos_administrativos_pct=valor(self.custos_administrativos_spin),
        )

    def _criar_spin(self) -> QDoubleSpinBox:
        """Build one percent field."""
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(-100.0, 999.99)
        spin.setSuffix(" %")
        spin.setToolTip(TOOLTIP_VALOR_INICIAL)
        return spin

    def _validate_and_accept(self) -> None:
        """Require an entity before accepting."""
        if self.entidade_combo.currentData() is None:
            self.error_label.setText("Escolha um registo na lista.")
            return

        self.accept()
