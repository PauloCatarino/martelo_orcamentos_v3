"""Ctrl+V de uma imagem no corpo do email.

Um QTextEdit normal recusa a imagem sem dizer nada: carrega-se em Ctrl+V
depois de um print de ecrã e não acontece coisa nenhuma.

A forma como a imagem entra no corpo não é indiferente. Tem de ser
``<img src="file:///...">``, porque é isso que o ``email_service`` procura para
a trocar por ``cid:`` e a anexar como inline. De qualquer outra maneira ficava
bonita na janela e chegava ao cliente como um quadrado vazio.
"""

from __future__ import annotations

import re

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMimeData, QUrl  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.services.email_service import _extrair_imagens_inline  # noqa: E402
from app.ui.widgets.corpo_email_edit import (  # noqa: E402
    LARGURA_MAXIMA,
    CorpoEmailEdit,
)


@pytest.fixture(scope="module")
def app():
    yield QApplication.instance() or QApplication([])


def _imagem(largura: int = 200, altura: int = 120) -> QImage:
    imagem = QImage(largura, altura, QImage.Format.Format_RGB32)
    imagem.fill(0x336699)
    return imagem


def _com_imagem(imagem: QImage) -> QMimeData:
    dados = QMimeData()
    dados.setImageData(imagem)
    return dados


def test_aceita_uma_imagem_da_area_de_transferencia(app) -> None:
    caixa = CorpoEmailEdit()

    assert caixa.canInsertFromMimeData(_com_imagem(_imagem())) is True


def test_a_imagem_colada_entra_como_ficheiro_local(app) -> None:
    caixa = CorpoEmailEdit()
    caixa.setHtml("<p>Bom dia,</p>")

    caixa.insertFromMimeData(_com_imagem(_imagem()))

    origens = re.findall(r'src="(file:[^"]+)"', caixa.toHtml())
    assert len(origens) == 1
    assert QUrl(origens[0]).toLocalFile().endswith(".png")


def test_o_email_troca_a_imagem_colada_por_uma_inline(app) -> None:
    """É este o encaixe que interessa: o corpo tem de sair pronto para o Outlook."""
    caixa = CorpoEmailEdit()
    caixa.insertFromMimeData(_com_imagem(_imagem()))

    corpo, inline = _extrair_imagens_inline(caixa.toHtml())

    assert len(inline) == 1
    cid, caminho = inline[0]
    assert caminho.endswith(".png")
    assert f'src="cid:{cid}"' in corpo


def test_uma_imagem_enorme_e_reduzida_antes_de_ir(app) -> None:
    """Um print de um monitor grande ia com vários MB e fazia recusar o email."""
    caixa = CorpoEmailEdit()

    caixa.insertFromMimeData(_com_imagem(_imagem(4000, 2200)))

    origem = re.findall(r'src="(file:[^"]+)"', caixa.toHtml())[0]
    gravada = QImage(QUrl(origem).toLocalFile())
    assert gravada.width() == LARGURA_MAXIMA


def test_texto_normal_continua_a_colar_como_dantes(app) -> None:
    caixa = CorpoEmailEdit()
    dados = QMimeData()
    dados.setText("um texto qualquer")

    caixa.insertFromMimeData(dados)

    assert "um texto qualquer" in caixa.toPlainText()
    assert 'src="file:' not in caixa.toHtml()
