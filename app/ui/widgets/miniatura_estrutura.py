"""Small isometric structural previews for costing lines.

The preview is intentionally illustrative: it always uses the same cube and
highlights where a catalog piece belongs.  It is not a dimensional drawing.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import unicodedata

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF

from app.domain.peca_funcao_types import (
    COSTA,
    DIVISORIA,
    FUNDO,
    GAVETA,
    LATERAL,
    PORTA,
    PORTA_CORRER,
    PRATELEIRA_AMOVIVEL,
    PRATELEIRA_FIXA,
    TETO,
    normalize_peca_funcao,
)

_COR_ESTRUTURA = QColor("#D96C5F")
_COR_CONTORNO = QColor("#8A3E36")
_COR_CUBO = QColor("#FFFFFF")
_COR_GUIA = QColor("#C9C0B8")

PUXADOR = "PUXADOR_VISUAL"
GAVETA_FRENTE = "GAVETA_FRENTE"
GAVETA_LATERAL = "GAVETA_LATERAL"
GAVETA_TRASEIRA = "GAVETA_TRASEIRA"
GAVETA_FUNDO = "GAVETA_FUNDO"
_PARTES_GAVETA = frozenset(
    {GAVETA, GAVETA_FRENTE, GAVETA_LATERAL, GAVETA_TRASEIRA, GAVETA_FUNDO}
)

FUNCOES_COM_PREVISAO = frozenset(
    {
        TETO,
        FUNDO,
        PRATELEIRA_FIXA,
        PRATELEIRA_AMOVIVEL,
        LATERAL,
        DIVISORIA,
        COSTA,
        PORTA,
        PORTA_CORRER,
        GAVETA,
    }
)


def tem_previsao_estrutural(funcao: str | None) -> bool:
    """Return whether a structural origin has a cube representation."""
    return (
        normalize_peca_funcao(funcao) in FUNCOES_COM_PREVISAO
        or funcao == PUXADOR
        or funcao in _PARTES_GAVETA
    )


def resolver_funcao_estrutural(
    funcao: str | None, codigo: str | None = None
) -> str | None:
    """Use the configured origin, with a safe visual fallback for legacy pieces."""
    if funcao == PUXADOR or funcao in _PARTES_GAVETA:
        return funcao
    normalizada = normalize_peca_funcao(funcao)
    if normalizada in FUNCOES_COM_PREVISAO:
        return normalizada

    texto = _normalizar_texto(codigo)
    if "PUXADOR" in texto:
        return PUXADOR
    if "GAVETA" in texto:
        if "FRENTE" in texto:
            return GAVETA_FRENTE
        if "LATERAL" in texto or "LADO" in texto:
            return GAVETA_LATERAL
        if "TRASEIRA" in texto or "COSTA" in texto:
            return GAVETA_TRASEIRA
        if "FUNDO" in texto:
            return GAVETA_FUNDO
        return GAVETA
    if "PRATELEIRA" in texto:
        return PRATELEIRA_AMOVIVEL if "AMOV" in texto else PRATELEIRA_FIXA
    for termo, origem in (
        ("DIVISORIA", DIVISORIA),
        ("LATERAL", LATERAL),
        ("COSTA", COSTA),
        ("TETO", TETO),
        ("TOPO", TETO),
        ("FUNDO", FUNDO),
        ("PORTA", PORTA),
        ("FRENTE_GAVETA", GAVETA),
    ):
        if termo in texto:
            return origem
    return None


def criar_miniatura_estrutura(
    funcao: str | None, quantidade, tamanho: int = 28
) -> QPixmap:
    """Draw one fixed-volume cube, highlighting the given structural origin."""
    return criar_miniatura_estrutura_componentes([(funcao, quantidade)], tamanho)


def criar_miniatura_estrutura_componentes(
    componentes: list[tuple[str | None, object]], tamanho: int = 28
) -> QPixmap:
    """Draw a fixed cube with all structural components of a composite piece."""
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    escala = tamanho / 34

    def ponto(x: float, y: float) -> QPointF:
        return QPointF(x * escala, y * escala)

    def poligono(*coordenadas: tuple[float, float]) -> QPolygonF:
        return QPolygonF([ponto(x, y) for x, y in coordenadas])

    def preencher(*coordenadas: tuple[float, float]) -> None:
        painter.setBrush(_COR_ESTRUTURA)
        painter.setPen(QPen(_COR_CONTORNO, max(1, escala)))
        painter.drawPolygon(poligono(*coordenadas))

    componentes_normalizados = [
        (resolver_funcao_estrutural(funcao), quantidade)
        for funcao, quantidade in componentes
    ]
    if any(funcao in _PARTES_GAVETA for funcao, _ in componentes_normalizados):
        _desenhar_gaveta(painter, componentes_normalizados, escala, ponto, poligono)
        painter.end()
        return pixmap

    # A light, transparent-looking fixed cube.
    painter.setBrush(_COR_CUBO)
    painter.setPen(QPen(_COR_GUIA, max(1, escala)))
    painter.drawPolygon(poligono((6, 11), (22, 11), (27, 6), (11, 6)))
    painter.drawPolygon(poligono((6, 11), (11, 6), (11, 22), (6, 27)))
    painter.drawPolygon(poligono((6, 11), (22, 11), (22, 27), (6, 27)))
    painter.drawPolygon(poligono((22, 11), (27, 6), (27, 22), (22, 27)))

    tem_puxador = any(funcao == PUXADOR for funcao, _ in componentes_normalizados)
    portas = 0
    for funcao_normalizada, quantidade in componentes_normalizados:
        quantidade_visual = _quantidade_visual(quantidade)

        if funcao_normalizada == TETO:
            preencher((6, 11), (22, 11), (27, 6), (11, 6))
        elif funcao_normalizada == FUNDO:
            preencher((6, 27), (22, 27), (27, 22), (11, 22))
        elif funcao_normalizada == COSTA:
            preencher((11, 6), (27, 6), (27, 22), (11, 22))
        elif funcao_normalizada == LATERAL:
            preencher((6, 11), (11, 6), (11, 22), (6, 27))
            if quantidade_visual >= 2:
                preencher((22, 11), (27, 6), (27, 22), (22, 27))
        elif funcao_normalizada == DIVISORIA:
            preencher((13.4, 10), (15.6, 8), (15.6, 24), (13.4, 26))
        elif funcao_normalizada in (PRATELEIRA_FIXA, PRATELEIRA_AMOVIVEL):
            preencher((6, 19), (22, 19), (27, 14), (11, 14))
        elif funcao_normalizada in (PORTA, PORTA_CORRER):
            portas = max(portas, quantidade_visual)
            if quantidade_visual >= 2:
                preencher((6, 11), (14, 11), (14, 27), (6, 27))
                preencher((14.4, 11), (22, 11), (22, 27), (14.4, 27))
            else:
                preencher((6, 11), (22, 11), (22, 27), (6, 27))
        elif funcao_normalizada == GAVETA:
            preencher((6, 19), (22, 19), (22, 27), (6, 27))

    if tem_puxador and portas:
        painter.setBrush(QColor("#5A3E2B"))
        painter.setPen(Qt.PenStyle.NoPen)
        for x in ((13, 15) if portas >= 2 else (19,)):
            painter.drawEllipse(ponto(x - 1, 18), 2 * escala, 2 * escala)

    painter.end()
    return pixmap


def _quantidade_visual(quantidade) -> int:
    """Map any business quantity to the 1/2-piece visual convention."""
    try:
        numero = Decimal(str(quantidade))
    except (InvalidOperation, ValueError):
        return 1
    return 2 if numero >= 2 else 1


def _normalizar_texto(texto: str | None) -> str:
    """Normalize a legacy catalog code for a conservative visual fallback."""
    sem_acentos = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in sem_acentos if not unicodedata.combining(c)).upper()


def _desenhar_gaveta(painter, componentes, escala, ponto, poligono) -> None:
    """Draw an open drawer: front, sides, back, bottom and optional pull."""
    partes = {funcao for funcao, _ in componentes}
    tem_puxador = PUXADOR in partes

    def desenhar(parte, *coordenadas) -> None:
        if parte not in partes and GAVETA not in partes:
            return
        painter.setBrush(_COR_ESTRUTURA)
        painter.setPen(QPen(_COR_CONTORNO, max(1, escala)))
        painter.drawPolygon(poligono(*coordenadas))

    # Back and bottom are behind the side/front surfaces.
    desenhar(GAVETA_TRASEIRA, (12, 10), (27, 10), (27, 21), (12, 21))
    desenhar(GAVETA_FUNDO, (7, 25), (22, 25), (27, 21), (12, 21))
    desenhar(GAVETA_LATERAL, (7, 15), (12, 10), (12, 21), (7, 27))
    desenhar(GAVETA_LATERAL, (22, 15), (27, 10), (27, 21), (22, 27))
    desenhar(GAVETA_FRENTE, (7, 15), (22, 15), (22, 27), (7, 27))

    if tem_puxador and (GAVETA_FRENTE in partes or GAVETA in partes):
        painter.setPen(QPen(QColor("#5A3E2B"), max(1, escala * 1.2)))
        painter.drawLine(ponto(12, 21), ponto(17, 21))
