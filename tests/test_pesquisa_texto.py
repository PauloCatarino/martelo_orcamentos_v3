"""Tests for the text search engine (accents, punctuation, plurals, synonyms)."""

from __future__ import annotations

from app.domain.pesquisa_texto import (
    corresponde,
    corresponde_texto,
    expandir_termos,
    indexar,
    normalizar,
    raiz,
    raizes,
    sugerir_pesquisa,
    sugerir_termo,
)


def test_normalizar_tira_acentos_e_pontuacao() -> None:
    assert normalizar("MÓVEIS J.F. VIVA") == "moveis j f viva"
    assert normalizar("26.1134_01_01") == "26 1134 01 01"
    assert normalizar("  Ângela  ") == "angela"
    assert normalizar(None) == ""


def test_raiz_tira_os_plurais_mais_comuns() -> None:
    assert raiz("roupeiros") == "roupeiro"
    assert raiz("portas") == "porta"
    assert raiz("moveis") == "movel"
    assert raiz("aviões" and normalizar("aviões")) == "aviao"
    assert raiz("metais") == "metal"
    assert raiz("homens") == "homem"


def test_raiz_nao_estraga_palavras_curtas_nem_codigos() -> None:
    """Cortar «jf» ou «26» daria falsos positivos por todo o lado."""
    assert raiz("jf") == "jf"
    assert raiz("26") == "26"
    assert raiz("ncs") == "ncs"


def test_singular_e_plural_encontram_se(  # o caso que o Paulo pediu
) -> None:
    obra = ["3 ROUPEIROS PORTAS ABRIR"]

    assert corresponde_texto(obra, "roupeiro") is True
    assert corresponde_texto(obra, "roupeiros") is True
    assert corresponde_texto(obra, "ROUPEIRO") is True
    assert corresponde_texto(obra, "closet") is False


def test_todas_as_palavras_tem_de_estar_presentes() -> None:
    obra = ["3 ROUPEIROS PORTAS ABRIR", "MÓVEIS J.F. VIVA"]

    assert corresponde_texto(obra, "roupeiro viva") is True
    assert corresponde_texto(obra, "roupeiro tecnolame") is False


def test_pesquisa_vazia_aceita_tudo() -> None:
    assert corresponde_texto(["seja o que for"], "") is True
    assert corresponde_texto([], "   ") is True


def test_sinonimos_alargam_a_pesquisa() -> None:
    obra = ["3 ROUPEIROS PORTAS ABRIR"]
    sinonimos = {"guarda": frozenset({"guarda", "roupeiro"}), "fato": frozenset({"fato", "roupeiro"})}

    assert corresponde_texto(obra, "guarda", sinonimos) is True
    assert corresponde_texto(obra, "guarda", None) is False


def test_indice_e_termos_separados_dao_o_mesmo_resultado() -> None:
    obra = ["1 CLOSET EM L", "TECNOLAME"]
    indice = indexar(obra)

    assert corresponde(indice, expandir_termos("closet")) is True
    assert corresponde(indice, expandir_termos("roupeiro")) is False


def test_sugestao_para_erro_de_escrita() -> None:
    vocabulario = {"roupeiro", "closet", "tecnolame"}

    assert sugerir_termo("roupeirs", vocabulario) == "roupeiro"
    assert sugerir_termo("xxxxxx", vocabulario) == ""


def test_sugerir_pesquisa_so_reescreve_o_que_nao_existe() -> None:
    vocabulario = {"roupeiro", "porta"}

    assert sugerir_pesquisa("roupeirs", vocabulario) == "roupeiro"
    # tudo já existe: não vale a pena sugerir nada
    assert sugerir_pesquisa("roupeiro porta", vocabulario) == ""
    assert sugerir_pesquisa("", vocabulario) == ""


def test_raizes_devolve_pela_ordem_de_escrita() -> None:
    assert raizes("Roupeiros de Correr") == ["roupeiro", "de", "correr"]
