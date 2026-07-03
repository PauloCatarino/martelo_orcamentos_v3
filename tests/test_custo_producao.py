"""Tests for the cutting/edging production-cost helpers (phase 8S.1)."""

from __future__ import annotations

from decimal import Decimal

from types import SimpleNamespace

from app.domain.custo_producao import (
    MOTIVO_SEM_DADOS,
    MOTIVO_SEM_ESCALOES,
    MOTIVO_SEM_TARIFA,
    aplicar_fator_serie,
    calcular_custo_cnc,
    calcular_custo_corte,
    calcular_custo_orlagem_lados,
    calcular_custo_por_minutos,
    calcular_tempo_operacao,
    escolher_tarifa,
    preco_peca_escalao,
    selecionar_escalao_area,
    somar_custo_producao,
)


def _escalao(nivel, area_max_m2, preco_peca_std, preco_peca_serie=None):
    return SimpleNamespace(
        nivel=nivel,
        area_max_m2=area_max_m2,
        preco_peca_std=preco_peca_std,
        preco_peca_serie=preco_peca_serie,
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


def test_custo_orlagem_lados_com_setup() -> None:
    # [2111]: 2 lados comp > 1500 (2 x 1.10) + 2 lados larg <= 1500 (2 x 0.55)
    # + setup 0.10 = 3.40.
    custo, motivo = calcular_custo_orlagem_lados(
        "2111",
        Decimal("2530"),
        Decimal("610"),
        Decimal("1"),
        Decimal("0.55"),
        Decimal("1.10"),
        Decimal("1500"),
        Decimal("0.10"),
    )
    assert custo == Decimal("3.40")
    assert motivo is None


def test_custo_orlagem_lado_1500_usa_escalao_baixo() -> None:
    custo, motivo = calcular_custo_orlagem_lados(
        "1000",
        Decimal("1500"),
        Decimal("600"),
        Decimal("1"),
        Decimal("0.55"),
        Decimal("1.10"),
        Decimal("1500"),
        None,
    )
    assert custo == Decimal("0.55")
    assert motivo is None


def test_custo_orlagem_sem_orla_fica_zero_sem_setup() -> None:
    custo, motivo = calcular_custo_orlagem_lados(
        "0000",
        Decimal("2530"),
        Decimal("610"),
        Decimal("2"),
        Decimal("0.55"),
        Decimal("1.10"),
        Decimal("1500"),
        Decimal("0.10"),
    )
    assert custo == Decimal("0")
    assert motivo is None  # peça sem orla -> sem setup e sem aviso


def test_custo_orlagem_tarifa_em_falta_com_orla() -> None:
    custo, motivo = calcular_custo_orlagem_lados(
        "1000",
        Decimal("1000"),
        Decimal("600"),
        Decimal("1"),
        None,
        Decimal("1.10"),
        Decimal("1500"),
        None,
    )
    assert custo is None
    assert motivo == MOTIVO_SEM_TARIFA


def test_custo_orlagem_medida_em_falta_com_lado_orlado() -> None:
    custo, motivo = calcular_custo_orlagem_lados(
        "1000",
        None,
        Decimal("600"),
        Decimal("1"),
        Decimal("0.55"),
        Decimal("1.10"),
        Decimal("1500"),
        None,
    )
    assert custo is None
    assert motivo == MOTIVO_SEM_DADOS


def test_custo_orlagem_serie_com_fallback_std() -> None:
    preco_curto, fallback_curto = escolher_tarifa(
        Decimal("0.55"), None, usar_serie=True
    )
    preco_longo, fallback_longo = escolher_tarifa(
        Decimal("1.10"), Decimal("0.80"), usar_serie=True
    )
    custo, motivo = calcular_custo_orlagem_lados(
        "1010",
        Decimal("2530"),
        Decimal("610"),
        Decimal("1"),
        preco_curto,
        preco_longo,
        Decimal("1500"),
        None,
    )
    assert fallback_curto is True
    assert fallback_longo is False
    assert custo == Decimal("1.35")  # lado longo SERIE + lado curto fallback STD
    assert motivo is None


def test_custo_orlagem_qt_duplica_lados_e_setup() -> None:
    custo, motivo = calcular_custo_orlagem_lados(
        "2111",
        Decimal("2530"),
        Decimal("610"),
        Decimal("2"),
        Decimal("0.55"),
        Decimal("1.10"),
        Decimal("1500"),
        Decimal("0.10"),
    )
    assert custo == Decimal("6.80")
    assert motivo is None


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


def test_escolher_tarifa_std() -> None:
    valor, fallback = escolher_tarifa(Decimal("0.45"), Decimal("0.35"), False)
    assert valor == Decimal("0.45")
    assert fallback is False


def test_escolher_tarifa_serie() -> None:
    valor, fallback = escolher_tarifa(Decimal("0.45"), Decimal("0.35"), True)
    assert valor == Decimal("0.35")
    assert fallback is False


def test_escolher_tarifa_serie_fallback_std() -> None:
    valor, fallback = escolher_tarifa(Decimal("0.45"), None, True)
    assert valor == Decimal("0.45")
    assert fallback is True


def test_escolher_tarifa_ambas_vazias() -> None:
    assert escolher_tarifa(None, None, False) == (None, False)
    valor, fallback = escolher_tarifa(None, None, True)
    assert valor is None


def test_preco_peca_escalao_serie_e_fallback() -> None:
    escalao = _escalao(1, Decimal("0.25"), Decimal("1.20"), Decimal("0.90"))
    assert preco_peca_escalao(escalao, False) == (Decimal("1.20"), False)
    assert preco_peca_escalao(escalao, True) == (Decimal("0.90"), False)

    sem_serie = _escalao(1, Decimal("0.25"), Decimal("1.20"))
    assert preco_peca_escalao(sem_serie, True) == (Decimal("1.20"), True)
    assert preco_peca_escalao(None, True) == (None, False)


def test_custo_cnc_serie_usa_preco_serie() -> None:
    escaloes = [_escalao(1, Decimal("0.25"), Decimal("1.20"), Decimal("0.90"))]
    custo, motivo = calcular_custo_cnc(
        Decimal("0.2"), Decimal("2"), escaloes, usar_serie=True
    )
    assert custo == Decimal("1.80")  # 0.90 x 2
    assert motivo is None


def test_custo_cnc_serie_fallback_std() -> None:
    escaloes = [_escalao(1, Decimal("0.25"), Decimal("1.20"))]  # sem SERIE
    custo, _ = calcular_custo_cnc(
        Decimal("0.2"), Decimal("2"), escaloes, usar_serie=True
    )
    assert custo == Decimal("2.40")  # fallback ao STD 1.20 x 2


def test_custo_cnc_std_regressao_sem_usar_serie() -> None:
    escaloes = [_escalao(1, Decimal("0.25"), Decimal("1.20"), Decimal("0.90"))]
    custo, _ = calcular_custo_cnc(Decimal("0.2"), Decimal("2"), escaloes)
    assert custo == Decimal("2.40")  # default STD inalterado


def test_aplicar_fator_serie() -> None:
    assert aplicar_fator_serie(Decimal("3.00"), Decimal("0.90")) == Decimal("2.700")
    assert aplicar_fator_serie(Decimal("3.00"), None) == Decimal("3.00")
    assert aplicar_fator_serie(Decimal("3.00"), Decimal("0")) == Decimal("3.00")
    assert aplicar_fator_serie(None, Decimal("0.90")) is None
