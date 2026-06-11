"""Tests for the cutting/edging production-cost helpers (phase 8S.1)."""

from __future__ import annotations

from decimal import Decimal

from types import SimpleNamespace

from app.domain.custo_producao import (
    MOTIVO_SEM_DADOS,
    MOTIVO_SEM_ESCALOES,
    MOTIVO_SEM_TARIFA,
    calcular_custo_cnc,
    calcular_custo_corte,
    calcular_custo_orlagem,
    calcular_custo_por_minutos,
    calcular_tempo_operacao,
    selecionar_escalao_area,
    somar_custo_producao,
)


def _escalao(nivel, area_max_m2, preco_peca_std):
    return SimpleNamespace(
        nivel=nivel, area_max_m2=area_max_m2, preco_peca_std=preco_peca_std
    )


def _escaloes_cnc():
    return [
        _escalao(1, Decimal("0.25"), Decimal("1.20")),
        _escalao(2, Decimal("0.50"), Decimal("1.80")),
        _escalao(3, Decimal("1.00"), Decimal("2.60")),
        _escalao(4, Decimal("2.00"), Decimal("3.80")),
        _escalao(5, None, Decimal("5.50")),  # no limit
    ]


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
    # three partials (phase 8S.2)
    assert somar_custo_producao(
        Decimal("2.80"), Decimal("3.28"), Decimal("5.50")
    ) == Decimal("11.58")


def test_selecionar_escalao_limites() -> None:
    escaloes = _escaloes_cnc()
    assert selecionar_escalao_area(escaloes, Decimal("0.20")).nivel == 1
    assert selecionar_escalao_area(escaloes, Decimal("0.25")).nivel == 1  # <= limite
    assert selecionar_escalao_area(escaloes, Decimal("0.26")).nivel == 2
    assert selecionar_escalao_area(escaloes, Decimal("0.158")).nivel == 1
    # large area falls into the no-limit tier
    assert selecionar_escalao_area(escaloes, Decimal("2.625")).nivel == 5


def test_selecionar_escalao_sem_no_limite() -> None:
    escaloes = [_escalao(1, Decimal("0.25"), Decimal("1.20"))]
    # area exceeds the only finite tier -> no match
    assert selecionar_escalao_area(escaloes, Decimal("0.50")) is None


def test_custo_cnc_escalao_sem_limite() -> None:
    # 2.625 m2 -> no-limit tier (5.50) x qt 1 = 5.50.
    custo, motivo = calcular_custo_cnc(Decimal("2.625"), Decimal("1"), _escaloes_cnc())
    assert custo == Decimal("5.50")
    assert motivo is None


def test_custo_cnc_multiplica_por_qt() -> None:
    custo, _ = calcular_custo_cnc(Decimal("0.20"), Decimal("3"), _escaloes_cnc())
    assert custo == Decimal("3.60")  # 1.20 x 3


def test_custo_cnc_escaloes_inativos_ja_filtrados() -> None:
    # The repository passes only active tiers; an empty list -> SEM_ESCALOES.
    custo, motivo = calcular_custo_cnc(Decimal("0.20"), Decimal("1"), [])
    assert custo is None
    assert motivo == MOTIVO_SEM_ESCALOES


def test_custo_cnc_sem_area() -> None:
    custo, motivo = calcular_custo_cnc(None, Decimal("1"), _escaloes_cnc())
    assert custo is None
    assert motivo == MOTIVO_SEM_DADOS


def test_custo_cnc_area_excede_e_sem_no_limite() -> None:
    escaloes = [_escalao(1, Decimal("0.25"), Decimal("1.20"))]
    custo, motivo = calcular_custo_cnc(Decimal("0.50"), Decimal("1"), escaloes)
    assert custo is None
    assert motivo == MOTIVO_SEM_ESCALOES


def test_tempo_operacao_peca() -> None:
    # PECA: setup + (base × qt) × por_unidade = 2 + (2 × 3) × 0.5 = 5 min.
    setup, variavel = calcular_tempo_operacao(
        "PECA", Decimal("2"), Decimal("2"), Decimal("0.5"), None, Decimal("3")
    )
    assert setup == Decimal("2")
    assert variavel == Decimal("3")


def test_tempo_operacao_base_vazia_usa_qt() -> None:
    setup, variavel = calcular_tempo_operacao(
        "FURO", None, Decimal("0"), Decimal("0.5"), None, Decimal("4")
    )
    assert variavel == Decimal("2")  # (1 × 4) × 0.5


def test_tempo_operacao_m2() -> None:
    setup, variavel = calcular_tempo_operacao(
        "M2", None, Decimal("0"), Decimal("2"), Decimal("1.5"), Decimal("2")
    )
    assert variavel == Decimal("6")  # (1.5 × 2) × 2


def test_tempo_operacao_hora() -> None:
    # HORA: base hours × 60 (the operation time itself).
    setup, variavel = calcular_tempo_operacao(
        "HORA", Decimal("0.5"), Decimal("0"), None, None, Decimal("1")
    )
    assert setup == Decimal("0")
    assert variavel == Decimal("30")  # 0.5 × 60


def test_tempo_operacao_lote() -> None:
    setup, variavel = calcular_tempo_operacao(
        "LOTE", Decimal("3"), Decimal("1"), Decimal("2"), None, Decimal("10")
    )
    assert variavel == Decimal("6")  # 3 × 2 (qt ignored for LOTE)


def test_tempo_operacao_sem_tempos() -> None:
    setup, variavel = calcular_tempo_operacao(
        "PECA", Decimal("2"), None, None, None, Decimal("3")
    )
    assert setup is None and variavel is None


def test_custo_por_minutos() -> None:
    # tempo × €/h / 60 (multiply first -> exact for clean inputs).
    assert calcular_custo_por_minutos(Decimal("30"), Decimal("20")) == Decimal("10")
    assert calcular_custo_por_minutos(Decimal("10"), Decimal("30")) == Decimal("5")
    assert calcular_custo_por_minutos(None, Decimal("20")) is None
    assert calcular_custo_por_minutos(Decimal("10"), None) is None


def test_somar_custo_producao_quatro_parciais() -> None:
    assert somar_custo_producao(
        Decimal("2.80"), Decimal("3.28"), Decimal("11"), Decimal("3.33")
    ) == Decimal("20.41")
