"""Tests for the measure evaluation helpers."""

from __future__ import annotations

from decimal import Decimal

from app.domain.medidas import (
    avaliar_medida,
    calcular_area_m2,
    calcular_perimetro_ml,
    construir_contexto_item,
    normalizar_numero,
    normalizar_variaveis_medida,
)


def test_normalizar_variaveis_medida_maiusculas() -> None:
    # Variable letters are uppercased; numbers/operators/spacing are kept.
    assert normalizar_variaveis_medida("l/5*2") == "L/5*2"
    assert normalizar_variaveis_medida("hm-50") == "HM-50"
    assert normalizar_variaveis_medida("(h-50)/2") == "(H-50)/2"
    assert normalizar_variaveis_medida("l1+l2") == "L1+L2"
    assert normalizar_variaveis_medida("p") == "P"
    # Plain numbers and already-uppercase text are unchanged.
    assert normalizar_variaveis_medida("2100") == "2100"
    assert normalizar_variaveis_medida("L / 5 * 2") == "L / 5 * 2"
    # The evaluated result is the same before and after normalising the text.
    contexto = construir_contexto_item(Decimal("2100"), Decimal("800"), Decimal("560"))
    assert avaliar_medida(
        normalizar_variaveis_medida("l/5*2"), contexto
    ) == avaliar_medida("l/5*2", contexto)


def test_normalizar_variaveis_medida_entrada_nao_texto() -> None:
    assert normalizar_variaveis_medida(None) is None
    assert normalizar_variaveis_medida(Decimal("12")) == Decimal("12")


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


def test_avaliar_medida_variaveis_locais_hm_lm_pm() -> None:
    contexto = construir_contexto_item(Decimal("2750"), Decimal("1830"), Decimal("560"))
    contexto_com_local = {
        **contexto,
        "HM": Decimal("1000"),
        "LM": Decimal("500"),
        "PM": Decimal("20"),
    }

    assert avaliar_medida("HM", contexto_com_local) == Decimal("1000")
    assert avaliar_medida("LM", contexto_com_local) == Decimal("500")
    assert avaliar_medida("PM", contexto_com_local) == Decimal("20")
    # Without a division context, HM/LM/PM are unresolved and do not raise.
    assert avaliar_medida("HM", contexto) is None


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


def test_avaliar_medida_expressoes_matematicas() -> None:
    contexto = {
        "H": Decimal("1452"),
        "L": Decimal("236"),
        "P": Decimal("253"),
        "HM": Decimal("1452"),
        "LM": Decimal("236"),
        "PM": Decimal("253"),
    }

    assert avaliar_medida("H/2", contexto) == Decimal("726")
    assert avaliar_medida("L*2", contexto) == Decimal("472")
    assert avaliar_medida("P-20", contexto) == Decimal("233")
    assert avaliar_medida("HM/2", contexto) == Decimal("726")
    assert avaliar_medida("LM-50", contexto) == Decimal("186")
    assert avaliar_medida("PM+10", contexto) == Decimal("263")
    assert avaliar_medida("(H-50)/2", contexto) == Decimal("701")
    assert avaliar_medida("1452,5/2", contexto) == Decimal("726.25")
    assert avaliar_medida("1452/2", contexto) == Decimal("726")


def test_avaliar_medida_expressoes_invalidas_nao_rebentam() -> None:
    contexto = {"H": Decimal("1452")}

    assert avaliar_medida("abc", contexto) is None
    assert avaliar_medida("H//2", contexto) is None
    assert avaliar_medida("__import__('os')", contexto) is None
    assert avaliar_medida("H/0", contexto) is None
    # Unknown / future variables resolve to None instead of raising.
    assert avaliar_medida("H1/2", contexto) is None


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
