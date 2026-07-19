"""Dialog for editing the material fields of one cost line locally."""

from __future__ import annotations
from app.ui import tema

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.domain.custos import unidade_custo_valida
from app.domain.materia_prima_snapshot import familia_materia_prima, tipo_materia_prima
from app.domain.numeros import parse_decimal_humano, validar_decimal
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog
from app.ui.helpers.orla_picker import obter_precos_orlas_m2
from app.ui.widgets.orla_line_edit import OrlaLineEdit


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
        self.orla_0_4_input = OrlaLineEdit(linha.coresp_orla_0_4 or "")
        self.orla_1_0_input = OrlaLineEdit(linha.coresp_orla_1_0 or "")
        self.preco_orla_0_4_input = QLineEdit(self._format_decimal(linha.preco_orla_0_4_m2))
        self.preco_orla_1_0_input = QLineEdit(self._format_decimal(linha.preco_orla_1_0_m2))
        for widget in (self.preco_orla_0_4_input, self.preco_orla_1_0_input):
            widget.setToolTip(
                "Snapshot local da orla. Unidade obrigatória: euros por metro quadrado (€/m²)."
            )
        self.comp_mp_input = QLineEdit(self._format_decimal(linha.comp_mp))
        self.larg_mp_input = QLineEdit(self._format_decimal(linha.larg_mp))
        self.esp_mp_input = QLineEdit(self._format_decimal(linha.esp_mp))

        self.error_label = QLabel("")
        self.error_label.setObjectName("custeioLinhaMaterialError")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        self.selecionar_mp_button = QPushButton("Selecionar Matéria-Prima")
        self.selecionar_mp_button.clicked.connect(self.abrir_picker_materia_prima)
        form.addRow("", self.selecionar_mp_button)
        form.addRow("Ref LE", self.ref_le_input)
        form.addRow("Descrição no orçamento", self.descricao_no_orcamento_input)
        form.addRow("Unidade", self.unidade_input)
        form.addRow("Preço líquido", self.preco_liquido_input)
        form.addRow("Desperdício %", self.desperdicio_input)
        form.addRow("Tipo matéria-prima", self.tipo_mp_input)
        form.addRow("Família matéria-prima", self.familia_mp_input)
        form.addRow("Orla 0.4 (duplo clique para selecionar)", self.orla_0_4_input)
        form.addRow("Preço orla 0.4 (€/m²)", self.preco_orla_0_4_input)
        form.addRow("Orla 1.0 (duplo clique para selecionar)", self.orla_1_0_input)
        form.addRow("Preço orla 1.0 (€/m²)", self.preco_orla_1_0_input)
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
        self.orla_0_4_input.doubleClicked.connect(lambda: self._abrir_picker_orla("0_4"))
        self.orla_1_0_input.doubleClicked.connect(lambda: self._abrir_picker_orla("1_0"))

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> dict:
        """Return the edited material fields (raises ValueError on bad numbers)."""
        dados = {
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
            "preco_orla_0_4_m2": self._parse_decimal(
                self.preco_orla_0_4_input, "Preço orla 0.4 (€/m²)"
            ),
            "preco_orla_1_0_m2": self._parse_decimal(
                self.preco_orla_1_0_input, "Preço orla 1.0 (€/m²)"
            ),
            "comp_mp": self._parse_decimal(self.comp_mp_input, "Comp MP"),
            "larg_mp": self._parse_decimal(self.larg_mp_input, "Larg MP"),
            "esp_mp": self._parse_decimal(self.esp_mp_input, "Esp MP"),
        }
        self._validar_dados(dados)
        return dados

    def _validar_dados(self, dados: dict) -> None:
        unidade = dados.get("unidade")
        if unidade and not unidade_custo_valida(unidade):
            raise ValueError("Unidade inválida. Use M2, ML ou UND.")
        validar_decimal(dados.get("preco_liquido"), "Preço líquido", minimo=Decimal("0"))
        validar_decimal(
            dados.get("desperdicio_percentagem"), "Desperdício %", minimo=Decimal("0")
        )
        validar_decimal(
            dados.get("preco_orla_0_4_m2"), "Preço orla 0.4 (€/m²)", minimo=Decimal("0")
        )
        validar_decimal(
            dados.get("preco_orla_1_0_m2"), "Preço orla 1.0 (€/m²)", minimo=Decimal("0")
        )
        for campo, rotulo in (
            ("comp_mp", "Comp MP"),
            ("larg_mp", "Larg MP"),
            ("esp_mp", "Esp MP"),
        ):
            validar_decimal(dados.get(campo), rotulo, minimo=Decimal("0"))

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

    def abrir_picker_materia_prima(self) -> None:
        """Select a board and copy its material plus local edge snapshots."""
        picker = MateriaPrimaPickerDialog(parent=self)
        if picker.exec() and picker.selected_materia is not None:
            materia = picker.selected_materia
            self.ref_le_input.setText(materia.ref_le or "")
            self.descricao_no_orcamento_input.setText(materia.descricao or "")
            self.unidade_input.setText(materia.unidade or "")
            self.preco_liquido_input.setText(self._format_decimal(materia.preco_liquido))
            self.desperdicio_input.setText(
                self._format_decimal(materia.desperdicio_percentagem)
            )
            self.tipo_mp_input.setText(tipo_materia_prima(materia) or "")
            self.familia_mp_input.setText(familia_materia_prima(materia) or "")
            self.orla_0_4_input.setText(getattr(materia, "coresp_orla_0_4", None) or "")
            self.orla_1_0_input.setText(getattr(materia, "coresp_orla_1_0", None) or "")
            preco_fina, preco_grossa = obter_precos_orlas_m2(materia)
            self.preco_orla_0_4_input.setText(self._format_decimal(preco_fina))
            self.preco_orla_1_0_input.setText(self._format_decimal(preco_grossa))
            self.comp_mp_input.setText(self._format_decimal(materia.comprimento))
            self.larg_mp_input.setText(self._format_decimal(materia.largura))
            self.esp_mp_input.setText(self._format_decimal(materia.espessura))

    def _abrir_picker_orla(self, espessura: str) -> None:
        picker = MateriaPrimaPickerDialog(
            parent=self, initial_familia="ORLA", apenas_orlas=True
        )
        if not picker.exec() or picker.selected_materia is None:
            return
        materia = picker.selected_materia
        ref_input = self.orla_0_4_input if espessura == "0_4" else self.orla_1_0_input
        preco_input = (
            self.preco_orla_0_4_input if espessura == "0_4" else self.preco_orla_1_0_input
        )
        ref_input.setText(materia.ref_le or "")
        preco_input.setText(self._format_decimal(materia.preco_liquido))

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
