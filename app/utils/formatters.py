"""Formatting helpers for UI presentation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def format_mm(value: Any) -> str:
    """Format a millimeter value for display."""
    number = _to_decimal(value)
    if number is None:
        return ""

    return f"{_format_decimal_trimmed(number)} mm"


def format_quantity(value: Any, unidade: str | None = None) -> str:
    """Format a quantity without appending its unit."""
    number = _to_decimal(value)
    if number is None:
        return ""

    return _format_decimal_trimmed(number)


def format_medida_real(value: Any) -> str:
    """Uma medida vinda de uma f\u00f3rmula, com uma casa decimal.

    ``L/3`` de 1840 d\u00e1 613,333333 mm e a coluna ficava ileg\u00edvel a mostrar
    tudo. Nenhuma m\u00e1quina corta \u00e0 mil\u00e9sima de mil\u00edmetro: 613,3 diz o mesmo.

    \u00c9 **s\u00f3** a apresenta\u00e7\u00e3o \u2014 o valor guardado continua inteiro, e \u00e9 esse que
    entra na \u00e1rea, no custo e no plano de corte.
    """
    number = _to_decimal(value)
    if number is None:
        return ""

    return _format_decimal_trimmed(number.quantize(Decimal("0.1")))


def format_currency(value: Any) -> str:
    """Format a currency value for display."""
    number = _to_decimal(value)
    if number is None:
        return ""

    formatted = format(number.quantize(Decimal("0.01")), "f").replace(".", ",")
    return f"{formatted} \u20ac"


def format_version(numero_versao: Any) -> str:
    """Format a version number with two digits."""
    if numero_versao is None:
        return ""

    try:
        return f"{int(numero_versao):02d}"
    except (TypeError, ValueError):
        return str(numero_versao)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        value = value.replace(",", ".")

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_decimal_trimmed(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")

    if text == "-0":
        text = "0"

    return text.replace(".", ",")
