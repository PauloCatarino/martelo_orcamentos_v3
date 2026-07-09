"""Tests for human number and percentage helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.numeros import (
    formatar_percentagem,
    normalize_percentagem_humana,
    parse_decimal_humano,
    validar_decimal,
)


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
    for invalido in ("abc", "NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            parse_decimal_humano(invalido)


def test_formatar_percentagem() -> None:
    assert formatar_percentagem(None) == ""
    assert formatar_percentagem(Decimal("10")) == "10%"
    assert formatar_percentagem(Decimal("10.0")) == "10%"
    assert formatar_percentagem(Decimal("6.8")) == "6.8%"
    assert formatar_percentagem(Decimal("12.50")) == "12.5%"


def test_validar_decimal_aplica_limites_e_rejeita_nao_finitos() -> None:
    assert validar_decimal("1,25", "Preço", minimo=Decimal("0")) == Decimal("1.25")
    assert validar_decimal(None, "Preço") is None

    for valor in ("-1", "NaN", "Infinity"):
        with pytest.raises(ValueError):
            validar_decimal(valor, "Preço", minimo=Decimal("0"))

    with pytest.raises(ValueError):
        validar_decimal("0", "Medida", minimo=Decimal("0"), minimo_exclusivo=True)
