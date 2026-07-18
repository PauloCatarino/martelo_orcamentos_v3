"""Dialog to edit a saved module's HEADER (phase 8U.3).

Only the header is editable here (the structural lines come from the costing).
The code is fixed; name/description/category/scope/image can change. Validation
runs on save via ``on_save`` (returns False to keep the dialog open with the
data preserved).
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
    get_modulo_categoria_label,
    normalize_modulo_ambito,
    normalize_modulo_categoria,
)
from app.ui.helpers.modulo_categoria_opcoes import (
    carregar_arvore_categorias,
    carregar_opcoes_categorias,
)


@dataclass(frozen=True)
class EditarModuloDialogData:
    """Header data collected by the edit-module dialog (code is fixed)."""

    nome: str
    descricao: str | None
    ambito: str
    categoria: str
    imagem_path: str | None
    subcategoria: str | None = None


class EditarModuloDialog(QDialog):
    """Modal dialog to edit a reusable module's header."""

    def __init__(
        self,
        parent=None,
        *,
        codigo: str,
        dados: EditarModuloDialogData,
        on_save: Callable[[EditarModuloDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save

        self.setWindowTitle(f"Editar Módulo {codigo}")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.codigo_input = QLineEdit(codigo)
        self.codigo_input.setReadOnly(True)
        self.codigo_input.setToolTip(
            "O código é fixo (as linhas do módulo vêm do custeio)."
        )

        self.nome_input = QLineEdit(dados.nome or "")

        self.descricao_input = QPlainTextEdit(dados.descricao or "")
        self.descricao_input.setMinimumHeight(50)

        self.ambito_input = QComboBox()
        self.ambito_input.addItem("Utilizador (só meu)", AMBITO_UTILIZADOR)
        self.ambito_input.addItem("Global (todos)", AMBITO_GLOBAL)
        self._selecionar(self.ambito_input, normalize_modulo_ambito(dados.ambito))

        # Subcategories available per top-level category.
        self._arvore_subcategorias = carregar_arvore_categorias()

        self.categoria_input = QComboBox()
        for code, label in carregar_opcoes_categorias():
            self.categoria_input.addItem(label, code)
        categoria_atual = normalize_modulo_categoria(dados.categoria)
        if self.categoria_input.findData(categoria_atual) < 0:
            # Archived/legacy category: keep it selectable on this module.
            self.categoria_input.addItem(
                get_modulo_categoria_label(categoria_atual), categoria_atual
            )
        self._selecionar(self.categoria_input, categoria_atual)

        self.subcategoria_input = QComboBox()
        self.subcategoria_input.setToolTip(
            "Subcategoria (opcional) dentro da categoria escolhida. Geridas na "
            "Biblioteca de Módulos › Gerir Categorias."
        )
        self._recarregar_subcategorias(
            categoria_atual,
            selecionar=(
                normalize_modulo_categoria(dados.subcategoria)
                if dados.subcategoria
                else None
            ),
        )
        self.categoria_input.currentIndexChanged.connect(
            lambda _=0: self._recarregar_subcategorias(
                self.categoria_input.currentData()
            )
        )

        self.imagem_input = QLineEdit(dados.imagem_path or "")
        self.imagem_input.setPlaceholderText("(opcional) caminho da imagem")
        self.procurar_button = QPushButton("Procurar...")
        self.procurar_button.clicked.connect(self._procurar_imagem)
        imagem_row = QWidget()
        imagem_layout = QHBoxLayout()
        imagem_layout.setContentsMargins(0, 0, 0, 0)
        imagem_layout.addWidget(self.imagem_input, stretch=1)
        imagem_layout.addWidget(self.procurar_button)
        imagem_row.setLayout(imagem_layout)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Código", self.codigo_input)
        form.addRow("Nome", self.nome_input)
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Âmbito", self.ambito_input)
        form.addRow("Categoria", self.categoria_input)
        form.addRow("Subcategoria", self.subcategoria_input)
        form.addRow("Imagem", imagem_row)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Cancelar"
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
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

    @staticmethod
    def _selecionar(combo: QComboBox, code: str) -> None:
        index = combo.findData(code)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _recarregar_subcategorias(
        self, categoria_codigo: str | None, selecionar: str | None = None
    ) -> None:
        """Rebuild the subcategory picker for the chosen top-level category."""
        if selecionar is None:
            selecionar = self.subcategoria_input.currentData()
        self.subcategoria_input.blockSignals(True)
        self.subcategoria_input.clear()
        self.subcategoria_input.addItem("— Nenhuma —", None)
        for code, label in self._arvore_subcategorias.get(categoria_codigo or "", ()):
            self.subcategoria_input.addItem(label, code)
        indice = self.subcategoria_input.findData(selecionar)
        self.subcategoria_input.setCurrentIndex(indice if indice >= 0 else 0)
        self.subcategoria_input.blockSignals(False)

    def get_data(self) -> EditarModuloDialogData:
        """Return the edited header data."""
        descricao = self.descricao_input.toPlainText().strip()
        imagem = self.imagem_input.text().strip()
        return EditarModuloDialogData(
            nome=self.nome_input.text().strip(),
            descricao=descricao or None,
            ambito=self.ambito_input.currentData() or AMBITO_UTILIZADOR,
            categoria=self.categoria_input.currentData() or OUTROS,
            imagem_path=imagem or None,
            subcategoria=self.subcategoria_input.currentData(),
        )

    def set_error(self, message: str) -> None:
        """Show an error while keeping the dialog open and the data filled."""
        self.error_label.setText(message)

    def _validate_and_accept(self) -> None:
        """Require a name, then delegate to on_save (keeps data on failure)."""
        data = self.get_data()
        if not data.nome:
            self.error_label.setText("O nome é obrigatório.")
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()
