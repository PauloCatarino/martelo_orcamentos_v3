"""Tests for the STD/SERIE production type rules (phase 8S.4)."""

from __future__ import annotations

from app.domain.producao_types import (
    TIPO_PRODUCAO_SERIE,
    TIPO_PRODUCAO_STD,
    normalize_tipo_producao,
    tipo_producao_efetivo,
)


def test_normalize_tipo_producao() -> None:
    assert normalize_tipo_producao("STD") == TIPO_PRODUCAO_STD
    assert normalize_tipo_producao(" serie ") == TIPO_PRODUCAO_SERIE
    assert normalize_tipo_producao("std") == TIPO_PRODUCAO_STD
    assert normalize_tipo_producao(None) is None
    assert normalize_tipo_producao("") is None
    assert normalize_tipo_producao("XPTO") is None


def test_tipo_efetivo_herda_o_padrao() -> None:
    assert tipo_producao_efetivo(None, "STD") == TIPO_PRODUCAO_STD
    assert tipo_producao_efetivo(None, "SERIE") == TIPO_PRODUCAO_SERIE


def test_tipo_efetivo_excecao_do_item_vence() -> None:
    assert tipo_producao_efetivo("STD", "SERIE") == TIPO_PRODUCAO_STD
    assert tipo_producao_efetivo("SERIE", "STD") == TIPO_PRODUCAO_SERIE


def test_tipo_efetivo_fallback_std() -> None:
    assert tipo_producao_efetivo(None, None) == TIPO_PRODUCAO_STD
    assert tipo_producao_efetivo("INVALIDO", None) == TIPO_PRODUCAO_STD
    assert tipo_producao_efetivo(None, "INVALIDO") == TIPO_PRODUCAO_STD
