"""Tests for the default machine and operation seed script."""

from __future__ import annotations

from app.domain.operacao_types import CNC, CORTE, MANUAL, ORLAGEM
from scripts.create_default_operacoes import (
    DEFAULT_MAQUINAS,
    DEFAULT_OPERACOES,
    OBSOLETE_MAQUINA_CODIGOS,
    OBSOLETE_OPERACAO_CODIGOS,
    DefaultOperacoesResult,
)


def test_default_maquinas_constants_import() -> None:
    maquinas_by_codigo = {seed.codigo: seed for seed in DEFAULT_MAQUINAS}

    assert set(maquinas_by_codigo) == {
        "CORTE",
        "ORLAGEM",
        "CNC_ABD",
        "CNC_VERTICAL",
        "CNC_SANDWICH",
        "CNC_5_EIXOS",
        "REVESTIMENTO_SANDWICH",
        "MONTAGEM",
        "MANUAL",
    }
    assert "CNC" not in maquinas_by_codigo
    assert maquinas_by_codigo["CORTE"].tipo == CORTE
    assert maquinas_by_codigo["ORLAGEM"].tipo == ORLAGEM
    assert maquinas_by_codigo["MANUAL"].tipo == MANUAL
    assert maquinas_by_codigo["REVESTIMENTO_SANDWICH"].tipo == "REVESTIMENTO"
    assert maquinas_by_codigo["REVESTIMENTO_SANDWICH"].preco_m2_face_std is not None

    for codigo in ("CNC_ABD", "CNC_VERTICAL", "CNC_SANDWICH", "CNC_5_EIXOS"):
        assert maquinas_by_codigo[codigo].tipo == CNC
        assert maquinas_by_codigo[codigo].descricao
        assert maquinas_by_codigo[codigo].permite_furacao
        assert maquinas_by_codigo[codigo].permite_escaloes_area
        assert maquinas_by_codigo[codigo].preco_furo_std is not None

    # Capability matrix: ABD has no groove/pocket; SANDWICH has no pocket.
    assert not maquinas_by_codigo["CNC_ABD"].permite_rasgos
    assert not maquinas_by_codigo["CNC_ABD"].permite_pocket
    assert not maquinas_by_codigo["CNC_SANDWICH"].permite_pocket
    assert maquinas_by_codigo["CNC_SANDWICH"].permite_rasgos
    assert maquinas_by_codigo["CNC_VERTICAL"].permite_pocket
    assert maquinas_by_codigo["CNC_5_EIXOS"].permite_pocket


def test_obsolete_maquina_codigos_includes_generic_cnc() -> None:
    assert "CNC" in OBSOLETE_MAQUINA_CODIGOS
    assert "CNC_HORIZONTAL" in OBSOLETE_MAQUINA_CODIGOS
    assert "CNC_5_EIXOS_ORLAGEM" in OBSOLETE_MAQUINA_CODIGOS


def test_obsolete_operacao_codigos() -> None:
    assert set(OBSOLETE_OPERACAO_CODIGOS) == {"CNC_MECANIZACAO", "CNC_RASGO"}


def test_default_operacoes_constants_import() -> None:
    operacoes_by_codigo = {seed.codigo: seed for seed in DEFAULT_OPERACOES}

    assert {
        "CORTE_PAINEL",
        "ORLAGEM_PECA",
        "CNC_ABD",
        "CNC_VERTICAL",
        "CNC_SANDWICH",
        "CNC_5_EIXOS",
        "REVESTIMENTO_SANDWICH",
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
    # Each CNC operation points to its own machine (operation = machine).
    for codigo in ("CNC_ABD", "CNC_VERTICAL", "CNC_SANDWICH", "CNC_5_EIXOS"):
        assert operacoes_by_codigo[codigo].maquina_codigo == codigo
        assert operacoes_by_codigo[codigo].tipo_operacao == CNC
    assert (
        operacoes_by_codigo["REVESTIMENTO_SANDWICH"].maquina_codigo
        == "REVESTIMENTO_SANDWICH"
    )


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
