"""Tests for the basic production-time helpers (phase 8R). Times in minutes."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.tempos_producao import (
    AVISO_TEMPO_OPERACAO_SEM_DADOS,
    calcular_tempos_producao,
    calcular_tempos_producao_ligacoes,
    classificar_operacao,
    minutos_operacao_ligacao,
)


def _op(codigo, tipo, unidade_calculo, tempo_base=None, tempo_setup=None):
    return SimpleNamespace(
        codigo=codigo,
        tipo_operacao=tipo,
        unidade_calculo=unidade_calculo,
        tempo_base=tempo_base,
        tempo_setup=tempo_setup,
    )


def test_classificar_operacao() -> None:
    assert classificar_operacao("CORTE", "CORTE_PAINEL") == "corte"
    assert classificar_operacao("ORLAGEM", "ORLAGEM_PECA") == "orlagem"
    assert classificar_operacao("CNC", "CNC_MECANIZACAO") == "cnc"
    assert classificar_operacao("MONTAGEM", "MONTAGEM_GERAL") == "montagem"
    assert classificar_operacao("FURACAO", "FURACAO_MANUAL") == "manual"
    assert classificar_operacao("SETUP", "SETUP_MAQUINA") == "setup"
    assert classificar_operacao(None, None) is None


def test_tempo_corte_por_peca() -> None:
    ops = [_op("CORTE_PAINEL", "CORTE", "PECA", tempo_base=Decimal("2"))]
    tempos, faltam = calcular_tempos_producao(ops, Decimal("3"), Decimal("0"))
    assert tempos["corte"] == Decimal("6")
    assert faltam is False


def test_tempo_orlagem_por_ml() -> None:
    ops = [_op("ORLAGEM_PECA", "ORLAGEM", "ML", tempo_base=Decimal("1"))]
    tempos, _ = calcular_tempos_producao(ops, Decimal("1"), Decimal("5"))
    assert tempos["orlagem"] == Decimal("5")


def test_tempo_cnc_por_peca() -> None:
    ops = [_op("CNC_MECANIZACAO", "CNC", "PECA", tempo_base=Decimal("4"))]
    tempos, _ = calcular_tempos_producao(ops, Decimal("2"), Decimal("0"))
    assert tempos["cnc"] == Decimal("8")


def test_tempos_corte_orlagem_cnc() -> None:
    ops = [
        _op("CORTE_PAINEL", "CORTE", "PECA", tempo_base=Decimal("2")),
        _op("ORLAGEM_PECA", "ORLAGEM", "ML", tempo_base=Decimal("1")),
        _op("CNC_MECANIZACAO", "CNC", "PECA", tempo_base=Decimal("4")),
    ]
    tempos, faltam = calcular_tempos_producao(ops, Decimal("3"), Decimal("5"))
    assert tempos["corte"] == Decimal("6")
    assert tempos["orlagem"] == Decimal("5")
    assert tempos["cnc"] == Decimal("12")
    assert faltam is False


def test_sem_operacoes_tempos_zero() -> None:
    tempos, faltam = calcular_tempos_producao([], Decimal("3"), Decimal("5"))
    assert all(valor == Decimal("0") for valor in tempos.values())
    assert faltam is False


def test_orlagem_sem_orla_nao_avisa() -> None:
    ops = [_op("ORLAGEM_PECA", "ORLAGEM", "ML", tempo_base=None)]
    tempos, faltam = calcular_tempos_producao(ops, Decimal("3"), Decimal("0"))
    assert tempos["orlagem"] == Decimal("0")
    assert faltam is False  # no edging -> no diagnostic


def test_operacao_sem_tempo_marca_faltam() -> None:
    ops = [_op("CORTE_PAINEL", "CORTE", "PECA", tempo_base=None)]
    tempos, faltam = calcular_tempos_producao(ops, Decimal("3"), Decimal("0"))
    assert tempos["corte"] == Decimal("0")
    assert faltam is True


def test_tempo_setup_somado() -> None:
    ops = [_op("SETUP_MAQUINA", "SETUP", "SETUP", tempo_setup=Decimal("1.5"))]
    tempos, _ = calcular_tempos_producao(ops, Decimal("3"), Decimal("0"))
    assert tempos["setup"] == Decimal("1.5")


def test_aviso_constante() -> None:
    assert "Tempos de produção" in AVISO_TEMPO_OPERACAO_SEM_DADOS


# --- Times from the piece↔operation link (phase 8R.1) -------------------------


def _par(
    codigo,
    tipo,
    *,
    unidade_tempo=None,
    quantidade_base=None,
    tempo_setup_minutos=None,
    tempo_por_unidade_minutos=None,
    regra_calculo=None,
):
    """Build one (operacao, ligacao) pair as the service feeds the aggregator."""
    operacao = SimpleNamespace(codigo=codigo, tipo_operacao=tipo)
    ligacao = SimpleNamespace(
        unidade_tempo=unidade_tempo,
        quantidade_base=quantidade_base,
        tempo_setup_minutos=tempo_setup_minutos,
        tempo_por_unidade_minutos=tempo_por_unidade_minutos,
        regra_calculo=regra_calculo,
    )
    return operacao, ligacao


def test_tempos_ligacoes_corte_orlagem_cnc() -> None:
    pares = [
        _par("CORTE_PAINEL", "CORTE", unidade_tempo="PECA", tempo_por_unidade_minutos=Decimal("2")),
        _par("ORLAGEM_PECA", "ORLAGEM", unidade_tempo="ML", tempo_por_unidade_minutos=Decimal("1")),
        _par("CNC_MECANIZACAO", "CNC", unidade_tempo="PECA", tempo_por_unidade_minutos=Decimal("4")),
    ]

    tempos = calcular_tempos_producao_ligacoes(pares, None, Decimal("3"), Decimal("5"))

    assert tempos["corte"] == Decimal("6")  # PECA: 2 x QT 3
    assert tempos["orlagem"] == Decimal("5")  # ML orla: 1 x (2+3)
    assert tempos["cnc"] == Decimal("12")  # PECA: 4 x QT 3


def test_tempos_ligacoes_setup_somado() -> None:
    pares = [
        _par("CORTE_PAINEL", "CORTE", unidade_tempo="PECA",
             tempo_por_unidade_minutos=Decimal("2"), tempo_setup_minutos=Decimal("2")),
        _par("MONTAGEM_GERAL", "MONTAGEM", unidade_tempo="PECA",
             tempo_por_unidade_minutos=Decimal("1"), tempo_setup_minutos=Decimal("3")),
    ]

    tempos = calcular_tempos_producao_ligacoes(pares, None, Decimal("1"), Decimal("0"))

    assert tempos["setup"] == Decimal("5")  # 2 + 3 (all operations' setups)
    assert tempos["corte"] == Decimal("2")
    assert tempos["montagem"] == Decimal("1")


def test_tempos_ligacoes_montagem_hora() -> None:
    pares = [
        _par("MONTAGEM_GERAL", "MONTAGEM", unidade_tempo="HORA",
             quantidade_base=Decimal("0.5"), tempo_setup_minutos=Decimal("0")),
    ]

    tempos = calcular_tempos_producao_ligacoes(pares, None, Decimal("1"), Decimal("0"))

    assert tempos["montagem"] == Decimal("30")  # 0.5 h x 60


def test_tempos_ligacoes_sem_tempo_e_ignorado() -> None:
    pares = [_par("CORTE_PAINEL", "CORTE", unidade_tempo="PECA")]  # no minutes set

    tempos = calcular_tempos_producao_ligacoes(pares, None, Decimal("3"), Decimal("0"))

    assert all(valor == Decimal("0") for valor in tempos.values())


def test_minutos_operacao_orla_ml_usa_metros_de_orla() -> None:
    # ORLAGEM in ML uses the line's edging metres, not base x qt.
    setup, variavel = minutos_operacao_ligacao(
        bucket="orlagem",
        unidade_tempo="ML",
        quantidade_base=None,
        tempo_setup_minutos=None,
        tempo_por_unidade_minutos=Decimal("2"),
        regra_calculo=None,
        area_m2=None,
        qt_total=Decimal("3"),
        ml_orla_total=Decimal("5"),
    )
    assert (setup, variavel) == (Decimal("0"), Decimal("10"))  # 5 ml x 2


def test_minutos_operacao_regra_por_orlas_em_cnc() -> None:
    # 'Por orlas' makes even a non-orlagem bucket follow the edging metres.
    _setup, variavel = minutos_operacao_ligacao(
        bucket="cnc",
        unidade_tempo="ML",
        quantidade_base=None,
        tempo_setup_minutos=None,
        tempo_por_unidade_minutos=Decimal("2"),
        regra_calculo="POR_ORLAS",
        area_m2=None,
        qt_total=Decimal("3"),
        ml_orla_total=Decimal("5"),
    )
    assert variavel == Decimal("10")  # 5 ml x 2 (not base x qt)


def test_minutos_operacao_montagem_ml_nao_usa_orlas() -> None:
    # Assembly/manual stay on the per-unit path so they match the cost minutes.
    _setup, variavel = minutos_operacao_ligacao(
        bucket="montagem",
        unidade_tempo="ML",
        quantidade_base=None,
        tempo_setup_minutos=None,
        tempo_por_unidade_minutos=Decimal("2"),
        regra_calculo="POR_ORLAS",
        area_m2=None,
        qt_total=Decimal("3"),
        ml_orla_total=Decimal("5"),
    )
    assert variavel == Decimal("6")  # base(1) x QT 3 x 2, NOT the orla metres
