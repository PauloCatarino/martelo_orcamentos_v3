"""Caixa do corpo do email que aceita imagens coladas com Ctrl+V.

Um QTextEdit normal recusa uma imagem vinda da área de transferência: quem
carrega em Ctrl+V depois de um print de ecrã não recebe erro nenhum, não
acontece nada, e fica sem saber porquê.

A imagem é gravada num ficheiro temporário e entra no corpo como
``<img src="file:///...">``. Não é um pormenor: é exatamente a forma que o
``email_service._extrair_imagens_inline`` procura para trocar por ``cid:`` e
anexar a imagem ao email como inline. Uma imagem colada de qualquer outra
maneira (recurso do documento, data URI) aparecia bem na janela e chegava ao
cliente como um quadrado vazio.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QTextEdit

#: Acima disto a imagem é reduzida antes de entrar no email. Um print de ecrã
#: de um monitor grande, ou uma foto de telemóvel, ia com vários MB e alguns
#: servidores recusam o email por causa do peso.
LARGURA_MAXIMA = 1200

#: Largura com que a imagem é DESENHADA no email. A imagem vai inteira; isto é
#: só para não rebentar a largura da mensagem em quem a lê.
LARGURA_APRESENTADA = 620

EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class CorpoEmailEdit(QTextEdit):
    """Corpo do email em rich text, com Ctrl+V de imagens."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptRichText(True)
        self._pasta_temporaria: Path | None = None

    # --- colar ------------------------------------------------------------

    def canInsertFromMimeData(self, source: QMimeData) -> bool:  # noqa: N802
        if source.hasImage() or self._primeiro_ficheiro_imagem(source):
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData) -> None:  # noqa: N802
        caminho = self._guardar_imagem(source)
        if caminho is not None:
            self.inserir_imagem(caminho)
            return
        super().insertFromMimeData(source)

    def inserir_imagem(self, caminho: Path | str) -> None:
        """Escrever a imagem no corpo, no sítio onde está o cursor."""
        url = QUrl.fromLocalFile(str(caminho)).toString()
        self.textCursor().insertHtml(
            f'<img src="{url}" width="{LARGURA_APRESENTADA}"><br>'
        )

    # --- ajudantes --------------------------------------------------------

    def _guardar_imagem(self, source: QMimeData) -> Path | None:
        """Gravar a imagem da área de transferência num ficheiro temporário."""
        imagem: QImage | None = None
        if source.hasImage():
            candidata = source.imageData()
            if isinstance(candidata, QImage) and not candidata.isNull():
                imagem = candidata

        if imagem is None:
            ficheiro = self._primeiro_ficheiro_imagem(source)
            if ficheiro is None:
                return None
            candidata = QImage(str(ficheiro))
            if candidata.isNull():
                return None
            imagem = candidata

        if imagem.width() > LARGURA_MAXIMA:
            imagem = imagem.scaledToWidth(
                LARGURA_MAXIMA, Qt.TransformationMode.SmoothTransformation
            )

        destino = self._pasta() / f"colada_{uuid.uuid4().hex[:8]}.png"
        if not imagem.save(str(destino), "PNG"):
            return None
        return destino

    @staticmethod
    def _primeiro_ficheiro_imagem(source: QMimeData) -> Path | None:
        """Caminho da primeira imagem, quando o que se cola são ficheiros."""
        if not source.hasUrls():
            return None
        for url in source.urls():
            if not url.isLocalFile():
                continue
            caminho = Path(url.toLocalFile())
            if caminho.suffix.lower() in EXTENSOES_IMAGEM and caminho.is_file():
                return caminho
        return None

    def _pasta(self) -> Path:
        """Pasta temporária desta janela; os ficheiros vivem até o email sair."""
        if self._pasta_temporaria is None:
            self._pasta_temporaria = Path(
                tempfile.mkdtemp(prefix="martelo_email_")
            )
        return self._pasta_temporaria
