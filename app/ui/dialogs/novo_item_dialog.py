"""Dialog for creating a simple budget item."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.item_types import OUTRO, get_item_type_options, normalize_item_type


@dataclass(frozen=True)
class NovoItemDialogData:
    """Data collected by the new item dialog."""

    codigo: str | None
    item: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal
    unidade: str
    preco_unitario: Decimal
    tipo_item: str = "OUTRO"
    preco_manual: bool = False


class NovoItemDialog(QDialog):
    """Simple modal dialog for creating a budget item."""

    def __init__(self, parent=None, item_data: NovoItemDialogData | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Editar Item" if item_data is not None else "Novo Item")
        self.setModal(True)
        self.setMinimumSize(560, 620)

        self.codigo_input = QLineEdit()
        self.tipo_item_input = QComboBox()
        for code, label in get_item_type_options():
            self.tipo_item_input.addItem(label, code)
        self.item_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setMinimumHeight(140)
        self.descricoes_button = QPushButton("Descrições pré-definidas…")
        self.descricoes_button.clicked.connect(self._abrir_descricoes_predefinidas)
        descricao_widget = QWidget()
        descricao_layout = QVBoxLayout(descricao_widget)
        descricao_layout.setContentsMargins(0, 0, 0, 0)
        descricao_layout.addWidget(self.descricao_input)
        descricao_botao_row = QHBoxLayout()
        descricao_botao_row.addStretch()
        descricao_botao_row.addWidget(self.descricoes_button)
        descricao_layout.addLayout(descricao_botao_row)
        self.altura_input = QLineEdit()
        self.largura_input = QLineEdit()
        self.profundidade_input = QLineEdit()
        self.quantidade_input = QLineEdit("1")
        self.unidade_input = QLineEdit("un")
        self.preco_unitario_input = QLineEdit("0")
        self.preco_manual_check = QCheckBox(
            "Preço manual (não recalcular a partir do custeio)"
        )

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoItemError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("C\u00f3digo", self.codigo_input)
        form_layout.addRow("Tipo de item", self.tipo_item_input)
        form_layout.addRow("Item", self.item_input)
        form_layout.addRow("Descri\u00e7\u00e3o", descricao_widget)
        form_layout.addRow("Altura", self.altura_input)
        form_layout.addRow("Largura", self.largura_input)
        form_layout.addRow("Profundidade", self.profundidade_input)
        form_layout.addRow("Quantidade", self.quantidade_input)
        form_layout.addRow("Unidade", self.unidade_input)
        preco_widget = QWidget()
        preco_layout = QHBoxLayout(preco_widget)
        preco_layout.setContentsMargins(0, 0, 0, 0)
        preco_layout.addWidget(self.preco_unitario_input)
        preco_layout.addWidget(QLabel("€"))
        form_layout.addRow("Pre\u00e7o unit\u00e1rio", preco_widget)
        form_layout.addRow("", self.preco_manual_check)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if item_data is not None:
            self._fill_from_data(item_data)

    def get_data(self) -> NovoItemDialogData:
        """Return normalized dialog data."""
        return NovoItemDialogData(
            codigo=self._empty_to_none(self.codigo_input.text()),
            item=self.item_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            altura=self._parse_optional_decimal(self.altura_input.text()),
            largura=self._parse_optional_decimal(self.largura_input.text()),
            profundidade=self._parse_optional_decimal(self.profundidade_input.text()),
            quantidade=self._parse_decimal(self.quantidade_input.text()),
            unidade=self.unidade_input.text().strip() or "un",
            preco_unitario=self._parse_decimal(self.preco_unitario_input.text()),
            tipo_item=self.tipo_item_input.currentData() or OUTRO,
            preco_manual=self.preco_manual_check.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        try:
            data = self.get_data()
        except ValueError as error:
            self.error_label.setText(str(error))
            return

        if not data.item:
            self.error_label.setText("O item e obrigatorio.")
            return

        if data.quantidade <= 0:
            self.error_label.setText("A quantidade deve ser maior que 0.")
            return

        self.accept()

    def _parse_optional_decimal(self, value: str) -> Decimal | None:
        """Parse an optional decimal text value."""
        if not value.strip():
            return None

        return self._parse_decimal(value)

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse a decimal accepting comma or dot separators."""
        normalized = value.replace("€", "").replace(" ", "").strip().replace(",", ".")
        if not normalized:
            raise ValueError("Preencha os valores numericos obrigatorios.")

        try:
            numero = Decimal(normalized)
            if not numero.is_finite():
                raise ValueError("Valores numericos invalidos.")
            return numero
        except InvalidOperation as error:
            raise ValueError("Valores numericos invalidos.") from error

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None

    def _fill_from_data(self, item_data: NovoItemDialogData) -> None:
        """Fill dialog fields from existing item data."""
        self.codigo_input.setText(item_data.codigo or "")
        self._set_tipo_item(item_data.tipo_item)
        self.item_input.setText(item_data.item)
        self.descricao_input.setPlainText(item_data.descricao or "")
        self.altura_input.setText(self._format_dimensao(item_data.altura))
        self.largura_input.setText(self._format_dimensao(item_data.largura))
        self.profundidade_input.setText(self._format_dimensao(item_data.profundidade))
        self.quantidade_input.setText(self._format_dimensao(item_data.quantidade))
        self.unidade_input.setText(item_data.unidade)
        self.preco_unitario_input.setText(self._format_preco(item_data.preco_unitario))
        self.preco_manual_check.setChecked(item_data.preco_manual)

    def _format_dimensao(self, value: Decimal | None) -> str:
        """Dimensão/quantidade: até 1 casa decimal, sem '.0' nos inteiros (vírgula em PT)."""
        if value is None:
            return ""
        arredondado = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if arredondado == arredondado.to_integral_value():
            return f"{arredondado:.0f}"
        return f"{arredondado:.1f}".replace(".", ",")

    def _format_preco(self, value: Decimal | None) -> str:
        """Preço unitário: 2 casas decimais com vírgula (PT). O símbolo € fica no rótulo ao lado."""
        if value is None:
            return ""

        return f"{value:.2f}".replace(".", ",")

    def _set_tipo_item(self, value: str | None) -> None:
        """Select an item type in the combo box."""
        tipo_item = normalize_item_type(value)
        index = self.tipo_item_input.findData(tipo_item)
        if index >= 0:
            self.tipo_item_input.setCurrentIndex(index)

    def _abrir_descricoes_predefinidas(self) -> None:
        from app.core.session import app_session
        from app.ui.dialogs.descricoes_predefinidas_dialog import (
            DescricoesPredefinidasDialog,
        )

        user = app_session.current_user
        user_id = user.id if user is not None else None
        if user_id is None:
            self.error_label.setText("Utilizador não identificado.")
            return
        dialog = DescricoesPredefinidasDialog(self, user_id=user_id)
        if not dialog.exec():
            return
        self._inserir_descricoes(dialog.checked_entries())

    def _inserir_descricoes(self, entries) -> None:
        linhas = []
        for entry in entries:
            texto = (entry.texto or "").strip()
            if not texto:
                continue
            tipo = entry.tipo if entry.tipo in ("-", "*") else "-"
            linhas.append(f"\t{tipo} {texto}")
        if not linhas:
            return
        cursor = self.descricao_input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        existente = self.descricao_input.toPlainText()
        if existente.strip() and not existente.endswith("\n"):
            cursor.insertText("\n")
        cursor.insertText("\n".join(linhas))
        self.descricao_input.setTextCursor(cursor)
