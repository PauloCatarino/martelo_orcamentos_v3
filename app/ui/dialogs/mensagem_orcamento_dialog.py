"""Mensagem do Assistente quando um orçamento passa a Adjudicado/Não Adjudicado."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.domain import mensagens_orcamentos as regra
from app.ui import tema


class GraficoEstados(QWidget):
    """Barras horizontais: quantos orçamentos do cliente em cada estado."""

    ALTURA_BARRA = 22
    ESPACO = 6
    LARGURA_ROTULO = 130

    def __init__(self, contagem: dict[str, int], parent=None) -> None:
        super().__init__(parent)
        self.contagem = {e: n for e, n in contagem.items() if n}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(self._altura())
        self.setToolTip(
            "Orçamentos deste cliente por estado (Martelo V3 + Arquivo V2). "
            "Cada orçamento conta uma vez: ganho, se alguma versão foi adjudicada."
        )

    def _altura(self) -> int:
        linhas = max(len(self.contagem), 1)
        return linhas * (self.ALTURA_BARRA + self.ESPACO) + self.ESPACO

    def sizeHint(self) -> QSize:  # noqa: N802 - nome do Qt
        return QSize(420, self._altura())

    def paintEvent(self, _event) -> None:  # noqa: N802 - nome do Qt
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        maximo = max(self.contagem.values(), default=0)
        largura_util = max(self.width() - self.LARGURA_ROTULO - 60, 20)
        y = self.ESPACO
        fonte = QFont(self.font())
        for estado, quantos in self.contagem.items():
            fundo, texto = tema.cor_estado(estado)
            pintor.setPen(QColor(tema.TEXTO_NORMAL))
            pintor.setFont(fonte)
            pintor.drawText(
                QRectF(0, y, self.LARGURA_ROTULO - 8, self.ALTURA_BARRA),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                estado,
            )
            largura = largura_util * quantos / maximo if maximo else 0
            barra = QRectF(self.LARGURA_ROTULO, y + 2, max(largura, 3), self.ALTURA_BARRA - 4)
            pintor.setPen(QColor(texto))
            pintor.setBrush(QColor(fundo))
            pintor.drawRoundedRect(barra, 3, 3)
            negrito = QFont(fonte)
            negrito.setBold(True)
            pintor.setFont(negrito)
            pintor.drawText(
                QRectF(barra.right() + 6, y, 54, self.ALTURA_BARRA),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(quantos),
            )
            y += self.ALTURA_BARRA + self.ESPACO
        pintor.end()


class MensagemOrcamentoDialog(QDialog):
    def __init__(self, mensagem: regra.Mensagem, parent=None) -> None:
        super().__init__(parent)
        self.mensagem = mensagem
        self.setWindowTitle("Assistente dos Orçamentos")
        self.setMinimumWidth(620)
        ganho = mensagem.estado == regra.ADJUDICADO

        titulo = QLabel(mensagem.titulo)
        cor = tema.VERDE_ESCURO if ganho else tema.CASTANHO_ESCURO
        titulo.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {cor};")
        self.frase = QLabel(mensagem.frase)
        self.frase.setWordWrap(True)
        self.frase.setStyleSheet("font-size: 14px;")
        self.destaque = QLabel(mensagem.destaque)
        self.destaque.setWordWrap(True)
        self.destaque.setStyleSheet("font-size: 14px; font-weight: 600;")

        factos = QLabel("\n".join(f"• {facto}" for facto in mensagem.factos))
        factos.setWordWrap(True)
        factos.setStyleSheet("color: #5c6570;")

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(self.frase)
        layout.addWidget(self.destaque)
        layout.addSpacing(6)
        layout.addWidget(factos)

        self.grafico: GraficoEstados | None = None
        if mensagem.grafico:
            caixa = QGroupBox(f"Os orçamentos do cliente {mensagem.cliente}")
            caixa_layout = QVBoxLayout(caixa)
            self.grafico = GraficoEstados(mensagem.grafico)
            caixa_layout.addWidget(self.grafico)
            layout.addWidget(caixa)

        fechar = QPushButton("Obrigado!" if ganho else "Fechar")
        fechar.setToolTip("Fechar esta mensagem.")
        fechar.clicked.connect(self.accept)
        fechar.setDefault(True)
        rodape = QHBoxLayout()
        nota = QLabel("Mensagem só para si, do Assistente dos Orçamentos.")
        nota.setStyleSheet("color: #8a8f96; font-size: 11px;")
        rodape.addWidget(nota, 1)
        rodape.addWidget(fechar)
        layout.addLayout(rodape)
        self.adjustSize()
