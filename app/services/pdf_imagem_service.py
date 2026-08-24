"""Desenhar páginas de PDF sem deixar o ficheiro preso.

O QPdfDocument mantém o PDF aberto enquanto o objeto viver — e no Windows um
ficheiro aberto não se consegue apagar. Era isso que fazia aparecer "o ficheiro
está aberto em Python" ao tentar apagar, na pasta da obra, o plano de corte
acabado de gerar a partir do CUT-RITE: bastava a pré-visualização do Martelo ter
passado por ele. Aqui lemos os bytes primeiro e desenhamos a partir da memória,
por isso o Qt nunca chega a abrir o ficheiro.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def documento_pdf(caminho: Path | str) -> Iterator[object]:
    """Yield a QPdfDocument read from memory (the file is never held open)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtPdf import QPdfDocument

    # `dados` tem de ficar vivo enquanto o buffer for lido: é ele que guarda o
    # PDF em memória.
    dados = QByteArray(Path(caminho).read_bytes())
    buffer = QBuffer(dados)
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    documento = QPdfDocument()
    try:
        documento.load(buffer)
        yield documento
    finally:
        documento.close()
        buffer.close()


#: Miniaturas já desenhadas, por (caminho, data de alteração, tamanho, alvo).
#: O mesmo PDF é pedido de cada vez que se muda de ticket; desenhar a página
#: outra vez seria ir buscar o ficheiro à rede sem necessidade. Se o ficheiro
#: mudar no disco, a chave muda e a miniatura é refeita.
_MINIATURAS: dict[tuple, object] = {}
_MINIATURAS_MAXIMO = 64


def miniatura_primeira_pagina(caminho: Path | str, largura: int, altura: int):
    """Return the first page of a PDF as a QPixmap that fits (largura, altura).

    Devolve ``None`` quando não há como desenhar (ficheiro que desapareceu, PDF
    estragado, sem páginas). Uma miniatura é sempre acessória: nunca levanta
    exceção nem impede o ecrã de abrir.
    """
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QPixmap

    try:
        ficheiro = Path(caminho)
        estado = ficheiro.stat()
    except OSError:
        return None

    chave = (str(ficheiro), estado.st_mtime_ns, estado.st_size, largura, altura)
    if chave in _MINIATURAS:
        return _MINIATURAS[chave]

    miniatura = None
    try:
        with documento_pdf(ficheiro) as documento:
            if documento.pageCount() > 0:
                pagina = documento.pagePointSize(0)
                if pagina.width() > 0 and pagina.height() > 0:
                    escala = min(
                        largura / pagina.width(), altura / pagina.height()
                    )
                    imagem = documento.render(
                        0,
                        QSize(
                            max(1, int(pagina.width() * escala)),
                            max(1, int(pagina.height() * escala)),
                        ),
                    )
                    if not imagem.isNull():
                        miniatura = QPixmap.fromImage(imagem)
    except Exception:  # noqa: BLE001 - sem miniatura não é erro
        miniatura = None

    if len(_MINIATURAS) >= _MINIATURAS_MAXIMO:
        _MINIATURAS.clear()
    _MINIATURAS[chave] = miniatura
    return miniatura
