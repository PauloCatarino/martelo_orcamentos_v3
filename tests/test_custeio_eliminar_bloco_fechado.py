"""Eliminar uma composta FECHADA leva o conteúdo dela atrás.

Pedido do Paulo (2026-08-05): com o bloco fechado vê-se uma linha só, e essa
linha representa o conjunto — eliminá-la tem de eliminar tudo. Antes, os
filhos ficavam para trás como linhas soltas (o repositório limita-se a pôr
``linha_pai_id = None``) e nem se percebia o que tinha acontecido.

Com o bloco ABERTO manda a seleção: elimina-se o que se está a ver marcado.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.domain.custeio_linha_types import FERRAGEM, PECA, PECA_COMPOSTA
from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _linha(id_: int, tipo: str, pai: int | None = None):
    return SimpleNamespace(id=id_, tipo_linha=tipo, linha_pai_id=pai, custo_total=None)


# Uma gaveta composta (10) com dois filhos, e uma peça com ferragem auto (20).
LINHAS = [
    _linha(1, PECA),
    _linha(10, PECA_COMPOSTA),
    _linha(11, PECA, pai=10),
    _linha(12, FERRAGEM, pai=10),
    _linha(20, PECA),
    _linha(21, FERRAGEM, pai=20),
]


def _pagina(_app, *, expandidas=()):
    from app.domain.custeio_colapso import (
        descendentes_por_composta,
        ferragens_associadas_por_peca,
    )

    pagina = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    pagina._descendentes_composta = descendentes_por_composta(LINHAS)
    pagina._ferragens_associadas_por_peca = ferragens_associadas_por_peca(LINHAS)
    pagina._compostas_expandidas = set(expandidas)
    return pagina


def test_composta_fechada_leva_os_filhos(_app) -> None:
    pagina = _pagina(_app)

    assert sorted(pagina._conteudo_de_blocos_fechados([10])) == [11, 12]


def test_composta_aberta_elimina_so_o_selecionado(_app) -> None:
    pagina = _pagina(_app, expandidas={10})

    assert pagina._conteudo_de_blocos_fechados([10]) == []


def test_peca_fechada_leva_a_ferragem_automatica(_app) -> None:
    pagina = _pagina(_app)

    assert pagina._conteudo_de_blocos_fechados([20]) == [21]


def test_linha_normal_nao_arrasta_nada(_app) -> None:
    pagina = _pagina(_app)

    assert pagina._conteudo_de_blocos_fechados([1]) == []


def test_filho_selecionado_a_parte_nao_e_repetido(_app) -> None:
    # Selecionar o cabeçalho E um filho não pode mandar o filho duas vezes.
    pagina = _pagina(_app)

    extra = pagina._conteudo_de_blocos_fechados([10, 11])

    assert extra == [12]


def test_varios_blocos_fechados_de_uma_vez(_app) -> None:
    pagina = _pagina(_app)

    assert sorted(pagina._conteudo_de_blocos_fechados([10, 20])) == [11, 12, 21]


# ---- o aviso tem de dizer o que vai MESMO desaparecer ------------------------
def test_aviso_de_uma_linha_simples() -> None:
    mensagem = OrcamentoItemCusteioPage._mensagem_eliminar(1, 0)

    assert mensagem == "Deseja eliminar definitivamente esta linha de custeio?"


def test_aviso_conta_as_linhas_arrastadas() -> None:
    mensagem = OrcamentoItemCusteioPage._mensagem_eliminar(1, 9)

    assert "mais 9 linha(s)" in mensagem
    assert "as 10 linhas de custeio" in mensagem
    # E diz como fazer se só quiser algumas.
    assert "abra o bloco" in mensagem


def test_aviso_de_varias_linhas_sem_arrastar() -> None:
    mensagem = OrcamentoItemCusteioPage._mensagem_eliminar(3, 0)

    assert "as 3 linhas de custeio selecionadas" in mensagem
    assert "mais" not in mensagem
