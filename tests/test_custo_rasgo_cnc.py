from decimal import Decimal

from app.domain.custo_producao import (
    MOTIVO_MAQUINA_INCOMPATIVEL,
    calcular_comprimento_rasgo_ml,
    calcular_custo_rasgo_cnc,
)


def test_comprimento_geometrico_quatro_lados() -> None:
    assert calcular_comprimento_rasgo_ml(Decimal("2000"), Decimal("600"), 2, 2) == Decimal("5.2")


def test_custo_rasgo_nao_duplica_percurso_da_fresa() -> None:
    custo, motivo = calcular_custo_rasgo_cnc(
        Decimal("2000"), Decimal("600"), Decimal("1"), 2, 2, Decimal("0.40")
    )
    assert motivo is None
    assert custo == Decimal("2.080")


def test_custo_rasgo_led_um_comprimento_e_quantidade() -> None:
    custo, motivo = calcular_custo_rasgo_cnc(
        Decimal("1800"), None, Decimal("2"), 1, 0, Decimal("0.40")
    )
    assert motivo is None
    assert custo == Decimal("1.440")


def test_cnc_sem_fresagem_rejeita_rasgo() -> None:
    custo, motivo = calcular_custo_rasgo_cnc(
        Decimal("1000"), Decimal("500"), 1, 1, 0, Decimal("0.40"), False
    )
    assert custo is None
    assert motivo == MOTIVO_MAQUINA_INCOMPATIVEL
