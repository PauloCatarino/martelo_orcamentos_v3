"""Tests for UI formatting helpers."""

from __future__ import annotations

from decimal import Decimal

from app.utils.formatters import (
    format_currency,
    format_mm,
    format_quantity,
    format_tipo_item,
    format_version,
    normalize_tipo_item,
)


def test_format_mm() -> None:
    assert format_mm(Decimal("2400.000")) == "2400 mm"
    assert format_mm(None) == ""


def test_format_quantity() -> None:
    assert format_quantity(Decimal("1.000")) == "1"
    assert format_quantity(Decimal("2.500")) == "2,5"
    assert format_quantity(Decimal("2.500"), "un") == "2,5"
    assert format_quantity(None, "un") == ""


def test_format_currency() -> None:
    assert format_currency(Decimal("500")) == "500,00 \u20ac"
    assert format_currency(Decimal("12.5")) == "12,50 \u20ac"
    assert format_currency(None) == ""


def test_format_version() -> None:
    assert format_version(1) == "01"
    assert format_version(2) == "02"
    assert format_version(3) == "03"
    assert format_version(10) == "10"
    assert format_version(12) == "12"
    assert format_version(None) == ""


def test_format_tipo_item() -> None:
    assert format_tipo_item("ROUPEIRO_ABRIR") == "Roupeiro Abrir"
    assert format_tipo_item("ROUPEIRO_CORRER") == "Roupeiro Correr"
    assert format_tipo_item("MOVEL_WC") == "M\u00f3vel WC"
    assert format_tipo_item("COZINHA") == "Cozinha"
    assert format_tipo_item("OUTRO") == "Outro"
    assert format_tipo_item(None) == "Outro"
    assert format_tipo_item("INVALIDO") == "Outro"


def test_normalize_tipo_item() -> None:
    assert normalize_tipo_item("roupeiro_abrir") == "ROUPEIRO_ABRIR"
    assert normalize_tipo_item(None) == "OUTRO"
    assert normalize_tipo_item("INVALIDO") == "OUTRO"
