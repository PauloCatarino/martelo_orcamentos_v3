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
