"""Dialog for editing a reusable piece definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
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
from app.domain.peca_funcao_types import get_peca_funcao_options
from app.domain.peca_types import SIMPLES, get_peca_type_options, normalize_peca_type
from app.domain.peca_natureza_types import (
    CONJUNTO,
    MATERIAL,
    NEUTRA,
    SERVICO,
    get_peca_natureza_options,
    get_peca_orientacao_options,
    normalize_peca_natureza,
    normalize_peca_orientacao,
)
from app.repositories.def_peca_repository import DefPecaResumo
from app.ui.helpers.valueset_combo_helper import (
    carregar_chaves_valueset_combo,
    obter_valor_chave_combo,
)


@dataclass(frozen=True)
class EditarDefPecaDialogData:
    """Data collected by the edit piece definition dialog."""

    codigo: str
    nome: str
    nome_biblioteca: str | None
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


class EditarDefPecaDialog(QDialog):
    """Modal dialog for editing an existing reusable piece definition."""

    saved = Signal()

    def __init__(
        self,
        peca: DefPecaResumo,
        parent=None,
        on_save: Callable[[EditarDefPecaDialogData], bool] | None = None,
        on_save_as: Callable[[EditarDefPecaDialogData], bool] | None = None,
        embedded: bool = False,
    ) -> None:
        super().__init__(parent)

        self.peca = peca
        self.on_save = on_save
        self.on_save_as = on_save_as
        self.embedded = embedded
        self._is_edit = True

        self.setWindowTitle("Editar Peça")
        self.setModal(True)
        if self.embedded:
            # The same form is hosted in the Dados Gerais tab; it behaves as a
            # child widget instead of opening a modal window.
            self.setModal(False)
            self.setWindowFlags(Qt.WindowType.Widget)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.nome_input = QLineEdit()
        self.nome_biblioteca_input = QLineEdit()
        self.nome_biblioteca_input.setPlaceholderText("Vazio = usa o Nome")
        self.nome_biblioteca_input.setToolTip(
            "Texto que aparece na biblioteca de peças do custeio (seguido do "
            "código de orlas). Se ficar vazio, a biblioteca mostra o Nome."
        )
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
        self.funcao_input = QComboBox()
        self.funcao_input.setEditable(True)
        self.funcao_input.addItem("Selecionar origem…", None)
        for code, label in get_peca_funcao_options():
            self.funcao_input.addItem(label, code)
        self.funcao_input.setCurrentText("")
        self.funcao_input.setToolTip(
            "Origem estrutural da peça. Nome, material, orlas, uniões e operações "
            "podem variar sem alterar esta origem. Pode também escrever uma origem nova."
        )
        self.grupo_input = QComboBox()
        self.grupo_input.setEditable(True)
        for grupo in (
            "", "TETOS", "FUNDOS", "PRATELEIRAS FIXAS",
            "PRATELEIRAS AMOVIVEIS", "LATERAIS", "COSTAS", "PORTAS",
            "GAVETAS", "REMATES/GUARNICOES", "FERRAGENS", "ACESSORIOS",
            "SERVICOS", "PAINEIS SIMPLES",
        ):
            self.grupo_input.addItem(grupo)
        self.ativo_input = QCheckBox()
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

        carregar_chaves_valueset_combo(
            self.chave_valueset_material_input,
            valor_atual=peca.chave_valueset_material,
        )
        carregar_chaves_valueset_combo(
            self.chave_valueset_acabamento_sup_input,
            tipo="ACABAMENTO",
            valor_atual=peca.chave_valueset_acabamento_sup,
        )
        carregar_chaves_valueset_combo(
            self.chave_valueset_acabamento_inf_input,
            tipo="ACABAMENTO",
            valor_atual=peca.chave_valueset_acabamento_inf,
        )
        self.permite_acabamento_input.toggled.connect(self._update_acabamento_enabled)
        self.sem_material_input.toggled.connect(self._update_sem_material_enabled)
        self.natureza_input.currentIndexChanged.connect(self._update_natureza)

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
        form_layout.addRow("Nome na biblioteca", self.nome_biblioteca_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Natureza", self.natureza_input)
        form_layout.addRow("Orientação", self.orientacao_input)
        form_layout.addRow("Origem estrutural", self.funcao_input)
        form_layout.addRow("Grupo", self.grupo_input)
        form_layout.addRow("Ativo", self.ativo_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.save_as_button = self.button_box.addButton(
            "Gravar como…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.save_as_button.setToolTip(
            "Grava estes dados como um registo novo, sem alterar o original."
        )
        self.save_as_button.setVisible(self._is_edit)
        if self.embedded:
            self.save_as_button.setVisible(False)
            self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setVisible(False)
        self.button_box.accepted.connect(self._validate_and_accept)
        self.save_as_button.clicked.connect(self._validate_and_save_as)
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

        self._load_peca()

    def _load_peca(self) -> None:
        """Populate the form with the current piece values."""
        self.codigo_input.setText(self.peca.codigo)
        self.nome_input.setText(self.peca.nome)
        self.nome_biblioteca_input.setText(
            getattr(self.peca, "nome_biblioteca", None) or ""
        )
        self.descricao_input.setPlainText(self.peca.descricao or "")
        self._select_combo_data(self.tipo_peca_input, normalize_peca_type(self.peca.tipo_peca))
        self._select_combo_data(
            self.natureza_input, normalize_peca_natureza(self.peca.natureza)
        )
        self._select_combo_data(
            self.orientacao_input, normalize_peca_orientacao(self.peca.orientacao)
        )
        self._select_editable_combo(self.funcao_input, self.peca.funcao)
        self.grupo_input.setCurrentText(self.peca.grupo or "")
        self.ativo_input.setChecked(self.peca.ativo)
        self._select_combo_data(self.orla_c1_input, normalize_orla_type(self.peca.orla_c1))
        self._select_combo_data(self.orla_c2_input, normalize_orla_type(self.peca.orla_c2))
        self._select_combo_data(self.orla_l1_input, normalize_orla_type(self.peca.orla_l1))
        self._select_combo_data(self.orla_l2_input, normalize_orla_type(self.peca.orla_l2))
        self.permite_acabamento_input.setChecked(self.peca.permite_acabamento)
        self.sem_material_input.setChecked(getattr(self.peca, "sem_material", False))
        self._update_natureza()
        self._update_acabamento_enabled()
        self._update_sem_material_enabled()
        self._update_orla_preview()

    def _select_combo_data(self, combo: QComboBox, value: object) -> None:
        """Select the combo entry matching value, falling back to the first."""
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _select_editable_combo(self, combo: QComboBox, value: str | None) -> None:
        """Select a known structural origin or preserve a custom legacy value."""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentText(value or "")

    def get_data(self) -> EditarDefPecaDialogData:
        """Return normalized dialog data."""
        natureza = self.natureza_input.currentData() or MATERIAL
        return EditarDefPecaDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            nome_biblioteca=self._empty_to_none(self.nome_biblioteca_input.text()),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo_peca="COMPOSTA" if natureza == CONJUNTO else SIMPLES,
            natureza=natureza,
            orientacao=self.orientacao_input.currentData() or NEUTRA,
            funcao=(
                self.funcao_input.currentData()
                or self._empty_to_none(self.funcao_input.currentText())
            ),
            grupo=self._empty_to_none(self.grupo_input.currentText()),
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
        """Validate required fields and save before accepting."""
        self._validate_and_run(self.on_save)

    def _validate_and_save_as(self) -> None:
        """Validate required fields and save as a new record before accepting."""
        self._validate_and_run(self.on_save_as)

    def _validate_and_run(
        self,
        callback: Callable[[EditarDefPecaDialogData], bool] | None,
    ) -> None:
        """Run validation, then delegate to the requested save callback."""
        data = self.get_data()

        if not data.codigo:
            self.error_label.setText("O código é obrigatório.")
            return

        if not data.nome:
            self.error_label.setText("O nome é obrigatório.")
            return

        self.error_label.clear()
        if callback is not None and not callback(data):
            return

        if self.embedded:
            self.saved.emit()
        else:
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
