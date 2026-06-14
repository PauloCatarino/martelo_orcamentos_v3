"""Tests for the module library categories/scopes (phase 8U.0)."""

from __future__ import annotations

from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    COZINHAS,
    MOVEIS_WC,
    OUTROS,
    ROUPEIROS,
    get_modulo_categoria_label,
    get_modulo_categoria_options,
    normalize_modulo_ambito,
    normalize_modulo_categoria,
)


def test_categorias_seed() -> None:
    options = dict(get_modulo_categoria_options())
    assert options == {
        ROUPEIROS: "Roupeiros",
        COZINHAS: "Cozinhas",
        MOVEIS_WC: "Móveis WC",
        OUTROS: "Outros",
    }


def test_normalize_categoria_com_fallback() -> None:
    assert normalize_modulo_categoria("roupeiros") == ROUPEIROS
    assert normalize_modulo_categoria("  COZINHAS  ") == COZINHAS
    assert normalize_modulo_categoria("MOVEIS_WC") == MOVEIS_WC
    # Unknown / empty / None -> OUTROS.
    assert normalize_modulo_categoria("desconhecida") == OUTROS
    assert normalize_modulo_categoria("") == OUTROS
    assert normalize_modulo_categoria(None) == OUTROS


def test_categoria_label() -> None:
    assert get_modulo_categoria_label("cozinhas") == "Cozinhas"
    assert get_modulo_categoria_label(None) == "Outros"


def test_normalize_ambito_com_fallback() -> None:
    assert normalize_modulo_ambito("utilizador") == AMBITO_UTILIZADOR
    assert normalize_modulo_ambito("GLOBAL") == AMBITO_GLOBAL
    assert normalize_modulo_ambito("desconhecido") == AMBITO_UTILIZADOR
    assert normalize_modulo_ambito(None) == AMBITO_UTILIZADOR
