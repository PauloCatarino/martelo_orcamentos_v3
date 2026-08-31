"""Pesquisa nos Caminhos do Sistema.

São 55 linhas. O Paulo foi lá confirmar a linha nova (`pasta_instaladores`) e
não a encontrou — ela estava lá, na posição 22, mas entre outras 54 não se vê.
Encontrar um caminho não pode depender de percorrer a lista toda com os olhos.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.ui.pages.caminhos_sistema_page import configuracao_corresponde

INSTALADORES = SimpleNamespace(
    chave="pasta_instaladores",
    descricao="Pasta do servidor onde ficam os instaladores do Martelo V3.",
    grupo="Geral",
    valor=r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
    r"\Instalador_Setup_Martelo",
)
CUT_RITE = SimpleNamespace(
    chave="pasta_dados_cut_rite",
    descricao="Pasta de dados do CUT-RITE.",
    grupo="CUT-RITE",
    valor=r"\\SERVER_LE\Homag_iX\Cutrite\V12-Data\Data",
)


@pytest.mark.parametrize(
    "procurado",
    [
        "instaladores",     # a palavra certa
        "instalador",       # singular
        "instala",          # so' um pedaco: e' assim que as pessoas escrevem
        "INSTALADORES",     # maiusculas
        "pasta instalador", # duas palavras soltas
        "Instalador_Setup", # um pedaco do proprio caminho
    ],
)
def test_encontra_a_pasta_dos_instaladores(procurado: str) -> None:
    assert configuracao_corresponde(INSTALADORES, procurado) is True


def test_procura_tambem_pelo_valor_e_pelo_grupo() -> None:
    # Quem nao se lembra do nome lembra-se do sitio.
    assert configuracao_corresponde(CUT_RITE, "SERVER_LE") is True
    assert configuracao_corresponde(CUT_RITE, "cut-rite") is True


def test_nao_traz_o_que_nao_tem_nada_a_ver() -> None:
    assert configuracao_corresponde(CUT_RITE, "instaladores") is False
    assert configuracao_corresponde(INSTALADORES, "xyz") is False


def test_pesquisa_vazia_mostra_tudo() -> None:
    for procurado in ("", "   ", None):
        assert configuracao_corresponde(INSTALADORES, procurado) is True


def test_campos_a_none_nao_rebentam() -> None:
    vazia = SimpleNamespace(chave=None, descricao=None, grupo=None, valor=None)

    assert configuracao_corresponde(vazia, "seja o que for") is False
    assert configuracao_corresponde(vazia, "") is True


def test_a_pagina_usa_o_widget_de_pesquisa_da_casa() -> None:
    """O mesmo campo + pincel dos outros menus, não um inventado aqui."""
    import inspect

    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage

    fonte = inspect.getsource(CaminhosSistemaPage.__init__)
    assert "CampoPesquisa" in fonte
    assert "limpar_clicado" in fonte

    aplicar = inspect.getsource(CaminhosSistemaPage.aplicar_pesquisa)
    assert "configuracao_corresponde" in aplicar
