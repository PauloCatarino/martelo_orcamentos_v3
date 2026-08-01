"""The library text of a piece, shared by the costing tree and the catalog."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from app.domain.peca_biblioteca import texto_biblioteca_peca
from app.domain.peca_types import COMPOSTA, SIMPLES


def _peca(
    nome: str,
    *,
    nome_biblioteca=None,
    tipo_peca=SIMPLES,
    orlas=(2, 1, 1, 1),
    usa_orlas=True,
) -> SimpleNamespace:
    return SimpleNamespace(
        nome=nome,
        nome_biblioteca=nome_biblioteca,
        tipo_peca=tipo_peca,
        orla_c1=orlas[0],
        orla_c2=orlas[1],
        orla_l1=orlas[2],
        orla_l2=orlas[3],
        usa_orlas=usa_orlas,
    )


def test_usa_o_nome_da_biblioteca_quando_existe() -> None:
    peca = _peca("Lateral[2111]", nome_biblioteca="Lateral")

    assert texto_biblioteca_peca(peca) == "Lateral [2111]"


def test_cai_para_o_nome_quando_a_biblioteca_esta_vazia() -> None:
    assert texto_biblioteca_peca(_peca("Lateral[2111]")) == "Lateral[2111] [2111]"
    assert (
        texto_biblioteca_peca(_peca("Lateral[2111]", nome_biblioteca=""))
        == "Lateral[2111] [2111]"
    )


def test_uma_peca_sem_orlas_nao_mostra_o_codigo() -> None:
    # Ferragens e perfis comprados: o "[0000]" não diz nada e só suja a lista.
    peca = _peca(
        "Varão",
        nome_biblioteca="Varao Roupeiro {SPP}",
        orlas=(0, 0, 0, 0),
        usa_orlas=False,
    )

    assert texto_biblioteca_peca(peca) == "Varao Roupeiro {SPP}"


def test_marca_as_compostas() -> None:
    peca = _peca(
        "Varão",
        nome_biblioteca="Varao {SPP}+Suportes",
        tipo_peca=COMPOSTA,
        orlas=(0, 0, 0, 0),
        usa_orlas=False,
    )

    assert texto_biblioteca_peca(peca) == "Varao {SPP}+Suportes (composta)"


def test_a_arvore_do_custeio_e_o_catalogo_usam_o_mesmo_texto() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert "texto_biblioteca_peca" in inspect.getsource(
        DefPecasPage._preencher_arvore
    )
    assert "texto_biblioteca_peca" in inspect.getsource(
        OrcamentoItemCusteioPage._criar_folha_biblioteca
    )
