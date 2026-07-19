"""Tests for the method-driven CNC/coating cost dispatcher."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.custo_cnc_metodo import (
    TarifasCncMaquina,
    calcular_custo_cnc_por_metodo,
)
from app.domain.custo_producao import (
    MOTIVO_MAQUINA_INCOMPATIVEL,
    MOTIVO_SEM_DADOS,
    MOTIVO_SEM_ESCALOES,
    MOTIVO_SEM_TARIFA,
)
from app.domain.metodo_calculo_types import (
    ESCALAO_AREA,
    FURACAO,
    POCKET,
    RASGO,
    REVESTIMENTO,
    TEMPO,
)


def _escalao(nivel, area_max_m2, std, serie=None):
    return SimpleNamespace(
        nivel=nivel,
        area_max_m2=area_max_m2,
        preco_peca_std=std,
        preco_peca_serie=serie,
    )


def _tarifas(**kwargs):
    base = dict(
        escaloes_ativos=(
            _escalao(1, Decimal("0.25"), Decimal("1.20"), Decimal("0.90")),
            _escalao(2, None, Decimal("5.50"), Decimal("4.10")),
        ),
        preco_rasgo_ml=Decimal("0.40"),
        preco_furo=Decimal("0.12"),
        custo_hora=Decimal("60"),
        preco_m2_face=Decimal("3.25"),
    )
    base.update(kwargs)
    return TarifasCncMaquina(**base)


def _calc(metodo, tarifas=None, **kwargs):
    params = dict(
        metodo=metodo,
        area_m2=Decimal("0.24"),
        comp_real=Decimal("600"),
        larg_real=Decimal("400"),
        qt_total=Decimal("1"),
        quantidade_base=None,
        rasgo_qt_comp=0,
        rasgo_qt_larg=0,
        tempo_setup_minutos=None,
        tempo_por_unidade_minutos=None,
        unidade_tempo=None,
        tarifas=tarifas or _tarifas(),
        usar_serie=False,
    )
    params.update(kwargs)
    return calcular_custo_cnc_por_metodo(**params)


def test_escalao_area_std_e_serie() -> None:
    # 600x400 = 0.24 m² -> tier 1: 1.20 STD / 0.90 SERIE; QT 10.
    custo, tempo, motivo = _calc(ESCALAO_AREA, qt_total=Decimal("10"))
    assert (custo, tempo, motivo) == (Decimal("12.00"), None, None)
    custo, _, _ = _calc(ESCALAO_AREA, qt_total=Decimal("10"), usar_serie=True)
    assert custo == Decimal("9.00")


def test_escalao_area_maquina_sem_capacidade() -> None:
    custo, tempo, motivo = _calc(
        ESCALAO_AREA, tarifas=_tarifas(permite_escaloes_area=False)
    )
    assert (custo, tempo) == (None, None)
    assert motivo == MOTIVO_MAQUINA_INCOMPATIVEL


def test_escalao_area_sem_escaloes() -> None:
    _, _, motivo = _calc(ESCALAO_AREA, tarifas=_tarifas(escaloes_ativos=()))
    assert motivo == MOTIVO_SEM_ESCALOES


def test_tempo_pocket_quatro_minutos() -> None:
    # Pocket: 4 min per piece -> 4/60 × 60 €/h = 4.00 €; tempo returned.
    custo, tempo, motivo = _calc(
        TEMPO,
        quantidade_base=Decimal("1"),
        tempo_por_unidade_minutos=Decimal("4"),
        unidade_tempo="PECA",
    )
    assert custo == Decimal("4.00")
    assert tempo == Decimal("4")
    assert motivo is None


def test_pocket_usa_tempo_e_exige_capacidade_da_maquina() -> None:
    params = dict(
        quantidade_base=Decimal("1"),
        tempo_por_unidade_minutos=Decimal("4"),
        unidade_tempo="PECA",
    )
    custo, tempo, motivo = _calc(
        POCKET, tarifas=_tarifas(permite_pocket=True), **params
    )
    assert (custo, tempo, motivo) == (Decimal("4.00"), Decimal("4"), None)

    custo, tempo, motivo = _calc(POCKET, **params)
    assert (custo, tempo, motivo) == (None, None, MOTIVO_MAQUINA_INCOMPATIVEL)


def test_tempo_sem_tempos_configurados() -> None:
    custo, tempo, motivo = _calc(TEMPO)
    assert (custo, tempo) == (None, None)
    assert motivo == MOTIVO_SEM_DADOS


def test_tempo_sem_custo_hora_devolve_tempo() -> None:
    custo, tempo, motivo = _calc(
        TEMPO,
        tarifas=_tarifas(custo_hora=None),
        tempo_por_unidade_minutos=Decimal("4"),
    )
    assert custo is None
    assert tempo == Decimal("4")
    assert motivo == MOTIVO_SEM_TARIFA


def test_furacao_dobradica() -> None:
    # 3 holes × 4 hinges × 0.12 €/hole = 1.44 €.
    custo, tempo, motivo = _calc(
        FURACAO, quantidade_base=Decimal("3"), qt_total=Decimal("4")
    )
    assert (custo, tempo, motivo) == (Decimal("1.44"), None, None)


def test_furacao_sem_tarifa_e_sem_furos() -> None:
    _, _, motivo = _calc(
        FURACAO, quantidade_base=Decimal("3"), tarifas=_tarifas(preco_furo=None)
    )
    assert motivo == MOTIVO_SEM_TARIFA
    _, _, motivo = _calc(FURACAO, quantidade_base=None)
    assert motivo == MOTIVO_SEM_DADOS


def test_furacao_maquina_sem_capacidade() -> None:
    _, _, motivo = _calc(
        FURACAO,
        quantidade_base=Decimal("3"),
        tarifas=_tarifas(permite_furacao=False),
    )
    assert motivo == MOTIVO_MAQUINA_INCOMPATIVEL


def test_rasgo_calha_led() -> None:
    # 1 groove along COMP 1200 mm -> 1.20 ML × 0.40 = 0.48 €.
    custo, tempo, motivo = _calc(
        RASGO, comp_real=Decimal("1200"), rasgo_qt_comp=1
    )
    assert (custo, tempo, motivo) == (Decimal("0.480"), None, None)


def test_rasgo_maquina_sem_capacidade() -> None:
    _, _, motivo = _calc(
        RASGO, rasgo_qt_comp=1, tarifas=_tarifas(permite_rasgos=False)
    )
    assert motivo == MOTIVO_MAQUINA_INCOMPATIVEL


def test_revestimento_uma_e_duas_faces() -> None:
    # 2.0 m² × faces × 3.25 €/m².
    custo, _, motivo = _calc(
        REVESTIMENTO, area_m2=Decimal("2"), quantidade_base=Decimal("1")
    )
    assert (custo, motivo) == (Decimal("6.50"), None)
    custo, _, _ = _calc(
        REVESTIMENTO, area_m2=Decimal("2"), quantidade_base=Decimal("2")
    )
    assert custo == Decimal("13.00")


def test_revestimento_faces_vazias_conta_uma() -> None:
    custo, _, motivo = _calc(REVESTIMENTO, area_m2=Decimal("2"))
    assert (custo, motivo) == (Decimal("6.50"), None)


def test_revestimento_sem_tarifa() -> None:
    _, _, motivo = _calc(
        REVESTIMENTO, area_m2=Decimal("2"), tarifas=_tarifas(preco_m2_face=None)
    )
    assert motivo == MOTIVO_SEM_TARIFA


def test_metodo_desconhecido_ou_vazio() -> None:
    custo, tempo, motivo = _calc(None)
    assert (custo, tempo) == (None, None)
    assert motivo == MOTIVO_SEM_DADOS
    _, _, motivo = _calc("XPTO")
    assert motivo == MOTIVO_SEM_DADOS


def test_soma_furacao_mais_rasgo_na_mesma_peca() -> None:
    # New model: several method lines on the same piece just add up.
    furacao, _, _ = _calc(
        FURACAO, quantidade_base=Decimal("8"), qt_total=Decimal("2")
    )
    rasgo, _, _ = _calc(
        RASGO, larg_real=Decimal("600"), rasgo_qt_larg=1, qt_total=Decimal("2")
    )
    assert furacao + rasgo == Decimal("1.92") + Decimal("0.480")
