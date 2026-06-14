"""Dialog to save selected costing lines as a reusable module (phase 8U.1).

Named GuardarModuloDialog to avoid clashing with the unrelated legacy
NovoModuloDialog (the per-item modules page).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    OUTROS,
    get_modulo_categoria_options,
)


@dataclass(frozen=True)
class GuardarModuloDialogData:
    """Data collected by the save-as-module dialog."""

    codigo: str
    nome: str
    descricao: str | None
    ambito: str
    categoria: str
    imagem_path: str | None


class GuardarModuloDialog(QDialog):
    """Modal dialog to create a reusable module from costing lines.

    Validation runs on save via ``on_save`` (returns False to keep the dialog
    open with the data preserved, e.g. duplicate code / missing fields).
    """

    def __init__(
        self,
        parent=None,
        *,
        on_save: Callable[[GuardarModuloDialogData], bool] | None = None,
        num_linhas: int = 0,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save

        self.setWindowTitle("Guardar como Módulo")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.codigo_input = QLineEdit()
        self.codigo_input.setToolTip("Código único do módulo (ex.: ROUPEIRO_2P).")
        self.nome_input = QLineEdit()

        self.descricao_input = QPlainTextEdit()
        self.descricao_input.setMinimumHeight(50)

        self.ambito_input = QComboBox()
        self.ambito_input.addItem("Utilizador (só meu)", AMBITO_UTILIZADOR)
        self.ambito_input.addItem("Global (todos)", AMBITO_GLOBAL)

        self.categoria_input = QComboBox()
        for code, label in get_modulo_categoria_options():
            self.categoria_input.addItem(label, code)
        self._selecionar_categoria(OUTROS)

        self.imagem_input = QLineEdit()
        self.imagem_input.setPlaceholderText("(opcional) caminho da imagem")
        self.procurar_button = QPushButton("Procurar...")
        self.procurar_button.clicked.connect(self._procurar_imagem)
        imagem_row = QWidget()
        imagem_layout = QHBoxLayout()
        imagem_layout.setContentsMargins(0, 0, 0, 0)
        imagem_layout.addWidget(self.imagem_input, stretch=1)
        imagem_layout.addWidget(self.procurar_button)
        imagem_row.setLayout(imagem_layout)

        info = QLabel(
            f"Vai guardar {num_linhas} linha(s) de topo como um módulo "
            "reutilizável (só a estrutura — sem material/preço)."
        )
        info.setWordWrap(True)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Âmbito", self.ambito_input)
        form.addRow("Categoria", self.categoria_input)
        form.addRow("Imagem", imagem_row)

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

    def _procurar_imagem(self) -> None:
        """Pick an image file path (only the path is stored in this phase)."""
        caminho, _filtro = QFileDialog.getOpenFileName(
            self,
            "Escolher imagem do módulo",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.gif);;Todos os ficheiros (*)",
        )
        if caminho:
            self.imagem_input.setText(caminho)

    def _selecionar_categoria(self, code: str) -> None:
        index = self.categoria_input.findData(code)
        if index >= 0:
            self.categoria_input.setCurrentIndex(index)

    def get_data(self) -> GuardarModuloDialogData:
        """Return the dialog data."""
        descricao = self.descricao_input.toPlainText().strip()
        imagem = self.imagem_input.text().strip()
        return GuardarModuloDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=descricao or None,
            ambito=self.ambito_input.currentData() or AMBITO_UTILIZADOR,
            categoria=self.categoria_input.currentData() or OUTROS,
            imagem_path=imagem or None,
        )

    def set_error(self, message: str) -> None:
        """Show an error while keeping the dialog open and the data filled."""
        self.error_label.setText(message)

    def _validate_and_accept(self) -> None:
        """Require code/name, then delegate to on_save (keeps data on failure)."""
        data = self.get_data()
        if not data.codigo:
            self.error_label.setText("O código é obrigatório.")
            return
        if not data.nome:
            self.error_label.setText("O nome é obrigatório.")
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()
