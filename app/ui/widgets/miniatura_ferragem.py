"""Small representative pictograms for hardware lines in costing."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap


PUXADOR = "PUXADOR"
DOBRADICA = "DOBRADICA"
CORREDICA = "CORREDICA"
PE = "PE"

FERRAGEM_VISUAL_LABELS = {
    PUXADOR: "Puxador",
    DOBRADICA: "Dobradiça",
    CORREDICA: "Corrediça",
    PE: "Pé nivelador",
}

_COR_PREENCHIMENTO = QColor("#D96C5F")
_COR_CONTORNO = QColor("#8A3E36")
_COR_DETALHE = QColor("#5A302B")


def resolver_ferragem_visual(*valores: object) -> str | None:
    """Resolve a conservative pictogram from structured hardware identifiers.

    Values should be passed from most structured to least structured (ValueSet
    key, piece code, line code, description).  The exclusions prevent generic
    accessories whose name merely mentions a pull from being shown as a pull.
    """
    for valor in valores:
        texto = _normalizar_identificador(valor)
        if not texto:
            continue
        if "DOBRADICA" in texto:
            return DOBRADICA
        if "CORREDICA" in texto:
            return CORREDICA
        if _eh_pe_nivelador(texto):
            return PE
        if "PUXADOR" in texto and not any(
            termo in texto for termo in ("ESQUADRO", "PERFIL", "TERMINAL")
        ):
            return PUXADOR
    return None


def criar_miniatura_ferragem(tipo: str, tamanho: int = 28) -> QPixmap:
    """Draw one hardware pictogram with the same palette as structural icons."""
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    escala = tamanho / 28
    painter.scale(escala, escala)
    painter.setBrush(_COR_PREENCHIMENTO)
    painter.setPen(QPen(_COR_CONTORNO, max(1.2, 1.35 / escala)))

    if tipo == PUXADOR:
        _desenhar_puxador(painter)
    elif tipo == DOBRADICA:
        _desenhar_dobradica(painter)
    elif tipo == CORREDICA:
        _desenhar_corredica(painter)
    elif tipo == PE:
        _desenhar_pe(painter)

    painter.end()
    return pixmap


def _desenhar_puxador(painter: QPainter) -> None:
    caminho = QPainterPath(QPointF(10.5, 4.5))
    caminho.cubicTo(4.2, 4.5, 3.7, 23.5, 10.5, 23.5)
    caminho.cubicTo(13.4, 23.5, 14.4, 20.0, 14.8, 17.5)
    caminho.lineTo(24.0, 17.5)
    caminho.lineTo(24.0, 10.5)
    caminho.lineTo(14.8, 10.5)
    caminho.cubicTo(14.4, 8.0, 13.4, 4.5, 10.5, 4.5)
    caminho.closeSubpath()
    painter.drawPath(caminho)


def _desenhar_dobradica(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(2.5, 5.0, 12.5, 18.0))
    painter.drawRoundedRect(QRectF(12.0, 10.0, 9.5, 8.0), 1.5, 1.5)
    painter.drawRoundedRect(QRectF(20.0, 5.5, 5.5, 17.0), 1.2, 1.2)
    painter.setBrush(_COR_DETALHE)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(14.7, 12.2, 2.2, 2.2))
    painter.drawEllipse(QRectF(21.8, 8.0, 1.8, 1.8))
    painter.drawEllipse(QRectF(21.8, 18.2, 1.8, 1.8))


def _desenhar_corredica(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(2.5, 11.0, 22.5, 8.5), 1.0, 1.0)
    painter.drawRoundedRect(QRectF(2.5, 7.5, 18.0, 7.0), 1.0, 1.0)
    painter.drawRoundedRect(QRectF(19.5, 9.5, 6.0, 5.0), 0.8, 0.8)
    painter.setBrush(_COR_DETALHE)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(21.5, 15.5, 1.8, 2.8), 0.7, 0.7)


def _desenhar_pe(painter: QPainter) -> None:
    # Three bands are enough to suggest the threaded stem at 28 px.
    painter.drawRoundedRect(QRectF(11.5, 3.0, 5.0, 9.0), 1.0, 1.0)
    painter.setPen(QPen(_COR_DETALHE, 1.0))
    for y in (5.0, 7.0, 9.0):
        painter.drawLine(QPointF(11.8, y), QPointF(16.2, y))
    painter.setPen(QPen(_COR_CONTORNO, 1.35))
    painter.drawRoundedRect(QRectF(8.5, 10.5, 11.0, 10.0), 2.0, 2.0)
    painter.drawRoundedRect(QRectF(5.0, 19.0, 18.0, 5.0), 2.0, 2.0)


def _eh_pe_nivelador(texto: str) -> bool:
    return (
        "PE_NIVELADOR" in texto
        or texto in {"PE", "PES", "FERRAGEM_PES"}
        or texto.startswith("PES_")
    )


def _normalizar_identificador(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")
