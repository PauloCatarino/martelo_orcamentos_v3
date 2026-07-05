"""Dialog for creating and editing a configurable ValueSet key."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.repositories.def_valueset_chave_repository import DefValuesetChaveResumo

TIPO_OPCOES = (
    "MATERIAL",
    "FERRAGEM",
    "SISTEMA_CORRER",
    "ILUMINACAO",
    "ORLA",
    "ACABAMENTO",
    "ACESSORIO",
    "OUTRO",
)

GRUPO_OPCOES = (
    "MATERIAIS",
    "FERRAGENS",
    "SISTEMAS_CORRER",
    "ILUMINACAO",
    "ORLAS",
    "ACABAMENTOS",
    "ACESSORIOS",
    "OUTROS",
)


@dataclass(frozen=True)
class DefValuesetChaveDialogData:
    """Data collected by the ValueSet key dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    grupo: str | None
    sistema: bool
    ordem: int
    observacoes: str | None
    ativo: bool


class DefValuesetChaveDialog(QDialog):
    """Modal dialog for creating or editing a ValueSet key."""

    def __init__(
        self,
        chave: DefValuesetChaveResumo | None = None,
        parent=None,
        on_save: Callable[[DefValuesetChaveDialogData], bool] | None = None,
        on_save_as: Callable[[DefValuesetChaveDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.chave = chave
        self.on_save = on_save
        self.on_save_as = on_save_as
        self._is_edit = chave is not None

        self.setWindowTitle("Editar Chave ValueSet" if self._is_edit else "Nova Chave ValueSet")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.codigo_input.setPlaceholderText("Ex.: MATERIAL_PORTAS")
        self.nome_input = QLineEdit()
        self.descricao_input = QLineEdit()

        self.tipo_input = QComboBox()
        for tipo in TIPO_OPCOES:
            self.tipo_input.addItem(tipo, tipo)

        self.grupo_input = QComboBox()
        self.grupo_input.setEditable(True)
        for grupo in GRUPO_OPCOES:
            self.grupo_input.addItem(grupo)
        self.grupo_input.setCurrentText("")

        self.sistema_input = QCheckBox()
        self.ordem_input = QLineEdit()
        self.ordem_input.setText("1")
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.sistema_warning_label = QLabel("")
        self.sistema_warning_label.setObjectName("defValuesetChaveSystemWarning")
        self.sistema_warning_label.setStyleSheet("color: #8a6d00;")
        self.sistema_warning_label.setWordWrap(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("defValuesetChaveError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Tipo", self.tipo_input)
        form.addRow("Grupo", self.grupo_input)
        form.addRow("Sistema", self.sistema_input)
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Observações", self.observacoes_input)
        form.addRow("Ativo", self.ativo_input)

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
        self.button_box.accepted.connect(self._validate_and_accept)
        self.save_as_button.clicked.connect(self._validate_and_save_as)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.sistema_warning_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if chave is not None:
            self._load_chave(chave)

    def _load_chave(self, chave: DefValuesetChaveResumo) -> None:
        """Populate the form with an existing ValueSet key."""
        self.codigo_input.setText(chave.codigo)
        self.nome_input.setText(chave.nome)
        self.descricao_input.setText(chave.descricao or "")
        self._select_tipo(chave.tipo)
        self.grupo_input.setCurrentText(chave.grupo or "")
        self.sistema_input.setChecked(chave.sistema)
        self.ordem_input.setText(str(chave.ordem))
        self.observacoes_input.setText(chave.observacoes or "")
        self.ativo_input.setChecked(chave.ativo)

        if chave.sistema:
            self.sistema_warning_label.setText(
                "Esta é uma chave de sistema. Edite apenas se tiver certeza."
            )

    def _select_tipo(self, tipo: str | None) -> None:
        index = self.tipo_input.findData(tipo)
        if index < 0:
            self.tipo_input.insertItem(0, tipo or "(sem tipo)", tipo)
            index = 0
        self.tipo_input.setCurrentIndex(index)

    def get_data(self) -> DefValuesetChaveDialogData:
        """Return dialog data (raises ValueError on invalid order)."""
        return DefValuesetChaveDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.text()),
            tipo=self.tipo_input.currentData(),
            grupo=self._empty_to_none(self.grupo_input.currentText()),
            sistema=self.sistema_input.isChecked(),
            ordem=self._parse_ordem(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
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
        callback: Callable[[DefValuesetChaveDialogData], bool] | None,
    ) -> None:
        """Run validation, then delegate to the requested save callback."""
        if not self.codigo_input.text().strip():
            self.set_error("O código é obrigatório.")
            return

        if not self.nome_input.text().strip():
            self.set_error("O nome é obrigatório.")
            return

        try:
            data = self.get_data()
        except ValueError as error:
            self.set_error(str(error))
            return

        self.error_label.clear()
        if callback is not None and not callback(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _parse_ordem(self) -> int:
        text = self.ordem_input.text().strip()
        if not text:
            return 1

        try:
            return int(text)
        except ValueError as error:
            raise ValueError("Ordem inválida. Use um número inteiro.") from error

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
