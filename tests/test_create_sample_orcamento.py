"""Tests for the sample budget script."""

from __future__ import annotations

from decimal import Decimal

from scripts.create_sample_orcamento import (
    CLIENTE_EMAIL,
    CLIENTE_IS_TEMPORARY,
    CLIENTE_NOME,
    ITEM_ALTURA,
    ITEM_QUANTIDADE,
    ORCAMENTO_ANO,
    ORCAMENTO_NUMERO,
    VERSAO_NUMERO,
    format_codigo_versao,
)


def test_sample_orcamento_constants_import() -> None:
    assert CLIENTE_NOME == "Cliente Teste V3"
    assert CLIENTE_EMAIL == "cliente.teste@martelo.local"
    assert CLIENTE_IS_TEMPORARY is True
    assert ORCAMENTO_ANO == 2026
    assert ORCAMENTO_NUMERO == "260001"
    assert VERSAO_NUMERO == 1
    assert ITEM_ALTURA == Decimal("2400")
    assert ITEM_QUANTIDADE == Decimal("1")


def test_format_codigo_versao() -> None:
    assert format_codigo_versao("260001", 1) == "260001_01"
    assert format_codigo_versao("260001", 12) == "260001_12"
