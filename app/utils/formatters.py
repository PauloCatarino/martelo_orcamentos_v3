"""Formatting helpers for UI presentation."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
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


def format_quantity_2(value: Any) -> str:
    """Uma quantidade com NO MÁXIMO duas casas decimais.

    As tabelas do resumo de consumos (placas, orlas, ferragens, máquinas/MO)
    mostravam o número tal como sai do cálculo -- 6,903333333333 m²,
    0,8333333 min -- e as colunas ficavam ilegíveis. Ninguém compra placas
    à milésima de m²: duas casas dizem o mesmo.

    É **só** a apresentação -- o valor guardado e o que entra nas contas
    continuam inteiros. Os zeros à direita continuam a ser cortados, por
    isso ``6`` aparece como ``6`` e não como ``6,00``.
    """
    number = _to_decimal(value)
    if number is None:
        return ""

    try:
        number = number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:  # números absurdamente grandes: fica como estava
        pass

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


def format_currency(value: Any, *, milhares: bool = False) -> str:
    """Format a currency value for display.

    ``milhares`` acrescenta o separador de milhares, como se escreve em
    portugu\u00eas: ``236 059,86 \u20ac``. Fica desligado por omiss\u00e3o porque este
    formatador serve tamb\u00e9m tabelas, PDFs e o Excel, onde a largura dos n\u00fameros
    j\u00e1 est\u00e1 contada; liga-se onde o valor \u00e9 grande e se l\u00ea de relance, como o
    total do rodap\u00e9 dos or\u00e7amentos.
    """
    number = _to_decimal(value)
    if number is None:
        return ""

    quantizado = number.quantize(Decimal("0.01"))
    if milhares:
        # Espa\u00e7o INQUEBR\u00c1VEL: com um espa\u00e7o normal a linha podia partir entre
        # "236" e "059" e ficavam dois n\u00fameros diferentes no ecr\u00e3.
        formatted = f"{quantizado:,.2f}".replace(",", "\u00a0").replace(".", ",")
    else:
        formatted = format(quantizado, "f").replace(".", ",")
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
