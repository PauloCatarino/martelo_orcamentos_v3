"""Dialog for creating a reusable piece definition."""

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

from app.domain.orla_types import format_orla_code, get_orla_type_options
from app.domain.peca_types import SIMPLES, get_peca_type_options
from app.domain.peca_natureza_types import (
    CONJUNTO,
    MATERIAL,
    NEUTRA,
    SERVICO,
    get_peca_natureza_options,
    get_peca_orientacao_options,
)
from app.ui.helpers.valueset_combo_helper import (
    carregar_chaves_valueset_combo,
    obter_valor_chave_combo,
)


@dataclass(frozen=True)
class NovaDefPecaDialogData:
    """Data collected by the new piece definition dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo_peca: str
    natureza: str
    orientacao: str
    funcao: str | None
    grupo: str | None
    orla_c1: int
    orla_c2: int
    orla_l1: int
    orla_l2: int
    chave_valueset_material: str | None
    permite_acabamento: bool
    chave_valueset_acabamento_sup: str | None
    chave_valueset_acabamento_inf: str | None
    sem_material: bool
    ativo: bool


class NovaDefPecaDialog(QDialog):
    """Simple modal dialog for creating a reusable piece definition."""

    def __init__(
        self,
        parent=None,
        on_save: Callable[[NovaDefPecaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save

        self.setWindowTitle("Nova Pe\u00e7a")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.nome_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.tipo_peca_input = QComboBox()
        for code, label in get_peca_type_options():
            self.tipo_peca_input.addItem(label, code)
        self.natureza_input = QComboBox()
        for code, label in get_peca_natureza_options():
            self.natureza_input.addItem(label, code)
        self.orientacao_input = QComboBox()
        for code, label in get_peca_orientacao_options():
            self.orientacao_input.addItem(label, code)
        self.funcao_input = QLineEdit()
        self.grupo_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)
        self.chave_valueset_material_input = QComboBox()
        self.sem_material_input = QCheckBox("Peça de serviço (sem material)")
        self.sem_material_input.setToolTip(
            "A peça não consome matéria-prima: o custo vem apenas das operações "
            "associadas (corte, CNC, manual, montagem). Ao marcar, a chave de "
            "material ValueSet é desativada e ignorada."
        )
        self.sem_material_input.setEnabled(False)
        self.permite_acabamento_input = QCheckBox()
        self.chave_valueset_acabamento_sup_input = QComboBox()
        self.chave_valueset_acabamento_inf_input = QComboBox()

        carregar_chaves_valueset_combo(self.chave_valueset_material_input)
        self.sem_material_input.toggled.connect(self._update_sem_material_enabled)
        self.natureza_input.currentIndexChanged.connect(self._update_natureza)
        self._update_natureza()
        self._update_sem_material_enabled()
        carregar_chaves_valueset_combo(
            self.chave_valueset_acabamento_sup_input, tipo="ACABAMENTO"
        )
        carregar_chaves_valueset_combo(
            self.chave_valueset_acabamento_inf_input, tipo="ACABAMENTO"
        )
        self.permite_acabamento_input.toggled.connect(self._update_acabamento_enabled)
        self._update_acabamento_enabled()

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
        self.orla_preview_label.setObjectName("novaDefPecaOrlaPreview")

        for combo in orla_combos:
            combo.currentIndexChanged.connect(self._update_orla_preview)
        self._update_orla_preview()

        self.error_label = QLabel("")
        self.error_label.setObjectName("novaDefPecaError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("C\u00f3digo", self.codigo_input)
        form_layout.addRow("Nome", self.nome_input)
        form_layout.addRow("Descri\u00e7\u00e3o", self.descricao_input)
        form_layout.addRow("Natureza", self.natureza_input)
        form_layout.addRow("Orienta\u00e7\u00e3o", self.orientacao_input)
        form_layout.addRow("Fun\u00e7\u00e3o", self.funcao_input)
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

        valueset_group = QGroupBox("ValueSets")
        valueset_form = QFormLayout()
        valueset_form.addRow("Peça de serviço", self.sem_material_input)
        valueset_form.addRow("Chave material ValueSet", self.chave_valueset_material_input)
        valueset_form.addRow("Permite acabamento", self.permite_acabamento_input)
        valueset_form.addRow(
            "Chave acabamento face superior",
            self.chave_valueset_acabamento_sup_input,
        )
        valueset_form.addRow(
            "Chave acabamento face inferior",
            self.chave_valueset_acabamento_inf_input,
        )
        valueset_group.setLayout(valueset_form)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(orla_group)
        layout.addWidget(valueset_group)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> NovaDefPecaDialogData:
        """Return normalized dialog data."""
        natureza = self.natureza_input.currentData() or MATERIAL
        return NovaDefPecaDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo_peca="COMPOSTA" if natureza == CONJUNTO else SIMPLES,
            natureza=natureza,
            orientacao=self.orientacao_input.currentData() or NEUTRA,
            funcao=self._empty_to_none(self.funcao_input.text()),
            grupo=self._empty_to_none(self.grupo_input.text()),
            orla_c1=self.orla_c1_input.currentData(),
            orla_c2=self.orla_c2_input.currentData(),
            orla_l1=self.orla_l1_input.currentData(),
            orla_l2=self.orla_l2_input.currentData(),
            chave_valueset_material=(
                None
                if self.sem_material_input.isChecked()
                else obter_valor_chave_combo(self.chave_valueset_material_input)
            ),
            permite_acabamento=self.permite_acabamento_input.isChecked(),
            chave_valueset_acabamento_sup=obter_valor_chave_combo(
                self.chave_valueset_acabamento_sup_input
            ),
            chave_valueset_acabamento_inf=obter_valor_chave_combo(
                self.chave_valueset_acabamento_inf_input
            ),
            sem_material=natureza in (SERVICO, CONJUNTO),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        data = self.get_data()

        if not data.codigo:
            self.error_label.setText("O c\u00f3digo \u00e9 obrigat\u00f3rio.")
            return

        if not data.nome:
            self.error_label.setText("O nome \u00e9 obrigat\u00f3rio.")
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

    def _update_acabamento_enabled(self) -> None:
        """Enable or disable finish ValueSet combos."""
        enabled = self.permite_acabamento_input.isChecked()
        self.chave_valueset_acabamento_sup_input.setEnabled(enabled)
        self.chave_valueset_acabamento_inf_input.setEnabled(enabled)

    def _update_sem_material_enabled(self) -> None:
        """Disable and clear the material ValueSet combo for service pieces."""
        sem_material = self.sem_material_input.isChecked()
        self.chave_valueset_material_input.setEnabled(not sem_material)
        if sem_material:
            self.chave_valueset_material_input.setCurrentIndex(0)

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None

    def _update_natureza(self) -> None:
        """Derive legacy material behavior from the unified nature field."""
        self.sem_material_input.setChecked(
            self.natureza_input.currentData() in (SERVICO, CONJUNTO)
        )
