"""A descrição do item aparece inteira na tabela do Relatório de Orçamento.

Vinha cortada com "…" e só se lia passando o rato por cima — o que impedia
conferir de relance se a descrição estava completa antes de enviar ao cliente.
"""

from __future__ import annotations

from decimal import Decimal
import sys
from types import SimpleNamespace

import pytest

from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

DESCRICAO_LONGA = (
    "ROUPEIRO 4 PORTAS ABRIR\n"
    "   - Interiores AGL MLM LINHO CANCUN 10/16/19mm\n"
    "   - Frentes MDF HIDROFUGO BRANCO B3002/MA_19MM\n"
    "   - Interiores AGL MLM BRANCO B3768/SC 12/19mm\n"
    "   * Portas Vidro/Aro Aluminio [Não Inclui]\n"
    "   - Dobradiças Blum"
)

COL_DESCRICAO = OrcamentoRelatoriosPage.ITEMS_HEADERS.index("Descrição")
COL_PRECO = OrcamentoRelatoriosPage.ITEMS_HEADERS.index("Preço Total")


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def pagina(_app):
    """A página a sério — o construtor monta os separadores sem tocar na BD."""
    return OrcamentoRelatoriosPage(orcamento_versao_id=1)


def _item(ordem: int, descricao: str):
    return SimpleNamespace(
        ordem=ordem,
        codigo="4 PORTAS",
        descricao=descricao,
        item="",
        altura=Decimal("2500"),
        largura=Decimal("2500"),
        profundidade=Decimal("600"),
        unidade="un",
        quantidade=Decimal("1"),
        preco_unitario=Decimal("1559.71"),
        preco_total=Decimal("1559.71"),
    )


def test_a_descricao_toda_fica_na_celula(pagina) -> None:
    pagina._preencher_items([_item(1, DESCRICAO_LONGA)])

    texto = pagina.items_table.item(0, COL_DESCRICAO).text()

    assert texto == DESCRICAO_LONGA
    # As linhas que antes ficavam escondidas:
    assert "Dobradiças Blum" in texto
    assert "[Não Inclui]" in texto


def test_a_tabela_de_items_quebra_o_texto(pagina) -> None:
    assert pagina.items_table.wordWrap()


def test_a_altura_da_linha_acompanha_o_conteudo(pagina) -> None:
    from PySide6.QtWidgets import QHeaderView

    # A secção só existe depois de haver linhas; sem isso o Qt devolve `Fixed`.
    pagina._preencher_items([_item(1, DESCRICAO_LONGA)])

    modo = pagina.items_table.verticalHeader().sectionResizeMode(0)

    assert modo == QHeaderView.ResizeMode.ResizeToContents


def test_a_linha_cresce_para_caber_a_descricao(pagina) -> None:
    pagina._preencher_items([_item(1, "ROUPEIRO SIMPLES"), _item(2, DESCRICAO_LONGA)])

    curta = pagina.items_table.rowHeight(0)
    longa = pagina.items_table.rowHeight(1)

    assert longa > curta, "a linha da descrição longa devia ficar mais alta"


def test_o_resto_da_linha_encosta_em_cima(pagina) -> None:
    from PySide6.QtCore import Qt

    pagina._preencher_items([_item(1, DESCRICAO_LONGA)])

    # Com linhas altas, os preços não podem ficar a meio da altura, longe do
    # item a que pertencem.
    alinhamento = pagina.items_table.item(0, COL_PRECO).textAlignment()

    assert alinhamento & Qt.AlignmentFlag.AlignTop


def test_a_descricao_tem_largura_para_respirar() -> None:
    # Não resolve sozinho (o texto quebra na largura que houver), mas evita que
    # a coluna nasça estreita e a linha fique altíssima.
    assert OrcamentoRelatoriosPage.ITEMS_LARGURAS["Descrição"] >= 300
