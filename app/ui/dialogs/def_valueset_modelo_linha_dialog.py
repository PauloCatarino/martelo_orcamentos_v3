"""Dialog for creating and editing a ValueSet model line."""

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

from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.ui.helpers.valueset_combo_helper import (
    carregar_chaves_valueset_combo,
    obter_valor_chave_combo,
)


@dataclass(frozen=True)
class DefValuesetModeloLinhaDialogData:
    """Data collected by the ValueSet model line dialog."""

    chave: str | None
    codigo_opcao: str
    nome_opcao: str
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    valor_texto: str | None
    padrao: bool
    ordem: int
    observacoes: str | None
    ativo: bool


class DefValuesetModeloLinhaDialog(QDialog):
    """Modal dialog for creating or editing a ValueSet model line."""

    def __init__(
        self,
        linha: DefValuesetModeloLinhaResumo | None = None,
        parent=None,
        on_save: Callable[[DefValuesetModeloLinhaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.linha = linha
        self.on_save = on_save
        self._is_edit = linha is not None

        self.setWindowTitle(
            "Editar Linha do Modelo" if self._is_edit else "Nova Linha do Modelo"
        )
        self.setModal(True)
        self.setMinimumWidth(480)

        self.chave_input = QComboBox()
        carregar_chaves_valueset_combo(
            self.chave_input,
            valor_atual=linha.chave if linha is not None else None,
        )

        self.codigo_opcao_input = QLineEdit()
        self.codigo_opcao_input.setPlaceholderText("Ex.: AGL_19_STANDARD")
        self.nome_opcao_input = QLineEdit()
        self.ref_materia_prima_input = QLineEdit()
        self.descricao_materia_prima_input = QLineEdit()
        self.valor_texto_input = QLineEdit()
        self.valor_texto_input.setPlaceholderText("Ex.: Aglomerado 19mm standard")
        self.padrao_input = QCheckBox()
        self.ordem_input = QLineEdit()
        self.ordem_input.setText("1")
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("defValuesetModeloLinhaError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Chave ValueSet", self.chave_input)
        form.addRow("Código opção", self.codigo_opcao_input)
        form.addRow("Nome opção", self.nome_opcao_input)
        form.addRow("Ref. matéria-prima", self.ref_materia_prima_input)
        form.addRow("Descrição matéria-prima", self.descricao_materia_prima_input)
        form.addRow("Valor texto", self.valor_texto_input)
        form.addRow("Padrão", self.padrao_input)
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Observações", self.observacoes_input)
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

        if linha is not None:
            self._load_linha(linha)

    def _load_linha(self, linha: DefValuesetModeloLinhaResumo) -> None:
        """Populate the form with an existing model line."""
        self.codigo_opcao_input.setText(linha.codigo_opcao or "")
        self.nome_opcao_input.setText(linha.nome_opcao or "")
        self.ref_materia_prima_input.setText(linha.ref_materia_prima or "")
        self.descricao_materia_prima_input.setText(linha.descricao_materia_prima or "")
        self.valor_texto_input.setText(linha.valor_texto or "")
        self.padrao_input.setChecked(linha.padrao)
        self.ordem_input.setText(str(linha.ordem))
        self.observacoes_input.setText(linha.observacoes or "")
        self.ativo_input.setChecked(linha.ativo)

    def get_data(self) -> DefValuesetModeloLinhaDialogData:
        """Return dialog data (raises ValueError on invalid order)."""
        return DefValuesetModeloLinhaDialogData(
            chave=obter_valor_chave_combo(self.chave_input),
            codigo_opcao=self.codigo_opcao_input.text().strip(),
            nome_opcao=self.nome_opcao_input.text().strip(),
            ref_materia_prima=self._empty_to_none(self.ref_materia_prima_input.text()),
            descricao_materia_prima=self._empty_to_none(
                self.descricao_materia_prima_input.text()
            ),
            valor_texto=self._empty_to_none(self.valor_texto_input.text()),
            padrao=self.padrao_input.isChecked(),
            ordem=self._parse_ordem(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        if obter_valor_chave_combo(self.chave_input) is None:
            self.set_error("Selecione uma chave ValueSet.")
            return

        if not self.codigo_opcao_input.text().strip():
            self.set_error("O código da opção é obrigatório.")
            return

        if not self.nome_opcao_input.text().strip():
            self.set_error("O nome da opção é obrigatório.")
            return

        try:
            data = self.get_data()
        except ValueError as error:
            self.set_error(str(error))
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
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
