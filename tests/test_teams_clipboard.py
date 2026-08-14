"""Inline image preparation for Microsoft Teams tickets."""

from __future__ import annotations

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.ui.helpers.teams_clipboard import copiar_fotos_inline, preparar_imagem_inline


def _foto(caminho, largura: int, altura: int, cor: str) -> str:
    imagem = QImage(largura, altura, QImage.Format.Format_RGB32)
    imagem.fill(QColor(cor))
    assert imagem.save(str(caminho))
    return str(caminho)


def test_uma_foto_fica_como_imagem_e_nao_url_de_ficheiro(tmp_path) -> None:
    caminho = _foto(tmp_path / "obra.png", 320, 180, "#8B6F4E")

    imagem, total = preparar_imagem_inline([caminho])

    assert total == 1
    assert imagem is not None
    assert imagem.width() == 320
    assert imagem.height() == 180


def test_varias_fotos_formam_uma_composicao_unica(tmp_path) -> None:
    caminhos = [
        _foto(tmp_path / "a.png", 400, 300, "#8B6F4E"),
        _foto(tmp_path / "b.png", 300, 400, "#EFE7DA"),
        _foto(tmp_path / "c.png", 500, 250, "#315C35"),
    ]

    imagem, total = preparar_imagem_inline(caminhos)

    assert total == 3
    assert imagem is not None
    assert imagem.width() > 500
    assert imagem.height() > 400


def test_ficheiros_invalidos_sao_ignorados(tmp_path) -> None:
    valido = _foto(tmp_path / "valido.png", 120, 90, "#FFFFFF")

    imagem, total = preparar_imagem_inline([str(tmp_path / "falta.png"), valido])

    assert total == 1
    assert imagem is not None


def test_clipboard_recebe_imagem_inline_e_nao_url_de_anexo(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    caminho = _foto(tmp_path / "ticket.png", 200, 120, "#8B6F4E")

    assert copiar_fotos_inline([caminho]) == 1

    dados = app.clipboard().mimeData()
    assert dados is not None
    assert dados.hasImage()
    assert not dados.hasUrls()
