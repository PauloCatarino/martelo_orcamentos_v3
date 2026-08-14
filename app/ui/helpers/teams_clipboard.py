"""Prepare ticket photographs for inline pasting in Microsoft Teams."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter
from PySide6.QtWidgets import QApplication


_LIMITE_UNICA = QSize(1800, 1400)
_LIMITE_CELULA = QSize(900, 700)
_MARGEM = 16
_ESPACO = 16


def copiar_fotos_inline(caminhos: Iterable[str]) -> int:
    """Copy existing readable photos as one clipboard image.

    A single photograph keeps its aspect ratio. Multiple photographs become a
    white contact sheet so Teams inserts all of them inline with one Ctrl+V.
    Returns the number of source photographs included.
    """
    imagem, total = preparar_imagem_inline(caminhos)
    if imagem is None or total == 0:
        return 0

    app = QApplication.instance()
    if app is None:
        raise RuntimeError("A aplicação gráfica não está disponível.")
    app.clipboard().setImage(imagem)
    return total


def preparar_imagem_inline(caminhos: Iterable[str]) -> tuple[QImage | None, int]:
    """Load and compose photographs without touching the clipboard."""
    imagens = [_ler_imagem(caminho) for caminho in caminhos]
    imagens = [imagem for imagem in imagens if imagem is not None]
    if not imagens:
        return None, 0

    if len(imagens) == 1:
        imagem = imagens[0]
        if (
            imagem.width() > _LIMITE_UNICA.width()
            or imagem.height() > _LIMITE_UNICA.height()
        ):
            imagem = imagem.scaled(
                _LIMITE_UNICA,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return _sobre_branco(imagem), 1

    reduzidas = [
        imagem.scaled(
            _LIMITE_CELULA,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        for imagem in imagens
    ]
    linhas = [
        reduzidas[indice : indice + 2]
        for indice in range(0, len(reduzidas), 2)
    ]
    larguras = [
        sum(img.width() for img in linha) + _ESPACO * (len(linha) - 1)
        for linha in linhas
    ]
    alturas = [max(img.height() for img in linha) for linha in linhas]
    largura = max(larguras) + 2 * _MARGEM
    altura = sum(alturas) + _ESPACO * (len(linhas) - 1) + 2 * _MARGEM

    mosaico = QImage(largura, altura, QImage.Format.Format_RGB32)
    mosaico.fill(QColor("#FFFFFF"))
    painter = QPainter(mosaico)
    y = _MARGEM
    for linha, largura_linha, altura_linha in zip(linhas, larguras, alturas):
        x = (largura - largura_linha) // 2
        for imagem in linha:
            painter.drawImage(x, y + (altura_linha - imagem.height()) // 2, imagem)
            x += imagem.width() + _ESPACO
        y += altura_linha + _ESPACO
    painter.end()
    return mosaico, len(imagens)


def _ler_imagem(caminho: str) -> QImage | None:
    reader = QImageReader(str(caminho or ""))
    reader.setAutoTransform(True)
    imagem = reader.read()
    return None if imagem.isNull() else imagem


def _sobre_branco(imagem: QImage) -> QImage:
    resultado = QImage(imagem.size(), QImage.Format.Format_RGB32)
    resultado.fill(QColor("#FFFFFF"))
    painter = QPainter(resultado)
    painter.drawImage(0, 0, imagem)
    painter.end()
    return resultado
