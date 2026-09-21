"""Gráfico dos últimos meses de trabalho de uma pessoa (Assistente dos Orçamentos).

Uma coluna por mês: a altura são os orçamentos criados, a parte cheia os que já
foram adjudicados. Desenhado à mão (QPainter) para ficar nas cores do Martelo e
não trazer bibliotecas de gráficos para dentro de um diálogo pequeno.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.domain.mensagens_orcamentos import MesDeTrabalho
from app.ui import tema


class GraficoMeses(QWidget):
    ALTURA = 150
    ESPACO = 10
    ALTURA_ROTULO = 34

    def __init__(self, meses: tuple[MesDeTrabalho, ...] = (), parent=None) -> None:
        super().__init__(parent)
        self.meses = tuple(meses)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(self.ALTURA)
        self.setToolTip(
            "Orçamentos que criou em cada mês (coluna) e quantos desses já foram "
            "adjudicados (parte cheia). Inclui o Arquivo V2."
        )

    def definir(self, meses: tuple[MesDeTrabalho, ...]) -> None:
        self.meses = tuple(meses)
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - nome do Qt
        return QSize(max(len(self.meses), 1) * 80, self.ALTURA)

    def paintEvent(self, _event) -> None:  # noqa: N802 - nome do Qt
        if not self.meses:
            return
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        maximo = max((mes.criados for mes in self.meses), default=0)
        largura_coluna = (self.width() - self.ESPACO) / len(self.meses) - self.ESPACO
        largura_coluna = max(largura_coluna, 12)
        altura_util = self.height() - self.ALTURA_ROTULO - 18
        fonte = QFont(self.font())
        pequena = QFont(fonte)
        pequena.setPointSizeF(max(fonte.pointSizeF() - 1, 6.0))

        for indice, mes in enumerate(self.meses):
            x = self.ESPACO + indice * (largura_coluna + self.ESPACO)
            altura = altura_util * (mes.criados / maximo) if maximo else 0
            topo = 18 + altura_util - altura
            coluna = QRectF(x, topo, largura_coluna, altura)
            pintor.setPen(QColor(tema.CINZA_CASTANHO))
            pintor.setBrush(QColor(tema.BEGE_AREIA))
            pintor.drawRoundedRect(coluna, 3, 3)
            if mes.criados:
                fundo, _ = tema.cor_estado("Adjudicado")
                altura_ganhos = altura * (mes.ganhos / mes.criados)
                ganhos = QRectF(
                    x, topo + altura - altura_ganhos, largura_coluna, altura_ganhos
                )
                pintor.setBrush(QColor(fundo))
                pintor.drawRoundedRect(ganhos, 3, 3)

            pintor.setPen(QColor(tema.TEXTO_NORMAL))
            pintor.setFont(pequena)
            pintor.drawText(
                QRectF(x, 0, largura_coluna, 16),
                Qt.AlignmentFlag.AlignCenter,
                str(mes.criados),
            )
            pintor.drawText(
                QRectF(x, self.height() - self.ALTURA_ROTULO, largura_coluna, 16),
                Qt.AlignmentFlag.AlignCenter,
                mes.rotulo,
            )
            negrito = QFont(pequena)
            negrito.setBold(True)
            pintor.setFont(negrito)
            pintor.setPen(QColor(tema.VERDE_ESCURO))
            pintor.drawText(
                QRectF(x, self.height() - self.ALTURA_ROTULO + 16, largura_coluna, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"{mes.ganhos} ganhos",
            )
        pintor.end()
