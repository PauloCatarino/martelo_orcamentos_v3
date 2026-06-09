"""Tests for the raw-material cost helpers (phase 8I)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.custos import (
    AVISO_MP_DADOS_INCOMPLETOS,
    AVISO_MP_UNIDADE_INVALIDA,
    AVISO_MP_UNIDADE_ML,
    AVISO_MP_UNIDADE_UND,
    calcular_custo_mp,
    desperdicio_para_fracao,
    fator_desperdicio,
)


def test_desperdicio_para_fracao_normaliza() -> None:
    assert desperdicio_para_fracao(None) == Decimal("0")
    assert desperdicio_para_fracao(Decimal("0.10")) == Decimal("0.10")
    assert desperdicio_para_fracao(Decimal("10")) == Decimal("0.10")
    assert desperdicio_para_fracao(Decimal("100")) == Decimal("1.00")


def test_fator_desperdicio_aceita_fracao_e_humano() -> None:
    assert fator_desperdicio(Decimal("0.20")) == Decimal("1.2")
    assert fator_desperdicio(Decimal("20")) == Decimal("1.2")
    assert fator_desperdicio(Decimal("0.10")) == Decimal("1.1")
    assert fator_desperdicio(Decimal("10")) == Decimal("1.1")
    assert fator_desperdicio(None) == Decimal("1")


def test_custo_mp_m2_com_desperdicio() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), Decimal("0.20"), "M2"
    )
    assert custo == Decimal("36")
    assert aviso is None


def test_custo_mp_m2_sem_desperdicio() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, "M2"
    )
    assert custo == Decimal("30")
    assert aviso is None


def test_custo_mp_qt_zero() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("0"), Decimal("10"), Decimal("0.20"), "M2"
    )
    assert custo == Decimal("0")
    assert aviso is None


def test_custo_mp_area_vazia() -> None:
    custo, aviso = calcular_custo_mp(None, Decimal("6"), Decimal("10"), None, "M2")
    assert custo is None
    assert aviso == AVISO_MP_DADOS_INCOMPLETOS


def test_custo_mp_preco_vazio() -> None:
    custo, aviso = calcular_custo_mp(Decimal("0.5"), Decimal("6"), None, None, "M2")
    assert custo is None
    assert aviso == AVISO_MP_DADOS_INCOMPLETOS


def test_custo_mp_unidade_ml() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, "ML"
    )
    assert custo is None
    assert aviso == AVISO_MP_UNIDADE_ML


def test_custo_mp_unidade_und() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, "UND"
    )
    assert custo is None
    assert aviso == AVISO_MP_UNIDADE_UND


def test_custo_mp_unidade_vazia() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, ""
    )
    assert custo is None
    assert aviso == AVISO_MP_UNIDADE_INVALIDA


def test_custo_mp_unidade_m2_variacoes() -> None:
    for unidade in ("M2", "m2", "M²", "m²"):
        custo, aviso = calcular_custo_mp(
            Decimal("0.5"), Decimal("6"), Decimal("10"), None, unidade
        )
        assert custo == Decimal("30"), unidade
        assert aviso is None, unidade
