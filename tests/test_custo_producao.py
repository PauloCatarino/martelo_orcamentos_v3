"""Tests for the cutting/edging production-cost helpers (phase 8S.1)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.custo_producao import (
    MOTIVO_SEM_DADOS,
    MOTIVO_SEM_TARIFA,
    calcular_custo_corte,
    calcular_custo_orlagem,
    somar_custo_producao,
)


def test_custo_corte_com_setup() -> None:
    # 3.0 x 2 x 0.45 + 2 x 0.05 = 2.70 + 0.10 = 2.80.
    custo, motivo = calcular_custo_corte(
        Decimal("3.0"), Decimal("2"), Decimal("0.45"), Decimal("0.05")
    )
    assert custo == Decimal("2.80")
    assert motivo is None


def test_custo_corte_sem_setup() -> None:
    custo, _ = calcular_custo_corte(Decimal("3.0"), Decimal("2"), Decimal("0.45"), None)
    assert custo == Decimal("2.70")


def test_custo_corte_sem_tarifa() -> None:
    custo, motivo = calcular_custo_corte(Decimal("3.0"), Decimal("2"), None, None)
    assert custo is None
    assert motivo == MOTIVO_SEM_TARIFA


def test_custo_corte_sem_perimetro() -> None:
    custo, motivo = calcular_custo_corte(None, Decimal("2"), Decimal("0.45"), None)
    assert custo is None
    assert motivo == MOTIVO_SEM_DADOS


def test_custo_orlagem_com_setup() -> None:
    # 4.4 x 0.70 + 1 x 0.10 = 3.08 + 0.10 = 3.18.
    custo, motivo = calcular_custo_orlagem(
        Decimal("4.4"), Decimal("1"), Decimal("0.70"), Decimal("0.10")
    )
    assert custo == Decimal("3.18")
    assert motivo is None


def test_custo_orlagem_nao_multiplica_ml_por_qt() -> None:
    # ml_orla_total is already a line total: qt only affects the setup.
    custo, _ = calcular_custo_orlagem(Decimal("4.4"), Decimal("5"), Decimal("0.70"), None)
    assert custo == Decimal("3.08")  # 4.4 x 0.70, no qt on the metres


def test_custo_orlagem_sem_orla_fica_zero_sem_aviso() -> None:
    custo, motivo = calcular_custo_orlagem(
        Decimal("0"), Decimal("2"), Decimal("0.70"), Decimal("0.10")
    )
    assert custo == Decimal("0")
    assert motivo is None  # peça sem orla -> sem setup e sem aviso


def test_custo_orlagem_sem_tarifa_com_orla() -> None:
    custo, motivo = calcular_custo_orlagem(Decimal("4.4"), Decimal("1"), None, None)
    assert custo is None
    assert motivo == MOTIVO_SEM_TARIFA


def test_somar_custo_producao() -> None:
    assert somar_custo_producao(Decimal("2.80"), Decimal("3.18")) == Decimal("5.98")
    assert somar_custo_producao(Decimal("2.80"), None) == Decimal("2.80")
    assert somar_custo_producao(None, Decimal("0")) == Decimal("0")
    assert somar_custo_producao(None, None) is None  # all empty -> None
