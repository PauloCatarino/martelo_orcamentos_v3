"""Tests for human number and percentage helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.numeros import normalize_percentagem_humana, parse_decimal_humano


def test_normalizar_fracao_para_percentagem() -> None:
    assert normalize_percentagem_humana(Decimal("0.1")) == Decimal("10")
    assert normalize_percentagem_humana(Decimal("0.32")) == Decimal("32")


def test_normalizar_mantem_percentagem_humana() -> None:
    assert normalize_percentagem_humana(Decimal("5")) == Decimal("5")
    assert normalize_percentagem_humana(Decimal("36")) == Decimal("36")


def test_normalizar_none_e_zero() -> None:
    assert normalize_percentagem_humana(None) is None
    assert normalize_percentagem_humana(Decimal("0")) == Decimal("0")


def test_parse_aceita_virgula_e_ponto() -> None:
    assert parse_decimal_humano("8,62") == Decimal("8.62")
    assert parse_decimal_humano("0,1") == Decimal("0.1")
    assert parse_decimal_humano("10,5") == Decimal("10.5")
    assert parse_decimal_humano("8.62") == Decimal("8.62")


def test_parse_vazio_devolve_none() -> None:
    assert parse_decimal_humano("") is None
    assert parse_decimal_humano("   ") is None
    assert parse_decimal_humano(None) is None


def test_parse_invalido_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        parse_decimal_humano("abc")
