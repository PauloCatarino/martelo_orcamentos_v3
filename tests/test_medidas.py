"""Tests for the measure evaluation helpers."""

from __future__ import annotations

from decimal import Decimal

from app.domain.medidas import (
    avaliar_medida,
    calcular_area_m2,
    calcular_perimetro_ml,
    construir_contexto_item,
    normalizar_numero,
)


def test_avaliar_medida_variaveis_do_item() -> None:
    contexto = construir_contexto_item(Decimal("2750"), Decimal("1830"), Decimal("560"))

    assert avaliar_medida("H", contexto) == Decimal("2750")
    assert avaliar_medida("COMP", contexto) == Decimal("2750")
    assert avaliar_medida("ALTURA_COMP", contexto) == Decimal("2750")
    assert avaliar_medida("L", contexto) == Decimal("1830")
    assert avaliar_medida("LARG", contexto) == Decimal("1830")
    assert avaliar_medida("P", contexto) == Decimal("560")
    assert avaliar_medida("PROF", contexto) == Decimal("560")
    # Variable lookup is case-insensitive.
    assert avaliar_medida("profundidade", contexto) == Decimal("560")


def test_avaliar_medida_numeros() -> None:
    assert avaliar_medida("1452", None) == Decimal("1452")
    assert avaliar_medida("1452,5", None) == Decimal("1452.5")
    assert avaliar_medida("1452.5", None) == Decimal("1452.5")
    assert avaliar_medida(Decimal("100"), None) == Decimal("100")
    assert avaliar_medida(100, None) == Decimal("100")


def test_avaliar_medida_vazio_e_invalido_nao_rebenta() -> None:
    assert avaliar_medida(None, None) is None
    assert avaliar_medida("", None) is None
    assert avaliar_medida("   ", None) is None
    assert avaliar_medida("abc", None) is None
    # Complex formulas are left unresolved in this phase.
    assert avaliar_medida("H/2", {"H": Decimal("2750")}) is None
    assert avaliar_medida("L-50", {"L": Decimal("1830")}) is None


def test_normalizar_numero() -> None:
    assert normalizar_numero("8,62") == Decimal("8.62")
    assert normalizar_numero(Decimal("5")) == Decimal("5")
    assert normalizar_numero(None) is None
    assert normalizar_numero("xpto") is None


def test_calcular_area_m2() -> None:
    assert calcular_area_m2(Decimal("1000"), Decimal("500")) == Decimal("0.5")
    assert calcular_area_m2(Decimal("2750"), Decimal("1830")) == Decimal("5.0325")
    assert calcular_area_m2(None, Decimal("500")) is None
    assert calcular_area_m2(Decimal("500"), None) is None


def test_calcular_perimetro_ml() -> None:
    assert calcular_perimetro_ml(Decimal("1000"), Decimal("500")) == Decimal("3")
    assert calcular_perimetro_ml(Decimal("2750"), Decimal("1830")) == Decimal("9.16")
    assert calcular_perimetro_ml(None, None) is None
