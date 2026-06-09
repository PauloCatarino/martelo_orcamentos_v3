"""Tests for the finishing-area helpers (phase 8M)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.acabamentos import (
    AVISO_ACABAMENTO_DADOS_INCOMPLETOS,
    calcular_areas_acabamento,
    tem_acabamento,
)


def test_tem_acabamento() -> None:
    assert tem_acabamento("LACADO_BRANCO") is True
    assert tem_acabamento(None) is False
    assert tem_acabamento("") is False
    assert tem_acabamento("   ") is False
    assert tem_acabamento("SEM_ACABAMENTO") is False
    assert tem_acabamento("sem_acabamento") is False


def test_acabamento_superior() -> None:
    sup, inf, aviso = calcular_areas_acabamento(
        Decimal("2.1"), Decimal("2"), "LACADO", "SEM_ACABAMENTO"
    )
    assert sup == Decimal("4.2")
    assert inf == Decimal("0")
    assert aviso is None


def test_acabamento_inferior() -> None:
    sup, inf, aviso = calcular_areas_acabamento(Decimal("2.1"), Decimal("2"), None, "LACADO")
    assert sup == Decimal("0")
    assert inf == Decimal("4.2")
    assert aviso is None


def test_acabamento_ambos() -> None:
    sup, inf, aviso = calcular_areas_acabamento(
        Decimal("2.1"), Decimal("2"), "LACADO", "LACADO"
    )
    assert sup == Decimal("4.2")
    assert inf == Decimal("4.2")
    assert aviso is None


def test_acabamento_sem_acabamento() -> None:
    sup, inf, aviso = calcular_areas_acabamento(
        Decimal("2.1"), Decimal("2"), "SEM_ACABAMENTO", None
    )
    assert sup is None
    assert inf is None
    assert aviso is None


def test_acabamento_sem_area_avisa() -> None:
    sup, inf, aviso = calcular_areas_acabamento(None, Decimal("2"), "LACADO", None)
    assert sup is None
    assert inf is None
    assert aviso == AVISO_ACABAMENTO_DADOS_INCOMPLETOS


def test_acabamento_qt_none_assume_um() -> None:
    sup, _, _ = calcular_areas_acabamento(Decimal("2.1"), None, "LACADO", None)
    assert sup == Decimal("2.1")


def test_acabamento_campos_none_nao_rebenta() -> None:
    assert calcular_areas_acabamento(None, None, None, None) == (None, None, None)
