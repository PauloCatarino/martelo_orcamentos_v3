"""O X de eliminar e desenhado, nao depende da fonte do sistema."""

from __future__ import annotations

import inspect
import sys

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _cores(pixmap) -> set[tuple[int, int, int]]:
    """Cores opacas presentes na imagem."""
    imagem = pixmap.toImage()
    encontradas = set()
    for x in range(imagem.width()):
        for y in range(imagem.height()):
            cor = imagem.pixelColor(x, y)
            if cor.alpha() > 200:
                encontradas.add((cor.red(), cor.green(), cor.blue()))
    return encontradas


def test_desenha_mesmo_um_x(_app) -> None:
    from app.ui.widgets.icone_eliminar import COR_X_NORMAL, pixmap_x

    pixmap = pixmap_x(COR_X_NORMAL, tamanho=12)

    # Ao dobro da resolucao, para nao sair esborratado nos ecras com escala.
    assert pixmap.devicePixelRatio() == 2.0
    assert (pixmap.width(), pixmap.height()) == (24, 24)

    imagem = pixmap.toImage()
    # As duas diagonais passam pelos cantos e cruzam-se no meio; as esquinas
    # a meio dos lados ficam vazias — e isso que distingue um X de uma bola.
    assert imagem.pixelColor(12, 12).alpha() > 0
    assert imagem.pixelColor(6, 6).alpha() > 0
    assert imagem.pixelColor(18, 6).alpha() > 0
    assert imagem.pixelColor(12, 1).alpha() == 0
    assert imagem.pixelColor(1, 12).alpha() == 0


def test_a_cor_pedida_e_a_cor_desenhada(_app) -> None:
    from app.ui.widgets.icone_eliminar import COR_X_NORMAL, COR_X_REALCE, pixmap_x

    assert (181, 44, 37) in _cores(pixmap_x(COR_X_NORMAL))
    assert (255, 255, 255) in _cores(pixmap_x(COR_X_REALCE))


def test_o_icone_nao_vem_vazio(_app) -> None:
    from app.ui.widgets.icone_eliminar import icone_x_eliminar

    icone = icone_x_eliminar()

    assert icone.isNull() is False
    assert icone.availableSizes()


def test_o_custeio_usa_o_icone_e_nao_o_caracter() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    fonte = inspect.getsource(
        OrcamentoItemCusteioPage._instalar_botao_apagar_ferragem
    )

    assert "icone_x_eliminar" in fonte
    # O caracter deixou de ser o conteudo do botao.
    assert 'QPushButton("✕"' not in fonte
    # Sem isto, o padding do estilo global esmagava o botao numa elipse.
    assert "padding: 0px" in fonte
    assert "min-height: 0px" in fonte
    assert "border-radius: 4px" in fonte


def test_o_x_fica_branco_com_o_rato_em_cima() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    fonte = inspect.getsource(OrcamentoItemCusteioPage.eventFilter)

    assert "_icone_x_realce" in fonte
    assert "_icone_x_normal" in fonte
