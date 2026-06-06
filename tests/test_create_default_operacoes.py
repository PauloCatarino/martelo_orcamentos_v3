"""Tests for the default machine and operation seed script."""

from __future__ import annotations

from app.domain.operacao_types import CNC, CORTE, MANUAL, ORLAGEM
from scripts.create_default_operacoes import (
    DEFAULT_MAQUINAS,
    DEFAULT_OPERACOES,
    OBSOLETE_MAQUINA_CODIGOS,
    DefaultOperacoesResult,
)


def test_default_maquinas_constants_import() -> None:
    maquinas_by_codigo = {seed.codigo: seed for seed in DEFAULT_MAQUINAS}

    assert set(maquinas_by_codigo) == {
        "CORTE",
        "ORLAGEM",
        "CNC_ABD",
        "CNC_VERTICAL",
        "CNC_HORIZONTAL",
        "CNC_5_EIXOS_ORLAGEM",
        "MONTAGEM",
        "MANUAL",
    }
    assert "CNC" not in maquinas_by_codigo
    assert maquinas_by_codigo["CORTE"].tipo == CORTE
    assert maquinas_by_codigo["ORLAGEM"].tipo == ORLAGEM
    assert maquinas_by_codigo["MANUAL"].tipo == MANUAL

    for codigo in ("CNC_ABD", "CNC_VERTICAL", "CNC_HORIZONTAL", "CNC_5_EIXOS_ORLAGEM"):
        assert maquinas_by_codigo[codigo].tipo == CNC
        assert maquinas_by_codigo[codigo].descricao


def test_obsolete_maquina_codigos_includes_generic_cnc() -> None:
    assert "CNC" in OBSOLETE_MAQUINA_CODIGOS


def test_default_operacoes_constants_import() -> None:
    operacoes_by_codigo = {seed.codigo: seed for seed in DEFAULT_OPERACOES}

    assert {
        "CORTE_PAINEL",
        "ORLAGEM_PECA",
        "CNC_MECANIZACAO",
        "FURACAO_MANUAL",
        "RASGO_MANUAL",
        "COLAGEM_MANUAL",
        "MONTAGEM_GERAL",
        "EMBALAMENTO",
        "SETUP_MAQUINA",
        "OPERACAO_MANUAL",
    } == set(operacoes_by_codigo)
    assert operacoes_by_codigo["CORTE_PAINEL"].maquina_codigo == "CORTE"
    assert operacoes_by_codigo["ORLAGEM_PECA"].unidade_calculo == "ML"
    assert operacoes_by_codigo["OPERACAO_MANUAL"].tipo_operacao == MANUAL
    assert operacoes_by_codigo["CNC_MECANIZACAO"].maquina_codigo == "CNC_VERTICAL"


def test_default_operacoes_result_dataclass() -> None:
    result = DefaultOperacoesResult(
        maquinas_criadas=4,
        maquinas_reutilizadas=4,
        maquinas_desativadas=1,
        operacoes_criadas=2,
        operacoes_reutilizadas=8,
    )

    assert result.maquinas_criadas == 4
    assert result.maquinas_reutilizadas == 4
    assert result.maquinas_desativadas == 1
    assert result.operacoes_criadas == 2
    assert result.operacoes_reutilizadas == 8
