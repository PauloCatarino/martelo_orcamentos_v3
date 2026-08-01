"""The library text of a piece, shared by the costing tree and the catalog."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from app.domain.peca_biblioteca import texto_biblioteca_peca
from app.domain.peca_types import COMPOSTA, SIMPLES


def _peca(nome: str, *, nome_biblioteca=None, tipo_peca=SIMPLES) -> SimpleNamespace:
    return SimpleNamespace(
        nome=nome, nome_biblioteca=nome_biblioteca, tipo_peca=tipo_peca
    )


def test_usa_o_nome_da_biblioteca_quando_existe() -> None:
    peca = _peca("Varão", nome_biblioteca="Varao Roupeiro {SPP}")

    assert texto_biblioteca_peca(peca, "0000") == "Varao Roupeiro {SPP} [0000]"


def test_cai_para_o_nome_quando_a_biblioteca_esta_vazia() -> None:
    assert texto_biblioteca_peca(_peca("Lateral[2222]"), "2222") == "Lateral[2222] [2222]"
    assert (
        texto_biblioteca_peca(_peca("Lateral[2222]", nome_biblioteca=""), "2222")
        == "Lateral[2222] [2222]"
    )


def test_marca_as_compostas() -> None:
    peca = _peca("Varão", nome_biblioteca="Varao {SPP}+Suportes", tipo_peca=COMPOSTA)

    assert texto_biblioteca_peca(peca, "0000") == "Varao {SPP}+Suportes [0000] (composta)"


def test_a_arvore_do_custeio_e_o_catalogo_usam_o_mesmo_texto() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert "texto_biblioteca_peca" in inspect.getsource(
        DefPecasPage._preencher_arvore
    )
    assert "texto_biblioteca_peca" in inspect.getsource(
        OrcamentoItemCusteioPage._criar_folha_biblioteca
    )
