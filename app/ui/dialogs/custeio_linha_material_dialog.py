"""Dialog for editing the material fields of one cost line locally."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.domain.numeros import parse_decimal_humano
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)


class CusteioLinhaMaterialDialog(QDialog):
    """Modal dialog to edit the material snapshot of one cost line."""

    def __init__(
        self,
        linha: OrcamentoItemCusteioLinhaResumo,
        parent=None,
        on_save: Callable[[dict], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.linha = linha
        self.on_save = on_save

        self.setWindowTitle("Editar Dados do Material")
        self.setModal(True)
        self.setMinimumWidth(440)

        self.ref_le_input = QLineEdit(linha.ref_le or "")
        self.descricao_no_orcamento_input = QLineEdit(linha.descricao_no_orcamento or "")
        self.unidade_input = QLineEdit(linha.unidade or "")
        self.preco_liquido_input = QLineEdit(self._format_decimal(linha.preco_liquido))
        self.desperdicio_input = QLineEdit(self._format_decimal(linha.desperdicio_percentagem))
        self.tipo_mp_input = QLineEdit(linha.tipo_materia_prima or "")
        self.familia_mp_input = QLineEdit(linha.familia_materia_prima or "")
        self.orla_0_4_input = QLineEdit(linha.coresp_orla_0_4 or "")
        self.orla_1_0_input = QLineEdit(linha.coresp_orla_1_0 or "")
        self.comp_mp_input = QLineEdit(self._format_decimal(linha.comp_mp))
        self.larg_mp_input = QLineEdit(self._format_decimal(linha.larg_mp))
        self.esp_mp_input = QLineEdit(self._format_decimal(linha.esp_mp))

        self.error_label = QLabel("")
        self.error_label.setObjectName("custeioLinhaMaterialError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Ref LE", self.ref_le_input)
        form.addRow("Descrição no orçamento", self.descricao_no_orcamento_input)
        form.addRow("Unidade", self.unidade_input)
        form.addRow("Preço líquido", self.preco_liquido_input)
        form.addRow("Desperdício %", self.desperdicio_input)
        form.addRow("Tipo matéria-prima", self.tipo_mp_input)
        form.addRow("Família matéria-prima", self.familia_mp_input)
        form.addRow("Orla 0.4", self.orla_0_4_input)
        form.addRow("Orla 1.0", self.orla_1_0_input)
        form.addRow("Comp MP", self.comp_mp_input)
        form.addRow("Larg MP", self.larg_mp_input)
        form.addRow("Esp MP", self.esp_mp_input)

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

    def get_data(self) -> dict:
        """Return the edited material fields (raises ValueError on bad numbers)."""
        return {
            "ref_le": self._empty_to_none(self.ref_le_input.text()),
            "descricao_no_orcamento": self._empty_to_none(
                self.descricao_no_orcamento_input.text()
            ),
            "unidade": self._empty_to_none(self.unidade_input.text()),
            "preco_liquido": self._parse_decimal(self.preco_liquido_input, "Preço líquido"),
            "desperdicio_percentagem": self._parse_decimal(
                self.desperdicio_input, "Desperdício %"
            ),
            "tipo_materia_prima": self._empty_to_none(self.tipo_mp_input.text()),
            "familia_materia_prima": self._empty_to_none(self.familia_mp_input.text()),
            "coresp_orla_0_4": self._empty_to_none(self.orla_0_4_input.text()),
            "coresp_orla_1_0": self._empty_to_none(self.orla_1_0_input.text()),
            "comp_mp": self._parse_decimal(self.comp_mp_input, "Comp MP"),
            "larg_mp": self._parse_decimal(self.larg_mp_input, "Larg MP"),
            "esp_mp": self._parse_decimal(self.esp_mp_input, "Esp MP"),
        }

    def _validate_and_accept(self) -> None:
        """Validate numbers before accepting."""
        try:
            dados = self.get_data()
        except ValueError as error:
            self.set_error(str(error))
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(dados):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _parse_decimal(self, widget: QLineEdit, label: str) -> Decimal | None:
        try:
            return parse_decimal_humano(widget.text())
        except ValueError as error:
            raise ValueError(f"{label} inválido. Use um número, por exemplo 1.5.") from error

    def _format_decimal(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value.normalize(), "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
