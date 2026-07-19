"""Dialog for creating/editing a configurable quantity rule (phase 8T.5.0)."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.domain.regras_quantidade_expr import avaliar_regra_quantidade

TOOLTIP_EXPRESSAO = (
    "Expressão que calcula a quantidade a partir das dimensões da peça "
    "principal.\n"
    "Variáveis: COMP, LARG, ESP (mm) e QT_PAI (quantidade da peça principal).\n"
    "Operadores: + - * / // (divisão inteira), comparações (< <= > >= == !=), "
    "and / or / not e o condicional «A if COND else B».\n"
    "Funções: CEIL(x), FLOOR(x), MIN(a, b, ...), MAX(a, b, ...).\n"
    "O resultado é arredondado para cima e nunca é negativo.\n"
    "Ex.: CEIL(COMP / 600)  •  2 if COMP <= 850 else 3"
)


@dataclass(frozen=True)
class RegraQuantidadeDialogData:
    """Data collected by the quantity-rule dialog."""

    codigo: str
    nome: str
    expressao: str
    descricao: str | None
    ativo: bool


class RegraQuantidadeDialog(QDialog):
    """Modal dialog to define a rule, with an inline expression tester."""

    def __init__(
        self,
        parent=None,
        *,
        titulo: str,
        dados: RegraQuantidadeDialogData | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(560)

        self.codigo_input = QLineEdit()
        self.codigo_input.setToolTip("Código único da regra (ex.: DOBRADICA).")
        self.nome_input = QLineEdit()

        self.expressao_input = QPlainTextEdit()
        self.expressao_input.setToolTip(TOOLTIP_EXPRESSAO)
        self.expressao_input.setMinimumHeight(70)

        self.descricao_input = QPlainTextEdit()
        self.descricao_input.setToolTip(
            "Descrição da regra (serve de tooltip onde a regra for usada)."
        )
        self.descricao_input.setMinimumHeight(50)

        self.ativo_check = QCheckBox("Ativo")
        self.ativo_check.setChecked(True)

        if dados is not None:
            self.codigo_input.setText(dados.codigo)
            # The code is the identity of the rule: fixed in edit mode.
            self.codigo_input.setEnabled(False)
            self.nome_input.setText(dados.nome)
            self.expressao_input.setPlainText(dados.expressao)
            self.descricao_input.setPlainText(dados.descricao or "")
            self.ativo_check.setChecked(dados.ativo)

        info = QLabel(TOOLTIP_EXPRESSAO)
        info.setWordWrap(True)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Código", self.codigo_input)
        form_layout.addRow("Nome", self.nome_input)
        form_layout.addRow("Expressão", self.expressao_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("", self.ativo_check)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form_layout)
        layout.addWidget(self._criar_zona_teste())
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def _criar_zona_teste(self) -> QGroupBox:
        """Build the 'Testar' area (COMP/LARG/ESP/QT_PAI + result)."""
        self.teste_comp = self._criar_spin(2000)
        self.teste_larg = self._criar_spin(600)
        self.teste_esp = self._criar_spin(19)
        self.teste_qt_pai = self._criar_spin(1)

        valores_layout = QFormLayout()
        valores_layout.addRow("COMP (mm)", self.teste_comp)
        valores_layout.addRow("LARG (mm)", self.teste_larg)
        valores_layout.addRow("ESP (mm)", self.teste_esp)
        valores_layout.addRow("QT_PAI", self.teste_qt_pai)

        self.testar_button = QPushButton("Testar")
        self.testar_button.setToolTip(
            "Avalia a expressão com os valores acima (não guarda)."
        )
        self.testar_button.clicked.connect(self._testar)

        self.resultado_label = QLabel("Resultado: —")

        botoes_layout = QHBoxLayout()
        botoes_layout.addWidget(self.testar_button)
        botoes_layout.addWidget(self.resultado_label, stretch=1)

        grupo_layout = QVBoxLayout()
        grupo_layout.addLayout(valores_layout)
        grupo_layout.addLayout(botoes_layout)

        grupo = QGroupBox("Testar expressão")
        grupo.setLayout(grupo_layout)
        return grupo

    def _testar(self) -> None:
        """Evaluate the current expression with the tester values."""
        contexto = {
            "COMP": Decimal(str(self.teste_comp.value())),
            "LARG": Decimal(str(self.teste_larg.value())),
            "ESP": Decimal(str(self.teste_esp.value())),
            "QT_PAI": Decimal(str(self.teste_qt_pai.value())),
        }
        quantidade, motivo = avaliar_regra_quantidade(
            self.expressao_input.toPlainText(), contexto
        )
        if motivo is not None:
            self.resultado_label.setText(f"Erro: {motivo}")
            return

        self.resultado_label.setText(f"Resultado: {quantidade}")

    def get_data(self) -> RegraQuantidadeDialogData:
        """Return the dialog data."""
        descricao = self.descricao_input.toPlainText().strip()
        return RegraQuantidadeDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            expressao=self.expressao_input.toPlainText().strip(),
            descricao=descricao or None,
            ativo=self.ativo_check.isChecked(),
        )

    @staticmethod
    def _criar_spin(valor_inicial: int) -> QDoubleSpinBox:
        """Build one tester dimension field (mm / quantity)."""
        spin = QDoubleSpinBox()
        spin.setDecimals(0)
        spin.setRange(0, 100000)
        spin.setValue(valor_inicial)
        return spin

    def _validate_and_accept(self) -> None:
        """Require code/name and a valid expression before accepting."""
        dados = self.get_data()
        if not dados.codigo:
            self.error_label.setText("O código é obrigatório.")
            return
        if not dados.nome:
            self.error_label.setText("O nome é obrigatório.")
            return
        if not dados.expressao:
            self.error_label.setText("A expressão é obrigatória.")
            return

        _quantidade, motivo = avaliar_regra_quantidade(dados.expressao)
        if motivo is not None:
            self.error_label.setText(f"Expressão inválida: {motivo}")
            return

        self.accept()
