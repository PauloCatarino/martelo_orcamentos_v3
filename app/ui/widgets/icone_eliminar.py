"""Ícone "X" de eliminar, desenhado pelo Qt em vez de escrito com um caracter.

O X flutuante do custeio era o caracter ``✕``. Quando a letra nao existe na
fonte do Windows, o botao aparece vazio — fica so' a bola vermelha a` volta,
que e' o que se via no ecra. Desenhado com duas linhas, o X aparece sempre
igual, em qualquer PC e em qualquer tamanho.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


#: Vermelho do botao de eliminar (o mesmo do contorno) e o X sobre fundo cheio.
COR_X_NORMAL = "#B52C25"
COR_X_REALCE = "#FFFFFF"


def pixmap_x(cor: str, tamanho: int = 12, espessura: float = 1.8) -> QPixmap:
    """Desenhar um X de ``tamanho`` pontos na cor pedida.

    Desenha-se ao dobro da resolucao (``devicePixelRatio`` 2) para o X nao sair
    esborratado nos ecras com escala.
    """
    ratio = 2.0
    pixmap = QPixmap(int(tamanho * ratio), int(tamanho * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        caneta = QPen(QColor(cor), espessura)
        caneta.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(caneta)

        margem = 2.5
        fim = tamanho - margem
        painter.drawLine(QPointF(margem, margem), QPointF(fim, fim))
        painter.drawLine(QPointF(fim, margem), QPointF(margem, fim))
    finally:
        painter.end()

    return pixmap


def icone_x_eliminar(cor: str = COR_X_NORMAL, tamanho: int = 12) -> QIcon:
    """Ícone X na cor pedida.

    Sao precisos dois: o vermelho para o botao em repouso e o branco para
    quando o fundo fica vermelho cheio. Quem usa o botao troca-os no
    ``Enter``/``Leave`` — os modos do ``QIcon`` nao servem aqui, porque o Qt so'
    passa a "Active" quando o botao tem o foco, e este nao o recebe.
    """
    return QIcon(pixmap_x(cor, tamanho))
