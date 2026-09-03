"""Tests for UI formatting helpers."""

from __future__ import annotations

from decimal import Decimal

from app.utils.formatters import (
    format_currency,
    format_mm,
    format_quantity,
    format_version,
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


def test_medida_real_mostra_uma_casa_decimal() -> None:
    """"L/3" de 1840 dá 613,333333 e a coluna do custeio ficava ilegível."""
    from app.utils.formatters import format_medida_real

    assert format_medida_real("613.333333") == "613,3"
    assert format_medida_real("1226.666667") == "1226,7"


def test_medida_real_nao_inventa_decimais_a_um_numero_redondo() -> None:
    from app.utils.formatters import format_medida_real

    assert format_medida_real("450") == "450"
    assert format_medida_real(19) == "19"


def test_medida_real_sem_valor_fica_vazia() -> None:
    from app.utils.formatters import format_medida_real

    assert format_medida_real(None) == ""


def test_quantity_2_corta_nas_duas_casas_decimais() -> None:
    """As colunas do resumo de consumos mostravam dez e doze casas decimais."""
    from app.utils.formatters import format_quantity_2

    assert format_quantity_2("6.903333333333") == "6,9"
    assert format_quantity_2("1058.216666") == "1058,22"
    assert format_quantity_2(Decimal("0.8333333")) == "0,83"


def test_quantity_2_nao_inventa_decimais_a_um_numero_redondo() -> None:
    from app.utils.formatters import format_quantity_2

    assert format_quantity_2(6) == "6"
    assert format_quantity_2(Decimal("1830")) == "1830"
    assert format_quantity_2("0.40") == "0,4"


def test_quantity_2_arredonda_para_cima_a_meio() -> None:
    from app.utils.formatters import format_quantity_2

    assert format_quantity_2("2.005") == "2,01"
    assert format_quantity_2("2.004") == "2"


def test_quantity_2_sem_valor_fica_vazia() -> None:
    from app.utils.formatters import format_quantity_2

    assert format_quantity_2(None) == ""
    assert format_quantity_2("") == ""
