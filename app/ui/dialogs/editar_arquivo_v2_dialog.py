"""Controlled editor for one shared V2 budget header."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.domain.orcamento_estados import ESTADOS_ORCAMENTO
from app.services.v2_arquivo_service import OrcamentoV2Resumo
from app.utils.formatters import format_currency


@dataclass(frozen=True)
class EditarArquivoV2Data:
    estado: str
    enc_phc: str | None
    total: Decimal | None


class EditarArquivoV2Dialog(QDialog):
    """Edit state and ENC PHC, with a guarded manual-price field."""

    def __init__(self, item: OrcamentoV2Resumo, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar orçamento V2")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.contexto_label = QLabel(
            f"Orçamento {item.numero} · versão {item.versao} · {item.cliente}"
        )
        self.contexto_label.setStyleSheet("font-weight: bold;")

        self.estado_combo = QComboBox()
        self.estado_combo.addItems(list(ESTADOS_ORCAMENTO))
        if item.estado and self.estado_combo.findText(item.estado) < 0:
            self.estado_combo.addItem(item.estado)
        self.estado_combo.setCurrentText(item.estado)

        self.enc_phc_input = QLineEdit(item.enc_phc or "")
        self.enc_phc_input.setPlaceholderText("Número da encomenda PHC")

        self.origem_label = QLabel(self._texto_origem(item))
        self.origem_label.setWordWrap(True)

        self.preco_input = QLineEdit(self._texto_preco(item.total))
        self.preco_input.setPlaceholderText("0,00")
        self.preco_input.setEnabled(item.preco_editavel)
        if item.preco_editavel:
            self.preco_input.setToolTip(
                "Preço manual: pode ser alterado e fica gravado na base partilhada."
            )
        else:
            self.preco_input.setToolTip(
                "Preço protegido: é calculado pelos items/custeio e deve ser alterado no V2."
            )

        self.aviso_label = QLabel(self._texto_aviso(item))
        self.aviso_label.setWordWrap(True)
        self.aviso_label.setStyleSheet(f"color: {tema.TEXTO_AVISO}; padding: 6px 0;")

        self.erro_label = QLabel("")
        self.erro_label.setWordWrap(True)
        self.erro_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")

        form = QFormLayout()
        form.addRow("Estado", self.estado_combo)
        form.addRow("Enc. PHC", self.enc_phc_input)
        form.addRow("Origem do preço", self.origem_label)
        form.addRow("Preço total", self.preco_input)

        self.botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.botoes.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.botoes.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.botoes.accepted.connect(self._validar_e_aceitar)
        self.botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.contexto_label)
        layout.addLayout(form)
        layout.addWidget(self.aviso_label)
        layout.addWidget(self.erro_label)
        layout.addWidget(self.botoes)

    def get_data(self) -> EditarArquivoV2Data:
        """Return normalized form values."""
        return EditarArquivoV2Data(
            estado=self.estado_combo.currentText().strip(),
            enc_phc=self._empty_to_none(self.enc_phc_input.text()),
            total=self._ler_preco(),
        )

    def _validar_e_aceitar(self) -> None:
        try:
            self._ler_preco()
        except ValueError as error:
            self.erro_label.setText(str(error))
            return
        self.accept()

    def _ler_preco(self) -> Decimal | None:
        texto = self.preco_input.text().strip()
        if not texto:
            return None
        try:
            valor = Decimal(texto.replace("€", "").replace(" ", "").replace(",", "."))
        except (InvalidOperation, ValueError):
            raise ValueError("O preço deve ser um valor numérico válido.") from None
        if valor < 0:
            raise ValueError("O preço não pode ser negativo.")
        return valor.quantize(Decimal("0.01"))

    @staticmethod
    def _texto_origem(item: OrcamentoV2Resumo) -> str:
        if item.origem_preco == "manual":
            return "Manual / fonte externa — editável no V3 durante a transição."
        if item.origem_preco == "custeio":
            return "Custeio / items do orçamento — protegido no V3."
        return "Desconhecida — preço protegido até a origem ser confirmada no V2."

    @staticmethod
    def _texto_aviso(item: OrcamentoV2Resumo) -> str:
        if item.origem_preco == "manual":
            return "As alterações são gravadas diretamente na base de dados partilhada com o V2."
        return (
            "O preço final não pode ser alterado aqui porque pode ser resultado do custeio. "
            "Abra o orçamento no V2, altere os items e deixe o V2 recalcular o total."
        )

    @staticmethod
    def _texto_preco(valor) -> str:
        return format_currency(valor).replace(" €", "") if valor is not None else ""

    @staticmethod
    def _empty_to_none(valor: str) -> str | None:
        valor = valor.strip()
        return valor or None
