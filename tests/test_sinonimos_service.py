"""Tests for building search synonyms from each user's AI profile."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.pesquisa_texto import corresponde_texto
from app.services.sinonimos_service import (
    MAXIMO_FORMAS,
    grupos_de_sinonimos,
    mapa_de_sinonimos,
)


def _entrada(tipo, expressao, significado=""):
    return SimpleNamespace(tipo=tipo, expressao=expressao, significado=significado)


def test_movel_usa_as_duas_colunas() -> None:
    grupos = grupos_de_sinonimos(
        [_entrada("movel", "roupeiro", "roupeiros, guarda-fatos")]
    )

    # «guarda-fatos» é uma forma só, com as duas palavras.
    assert grupos == [frozenset({("roupeiro",), ("guarda", "fato")})]


def test_material_so_usa_a_coluna_da_esquerda() -> None:
    """A segunda coluna dos materiais é uma frase, não uma lista de sinónimos.

    Usá-la faria de «obra», «leva» e «cor» sinónimos de «lacado».
    """
    grupos = grupos_de_sinonimos(
        [
            _entrada(
                "material",
                "lacar; verniz; envernizamento",
                "Obra que leva lacagem, seja qual for a cor",
            )
        ]
    )

    assert grupos == [frozenset({("lacar",), ("verniz",), ("envernizamento",)})]


def test_cliente_liga_a_abreviatura_ao_nome_completo() -> None:
    grupos = grupos_de_sinonimos(
        [_entrada("cliente", "a Viva; o JF", "MÓVEIS J.F. VIVA")]
    )

    # O artigo cai («a Viva» é «viva») e o nome completo fica uma frase.
    assert grupos == [
        frozenset({("viva",), ("jf",), ("movel", "j", "f", "viva")})
    ]


def test_palavras_soltas_de_uma_frase_nao_viram_sinonimos() -> None:
    """O bug de outubro de 2026: «a» e «móveis» eram sinónimos de «viva».

    Bastava a obra ter a palavra «a» (ou ser de outro cliente «Móveis…») para
    aparecer numa pesquisa por «viva».
    """
    mapa = mapa_de_sinonimos(
        grupos_de_sinonimos(
            [_entrada("cliente", "a Viva; a JF; JF_VIVA", "MÓVEIS J.F. VIVA")]
        )
    )

    assert corresponde_texto(["MÓVEIS SILVA", "uma porta a abrir"], "viva", mapa) is False
    assert corresponde_texto(["MÓVEIS J.F. VIVA"], "viva", mapa) is True
    assert corresponde_texto(["JF"], "viva", mapa) is True


def test_lista_comprida_e_vocabulario_nao_sinonimos() -> None:
    """«roupeiro; abrir; correr; cozinha; cama…» não quer dizer que são iguais.

    Lida como sinónimos, procurar «cozinha» devolvia todos os roupeiros.
    """
    lista = "roupeiro; abrir; correr; curvo; módulo; cama; cozinha; estante"
    assert len(lista.split(";")) > MAXIMO_FORMAS

    assert grupos_de_sinonimos([_entrada("movel", lista, "termos que uso")]) == []


def test_sinonimo_de_varias_palavras_exige_todas() -> None:
    mapa = mapa_de_sinonimos(grupos_de_sinonimos([_entrada("movel", "roupeiro", "guarda-fatos")]))

    assert corresponde_texto(["1 GUARDA FATOS"], "roupeiro", mapa) is True
    assert corresponde_texto(["GUARDA DE LOUÇA"], "roupeiro", mapa) is False
    # E escrever a frase procura-a como um só termo, com os sinónimos.
    assert corresponde_texto(["3 ROUPEIROS"], "guarda-fatos", mapa) is True


def test_quadros_sem_sinonimos_sao_ignorados() -> None:
    """Perguntas, avisos e «o que não quero ver» não são vocabulário."""
    entradas = [
        _entrada("pergunta", "Que obras estão atrasadas?", "lista"),
        _entrada("aviso", "orçamentos parados", "uma vez por semana"),
        _entrada("nao_quero", "contagens do meu trabalho", "sinto-me avaliado"),
        _entrada("estado", "está na máquina", "Produção"),
        _entrada("tempo", "urgente", "2 dias"),
    ]

    assert grupos_de_sinonimos(entradas) == []


def test_linha_com_uma_so_palavra_nao_gera_sinonimo() -> None:
    assert grupos_de_sinonimos([_entrada("movel", "roupeiro", "")]) == []
    # «roupeiros» é a mesma forma que «roupeiro»: continua a ser uma só.
    assert grupos_de_sinonimos([_entrada("movel", "roupeiro", "roupeiros")]) == []


def test_mapa_liga_cada_forma_ao_grupo_todo() -> None:
    grupo = frozenset({("roupeiro",), ("guarda", "fato")})
    mapa = mapa_de_sinonimos([grupo])

    assert mapa[("guarda", "fato")] == grupo
    assert mapa[("roupeiro",)] == grupo
    assert ("closet",) not in mapa


def test_grupos_diferentes_que_partilham_forma_juntam_se() -> None:
    mapa = mapa_de_sinonimos(
        [
            frozenset({("roupeiro",), ("guarda", "fato")}),
            frozenset({("roupeiro",), ("closet",)}),
        ]
    )

    assert mapa[("roupeiro",)] == frozenset(
        {("roupeiro",), ("guarda", "fato"), ("closet",)}
    )
