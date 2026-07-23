"""Tests for building search synonyms from each user's AI profile."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.sinonimos_service import (
    grupos_de_sinonimos,
    mapa_de_sinonimos,
)


def _entrada(tipo, expressao, significado=""):
    return SimpleNamespace(tipo=tipo, expressao=expressao, significado=significado)


def test_movel_usa_as_duas_colunas() -> None:
    grupos = grupos_de_sinonimos(
        [_entrada("movel", "roupeiro", "roupeiros, guarda-fatos")]
    )

    assert len(grupos) == 1
    assert {"roupeiro", "guarda", "fato"} <= grupos[0]


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

    assert grupos == [frozenset({"lacar", "verniz", "envernizamento"})]


def test_cliente_liga_a_abreviatura_ao_nome_completo() -> None:
    grupos = grupos_de_sinonimos(
        [_entrada("cliente", "a Viva; o JF", "MÓVEIS J.F. VIVA")]
    )

    # «MÓVEIS» fica na raiz «movel», que é a mesma de «móvel».
    assert {"viva", "jf", "movel"} <= grupos[0]


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


def test_mapa_liga_cada_palavra_ao_grupo_todo() -> None:
    mapa = mapa_de_sinonimos([frozenset({"roupeiro", "guarda", "fato"})])

    assert mapa["guarda"] == frozenset({"roupeiro", "guarda", "fato"})
    assert mapa["roupeiro"] == frozenset({"roupeiro", "guarda", "fato"})
    assert "closet" not in mapa


def test_grupos_diferentes_que_partilham_palavra_juntam_se() -> None:
    mapa = mapa_de_sinonimos(
        [frozenset({"roupeiro", "guarda"}), frozenset({"roupeiro", "closet"})]
    )

    assert mapa["roupeiro"] == frozenset({"roupeiro", "guarda", "closet"})
