"""Tests for the basic production-time helpers (phase 8R). Times in minutes."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.tempos_producao import (
    AVISO_TEMPO_OPERACAO_SEM_DADOS,
    calcular_tempos_producao,
    classificar_operacao,
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
