"""Representação visual das orlas aplicadas aos quatro lados de uma peça."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.domain.orla_types import (
    ORLA_FINA,
    ORLA_GROSSA,
    SEM_ORLA,
    get_orla_type_label,
    normalize_orla_type,
)
from app.ui import tema


@dataclass(frozen=True)
class OrlaVisualStyle:
    """Aspeto de uma orla no esquema da peça."""

    cor: str
    espessura: float
    tracejada: bool = False


_ORLA_VISUAL_STYLES = {
    SEM_ORLA: OrlaVisualStyle("#AAA6A1", 2.0, tracejada=True),
    ORLA_FINA: OrlaVisualStyle(tema.CASTANHO_MEDIO, 3.5),
    ORLA_GROSSA: OrlaVisualStyle(tema.CASTANHO_ESCURO, 7.0),
}


def get_orla_visual_style(valor: int | str | None) -> OrlaVisualStyle:
    """Devolve o estilo gráfico do tipo de orla normalizado."""
    return _ORLA_VISUAL_STYLES[normalize_orla_type(valor)]


class OrlaPecaPreview(QWidget):
    """Esquema dinâmico da peça, com C1/C2/L1/L2 e respetivas orlas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._orlas = (SEM_ORLA, SEM_ORLA, SEM_ORLA, SEM_ORLA)
        self._usa_orlas = True

        self.setObjectName("orlaPecaPreview")
        self.setMinimumSize(225, 235)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAccessibleName("Representação das orlas da peça")
        self.setToolTip(
            "Vista superior da peça. C1 e C2 são os lados do comprimento; "
            "L1 e L2 são os lados da largura."
        )

    @property
    def orlas(self) -> tuple[int, int, int, int]:
        """Valores normalizados na ordem C1, C2, L1 e L2."""
        return self._orlas

    @property
    def usa_orlas(self) -> bool:
        """Indica se a peça está configurada para trabalhar com orlas."""
        return self._usa_orlas

    def set_orlas(
        self,
        c1: int | str | None,
        c2: int | str | None,
        l1: int | str | None,
        l2: int | str | None,
    ) -> None:
        """Atualiza os quatro lados representados no esquema."""
        valores = tuple(normalize_orla_type(valor) for valor in (c1, c2, l1, l2))
        if valores != self._orlas:
            self._orlas = valores
            self.update()

    def set_usa_orlas(self, usa_orlas: bool) -> None:
        """Mostra o estado neutro quando a peça não trabalha com orlas."""
        usa_orlas = bool(usa_orlas)
        if usa_orlas != self._usa_orlas:
            self._usa_orlas = usa_orlas
            self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - nome definido pelo Qt
        return QSize(285, 250)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Desenha o cartão, a peça, as quatro arestas e a legenda."""
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        fundo = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(tema.CINZA_CASTANHO), 1.0))
        painter.setBrush(QColor("#FCFBF9"))
        painter.drawRoundedRect(fundo, 6.0, 6.0)

        self._desenhar_titulo(painter)
        peca = self._rect_peca()
        painter.setPen(QPen(QColor("#B8AEA4"), 1.0))
        painter.setBrush(QColor("#F1EDE7"))
        painter.drawRect(peca)

        valores = self._orlas if self._usa_orlas else (SEM_ORLA,) * 4
        c1, c2, l1, l2 = valores
        self._desenhar_aresta(painter, peca.bottomLeft(), peca.bottomRight(), c1)
        self._desenhar_aresta(painter, peca.topLeft(), peca.topRight(), c2)
        self._desenhar_aresta(painter, peca.topLeft(), peca.bottomLeft(), l1)
        self._desenhar_aresta(painter, peca.topRight(), peca.bottomRight(), l2)

        self._desenhar_rotulos(painter, peca, valores)
        self._desenhar_legenda(painter)
        painter.end()

    def _rect_peca(self) -> QRectF:
        margem_lateral = max(48.0, min(70.0, self.width() * 0.22))
        largura = max(120.0, self.width() - 2.0 * margem_lateral)
        topo = 62.0
        fundo = max(topo + 82.0, self.height() - 72.0)
        return QRectF((self.width() - largura) / 2.0, topo, largura, fundo - topo)

    def _desenhar_titulo(self, painter: QPainter) -> None:
        fonte = painter.font()
        fonte.setBold(True)
        painter.setFont(fonte)
        painter.setPen(QColor(tema.CASTANHO_ESCURO))
        painter.drawText(
            QRectF(12.0, 8.0, self.width() - 24.0, 22.0),
            int(Qt.AlignmentFlag.AlignCenter),
            "Representação da peça",
        )

        if not self._usa_orlas:
            fonte.setBold(False)
            fonte.setPointSizeF(max(7.5, fonte.pointSizeF() - 1.0))
            painter.setFont(fonte)
            painter.setPen(QColor(tema.CINZA_ESCURO))
            painter.drawText(
                QRectF(12.0, 29.0, self.width() - 24.0, 18.0),
                int(Qt.AlignmentFlag.AlignCenter),
                "A peça não leva orlas",
            )

    def _desenhar_aresta(self, painter: QPainter, inicio, fim, valor: int) -> None:
        estilo = get_orla_visual_style(valor)
        caneta = QPen(QColor(estilo.cor), estilo.espessura)
        caneta.setCapStyle(Qt.PenCapStyle.SquareCap)
        if estilo.tracejada:
            caneta.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(caneta)
        painter.drawLine(inicio, fim)

    def _desenhar_rotulos(
        self,
        painter: QPainter,
        peca: QRectF,
        valores: tuple[int, int, int, int],
    ) -> None:
        c1, c2, l1, l2 = valores
        self._desenhar_rotulo_horizontal(
            painter,
            QRectF(peca.left(), 31.0, peca.width(), 28.0),
            "C2",
            c2,
        )
        self._desenhar_rotulo_horizontal(
            painter,
            QRectF(peca.left(), peca.bottom() + 7.0, peca.width(), 35.0),
            "C1",
            c1,
        )
        self._desenhar_rotulo_lateral(
            painter,
            QRectF(3.0, peca.top(), peca.left() - 8.0, peca.height()),
            "L1",
            l1,
        )
        self._desenhar_rotulo_lateral(
            painter,
            QRectF(peca.right() + 5.0, peca.top(), self.width() - peca.right() - 8.0, peca.height()),
            "L2",
            l2,
        )

    def _desenhar_rotulo_horizontal(
        self,
        painter: QPainter,
        rect: QRectF,
        codigo: str,
        valor: int,
    ) -> None:
        fonte = painter.font()
        fonte.setBold(True)
        painter.setFont(fonte)
        painter.setPen(QColor(tema.TEXTO_NORMAL))
        painter.drawText(
            QRectF(rect.left(), rect.top(), rect.width(), 14.0),
            int(Qt.AlignmentFlag.AlignCenter),
            codigo,
        )

        fonte.setBold(False)
        fonte.setPointSizeF(max(7.5, fonte.pointSizeF() - 1.0))
        painter.setFont(fonte)
        painter.setPen(QColor(get_orla_visual_style(valor).cor))
        painter.drawText(
            QRectF(rect.left(), rect.top() + 13.0, rect.width(), rect.height() - 13.0),
            int(Qt.AlignmentFlag.AlignCenter),
            get_orla_type_label(valor),
        )

    def _desenhar_rotulo_lateral(
        self,
        painter: QPainter,
        rect: QRectF,
        codigo: str,
        valor: int,
    ) -> None:
        centro_y = rect.center().y()
        fonte = painter.font()
        fonte.setBold(True)
        painter.setFont(fonte)
        painter.setPen(QColor(tema.TEXTO_NORMAL))
        painter.drawText(
            QRectF(rect.left(), centro_y - 28.0, rect.width(), 16.0),
            int(Qt.AlignmentFlag.AlignCenter),
            codigo,
        )

        fonte.setBold(False)
        fonte.setPointSizeF(max(7.0, fonte.pointSizeF() - 1.5))
        painter.setFont(fonte)
        painter.setPen(QColor(get_orla_visual_style(valor).cor))
        texto = get_orla_type_label(valor).replace(" ", "\n")
        painter.drawText(
            QRectF(rect.left(), centro_y - 9.0, rect.width(), 38.0),
            int(Qt.AlignmentFlag.AlignCenter),
            texto,
        )

    def _desenhar_legenda(self, painter: QPainter) -> None:
        topo = self.height() - 25.0
        fonte = painter.font()
        fonte.setBold(False)
        fonte.setPointSizeF(max(7.0, fonte.pointSizeF() - 1.0))
        painter.setFont(fonte)

        itens = (
            (ORLA_GROSSA, "Grossa"),
            (ORLA_FINA, "Fina"),
            (SEM_ORLA, "Sem"),
        )
        largura_item = (self.width() - 12.0) / len(itens)
        for indice, (valor, texto) in enumerate(itens):
            esquerda = 6.0 + indice * largura_item
            estilo = get_orla_visual_style(valor)
            caneta = QPen(QColor(estilo.cor), min(estilo.espessura, 5.0))
            if estilo.tracejada:
                caneta.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(caneta)
            painter.drawLine(
                esquerda + 4.0,
                topo + 7.0,
                esquerda + 20.0,
                topo + 7.0,
            )
            painter.setPen(QColor(tema.CINZA_ESCURO))
            painter.drawText(
                QRectF(esquerda + 24.0, topo - 1.0, largura_item - 26.0, 17.0),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                texto,
            )
