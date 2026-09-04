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

    # letras trocadas: nem inteiro nem pedaço existe, aqui vale a pena sugerir
    assert sugerir_pesquisa("ruopeiro", vocabulario) == "roupeiro"
    # tudo já existe: não vale a pena sugerir nada
    assert sugerir_pesquisa("roupeiro porta", vocabulario) == ""
    assert sugerir_pesquisa("", vocabulario) == ""


def test_sugerir_pesquisa_cala_se_quando_o_pedaco_ja_encontra() -> None:
    """«877» encontra o 260877 — não faz sentido perguntar «Quis dizer 77?»."""
    vocabulario = {"260877", "260879", "roupeiro"}

    assert sugerir_pesquisa("877", vocabulario) == ""
    assert sugerir_pesquisa("roupeir", vocabulario) == ""


def test_raizes_devolve_pela_ordem_de_escrita() -> None:
    assert raizes("Roupeiros de Correr") == ["roupeiro", "de", "correr"]


def test_encontra_por_pedaco_de_palavra() -> None:
    """Raramente se escreve o número do orçamento todo."""
    indice = indexar(["260877", "260877_02", "PEDRO REIS", "ROUPEIROS PORTAS ABRIR"])

    assert corresponde(indice, expandir_termos("877")) is True
    assert corresponde(indice, expandir_termos("0877")) is True
    assert corresponde(indice, expandir_termos("260877")) is True
    assert corresponde(indice, expandir_termos("roup")) is True
    assert corresponde(indice, expandir_termos("pedr")) is True


def test_pedaco_curto_de_mais_continua_a_exigir_a_palavra_inteira() -> None:
    """Com uma ou duas letras, procurar por pedaço devolvia a lista toda."""
    indice = indexar(["260877", "ROUPEIROS"])

    assert corresponde(indice, expandir_termos("87")) is False
    assert corresponde(indice, expandir_termos("r")) is False
    # três já chega
    assert corresponde(indice, expandir_termos("877")) is True


def test_todas_as_palavras_escritas_tem_de_estar_la() -> None:
    indice = indexar(["260877", "PEDRO REIS"])

    assert corresponde(indice, expandir_termos("877 reis")) is True
    assert corresponde(indice, expandir_termos("877 silva")) is False
