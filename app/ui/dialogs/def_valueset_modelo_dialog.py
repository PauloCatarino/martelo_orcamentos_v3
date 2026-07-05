"""Dialog for creating and editing a ValueSet model (library entry)."""

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

from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo

TIPO_OPCOES = ("ROUPEIRO", "COZINHA", "MOVEL_WC", "GERAL", "OUTRO")
AMBITO_OPCOES = ("UTILIZADOR", "GLOBAL")


@dataclass(frozen=True)
class DefValuesetModeloDialogData:
    """Data collected by the ValueSet model dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    ambito: str
    visivel_para_todos: bool
    observacoes: str | None
    ativo: bool


class DefValuesetModeloDialog(QDialog):
    """Modal dialog for creating or editing a ValueSet model."""

    def __init__(
        self,
        modelo: DefValuesetModeloResumo | None = None,
        parent=None,
        on_save: Callable[[DefValuesetModeloDialogData], bool] | None = None,
        on_save_as: Callable[[DefValuesetModeloDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.modelo = modelo
        self.on_save = on_save
        self.on_save_as = on_save_as
        self._is_edit = modelo is not None

        self.setWindowTitle("Editar Modelo ValueSet" if self._is_edit else "Novo Modelo ValueSet")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.codigo_input = QLineEdit()
        self.codigo_input.setPlaceholderText("Ex.: ROUPEIRO_STANDARD")
        self.nome_input = QLineEdit()
        self.descricao_input = QLineEdit()

        self.tipo_input = QComboBox()
        self.tipo_input.setEditable(True)
        for tipo in TIPO_OPCOES:
            self.tipo_input.addItem(tipo)
        self.tipo_input.setCurrentText("")

        self.ambito_input = QComboBox()
        for ambito in AMBITO_OPCOES:
            self.ambito_input.addItem(ambito, ambito)
        self.ambito_input.currentTextChanged.connect(self._on_ambito_changed)

        self.visivel_input = QCheckBox()
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("defValuesetModeloError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Tipo", self.tipo_input)
        form.addRow("Âmbito", self.ambito_input)
        form.addRow("Visível para todos", self.visivel_input)
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
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if modelo is not None:
            self._load_modelo(modelo)

    def _load_modelo(self, modelo: DefValuesetModeloResumo) -> None:
        """Populate the form with an existing model."""
        self.codigo_input.setText(modelo.codigo)
        self.nome_input.setText(modelo.nome)
        self.descricao_input.setText(modelo.descricao or "")
        self.tipo_input.setCurrentText(modelo.tipo or "")
        index = self.ambito_input.findData(modelo.ambito)
        self.ambito_input.setCurrentIndex(index if index >= 0 else 0)
        self.visivel_input.setChecked(modelo.visivel_para_todos)
        self.observacoes_input.setText(modelo.observacoes or "")
        self.ativo_input.setChecked(modelo.ativo)

    def _on_ambito_changed(self, _text: str) -> None:
        """Default 'visivel para todos' from the chosen scope."""
        self.visivel_input.setChecked(self.ambito_input.currentData() == "GLOBAL")

    def get_data(self) -> DefValuesetModeloDialogData:
        """Return dialog data."""
        return DefValuesetModeloDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.text()),
            tipo=self._empty_to_none(self.tipo_input.currentText()),
            ambito=self.ambito_input.currentData() or "UTILIZADOR",
            visivel_para_todos=self.visivel_input.isChecked(),
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
        callback: Callable[[DefValuesetModeloDialogData], bool] | None,
    ) -> None:
        """Run validation, then delegate to the requested save callback."""
        if not self.codigo_input.text().strip():
            self.set_error("O código é obrigatório.")
            return

        if not self.nome_input.text().strip():
            self.set_error("O nome é obrigatório.")
            return

        self.error_label.clear()
        data = self.get_data()
        if callback is not None and not callback(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
