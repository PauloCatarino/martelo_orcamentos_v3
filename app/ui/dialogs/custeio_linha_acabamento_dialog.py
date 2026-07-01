"""Dialog for editing the finishing (acabamento) data of one cost line locally."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.domain.acabamentos import SEM_ACABAMENTO, tem_acabamento
from app.domain.numeros import (
    formatar_percentagem,
    normalize_percentagem_humana,
    parse_decimal_humano,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog
from app.utils.formatters import format_currency, format_quantity

FAMILIA_ACABAMENTO = "ACABAMENTO"


class CusteioLinhaAcabamentoDialog(QDialog):
    """Modal dialog to edit the finishing snapshot (sup/inf) of one cost line."""

    def __init__(
        self,
        linha: OrcamentoItemCusteioLinhaResumo,
        parent=None,
        on_save: Callable[[dict], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.linha = linha
        self.on_save = on_save

        self.setWindowTitle("Editar Dados do Acabamento")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.error_label = QLabel("")
        self.error_label.setObjectName("custeioLinhaAcabamentoError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        sup_box = self._criar_zona_face("Face superior", "sup", linha)
        inf_box = self._criar_zona_face("Face inferior", "inf", linha)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(sup_box)
        layout.addWidget(inf_box)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def _criar_zona_face(
        self, titulo: str, face: str, linha: OrcamentoItemCusteioLinhaResumo
    ) -> QGroupBox:
        """Build the editable group box for one finishing face."""
        codigo = linha.acabamento_face_sup if face == "sup" else linha.acabamento_face_inf
        ref_le = getattr(linha, f"acabamento_{face}_ref_le")
        descricao = getattr(linha, f"acabamento_{face}_descricao")
        unidade = getattr(linha, f"acabamento_{face}_unidade")
        preco = getattr(linha, f"acabamento_{face}_preco_liquido")
        desp = getattr(linha, f"acabamento_{face}_desperdicio_percentagem")
        area = (
            linha.area_acabamento_sup if face == "sup" else linha.area_acabamento_inf
        )

        ativo_checkbox = QCheckBox("Ativo")
        ativo_checkbox.setChecked(tem_acabamento(codigo))
        codigo_input = QLineEdit(codigo or "")
        ref_le_input = QLineEdit(ref_le or "")
        descricao_input = QLineEdit(descricao or "")
        unidade_input = QLineEdit(unidade or "")
        preco_input = QLineEdit(self._format_preco(preco))
        desp_input = QLineEdit(self._format_desp(desp))
        area_label = QLabel(format_quantity(area))

        setattr(self, f"ativo_{face}_checkbox", ativo_checkbox)
        setattr(self, f"codigo_{face}_input", codigo_input)
        setattr(self, f"ref_le_{face}_input", ref_le_input)
        setattr(self, f"descricao_{face}_input", descricao_input)
        setattr(self, f"unidade_{face}_input", unidade_input)
        setattr(self, f"preco_{face}_input", preco_input)
        setattr(self, f"desp_{face}_input", desp_input)

        select_button = QPushButton(f"Selecionar acabamento {titulo.lower()}")
        select_button.clicked.connect(lambda _checked=False, f=face: self._selecionar(f))
        setattr(self, f"selecionar_{face}_button", select_button)
        ativo_checkbox.toggled.connect(
            lambda _checked=False, f=face: self._alternar_ativo(f)
        )

        form = QFormLayout()
        form.addRow("Acabamento (código/opção)", codigo_input)
        form.addRow("Ref LE", ref_le_input)
        form.addRow("Descrição", descricao_input)
        form.addRow("Unidade", unidade_input)
        form.addRow("Preço líquido", preco_input)
        form.addRow("Desperdício %", desp_input)
        form.addRow("Área acabamento", area_label)

        box_layout = QVBoxLayout()
        box_layout.addWidget(ativo_checkbox)
        box_layout.addLayout(form)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(select_button)
        box_layout.addLayout(button_row)

        box = QGroupBox(titulo)
        box.setLayout(box_layout)
        self._alternar_ativo(face)
        return box

    def _alternar_ativo(self, face: str) -> None:
        """Enable or disable the editable finishing fields for one face."""
        ativo = getattr(self, f"ativo_{face}_checkbox").isChecked()
        codigo_input = getattr(self, f"codigo_{face}_input")

        for field_name in (
            "codigo",
            "ref_le",
            "descricao",
            "unidade",
            "preco",
            "desp",
        ):
            getattr(self, f"{field_name}_{face}_input").setEnabled(ativo)
        getattr(self, f"selecionar_{face}_button").setEnabled(ativo)

        if ativo and not tem_acabamento(codigo_input.text()):
            codigo_input.clear()

    def _selecionar(self, face: str) -> None:
        """Pick a finishing raw material (family ACABAMENTO) and copy its data."""
        picker = MateriaPrimaPickerDialog(parent=self, initial_familia=FAMILIA_ACABAMENTO)
        if not picker.exec() or picker.selected_materia is None:
            return

        materia = picker.selected_materia
        getattr(self, f"codigo_{face}_input").setText(materia.ref_le or "")
        getattr(self, f"ref_le_{face}_input").setText(materia.ref_le or "")
        getattr(self, f"descricao_{face}_input").setText(materia.descricao or "")
        getattr(self, f"unidade_{face}_input").setText(materia.unidade or "")
        getattr(self, f"preco_{face}_input").setText(
            self._format_preco(materia.preco_liquido)
        )
        getattr(self, f"desp_{face}_input").setText(
            self._format_desp(materia.desperdicio_percentagem)
        )

    def get_data(self) -> dict:
        """Return the edited finishing fields (raises ValueError on bad numbers)."""
        dados: dict = {}
        for face in ("sup", "inf"):
            if not getattr(self, f"ativo_{face}_checkbox").isChecked():
                dados[f"acabamento_face_{face}"] = SEM_ACABAMENTO
            else:
                dados[f"acabamento_face_{face}"] = self._empty_to_none(
                    getattr(self, f"codigo_{face}_input").text()
                )
            dados[f"acabamento_{face}_ref_le"] = self._empty_to_none(
                getattr(self, f"ref_le_{face}_input").text()
            )
            dados[f"acabamento_{face}_descricao"] = self._empty_to_none(
                getattr(self, f"descricao_{face}_input").text()
            )
            dados[f"acabamento_{face}_unidade"] = self._empty_to_none(
                getattr(self, f"unidade_{face}_input").text()
            )
            dados[f"acabamento_{face}_preco_liquido"] = self._parse_decimal(
                getattr(self, f"preco_{face}_input"), "Preço líquido"
            )
            dados[f"acabamento_{face}_desperdicio_percentagem"] = self._parse_desp(
                getattr(self, f"desp_{face}_input")
            )
        return dados

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

    def _parse_desp(self, widget: QLineEdit) -> Decimal | None:
        """Parse a waste value and normalize it to a human percentage (1, 5, ...).

        Accepts "1", "1%", "0.01" or "0,01"; 0.01/0,01 -> 1, 1/1% -> 1.
        """
        valor = self._parse_decimal(widget, "Desperdício %")
        return normalize_percentagem_humana(valor)

    def _format_preco(self, value: Decimal | None) -> str:
        """Show the net price in euros (e.g. 41,50 €)."""
        return format_currency(value)

    def _format_desp(self, value: Decimal | None) -> str:
        """Show the waste as a human percentage (e.g. 1%)."""
        return formatar_percentagem(normalize_percentagem_humana(value))

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
