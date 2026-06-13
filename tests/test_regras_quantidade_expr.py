"""Tests for the configurable quantity-rule expression engine (phase 8T.5.0)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.regras_quantidade_expr import (
    CONTEXTO_EXEMPLO,
    FUNCOES_REGRA,
    VARIAVEIS_REGRA,
    avaliar_regra_quantidade,
)

# The seed expressions (kept here so the engine tests are self-contained).
DOBRADICA = (
    "(2 if COMP <= 850 else 3 if COMP <= 1600 else 4 if COMP <= 2000 "
    "else 5 if COMP <= 2600 else 6 + ((COMP - 2600) // 600)) "
    "+ (1 if LARG >= 605 else 0)"
)
PES_NIVELADORES = (
    "4 if COMP < 650 and LARG < 800 else 6 if COMP >= 650 and LARG < 800 else 8"
)
SUPORTE_PRATELEIRA = (
    "8 if COMP >= 1100 and LARG >= 800 else "
    "6 if (COMP >= 1100 or (LARG > 800 and COMP < 1100)) else 4"
)


def _q(expressao: str, **contexto) -> int:
    """Evaluate an expression and assert it succeeded; return the quantity."""
    quantidade, motivo = avaliar_regra_quantidade(expressao, contexto)
    assert motivo is None, motivo
    return quantidade


def test_constantes_basicas() -> None:
    assert _q("1") == 1
    assert _q("0") == 0
    assert _q("2") == 2


def test_arredonda_para_cima_e_minimo_zero() -> None:
    assert _q("COMP / 600", COMP=601) == 2  # 1.0016 -> 2
    assert _q("COMP / 600", COMP=600) == 1  # exactly 1
    assert _q("3 - 10") == 0  # negative clamped to 0


def test_divisao_inteira_floordiv() -> None:
    assert _q("COMP // 600", COMP=1250) == 2
    assert _q("(COMP - 2600) // 600", COMP=3800) == 2


def test_funcoes_ceil_floor_min_max() -> None:
    assert _q("CEIL(COMP / 600)", COMP=601) == 2
    assert _q("FLOOR(COMP / 600)", COMP=1199) == 1
    assert _q("MIN(COMP, LARG)", COMP=2000, LARG=600) == 600
    assert _q("MAX(COMP, LARG, 100)", COMP=2000, LARG=600) == 2000


def test_comparacoes_e_booleanos() -> None:
    assert _q("5 if COMP > 1000 and LARG < 700 else 0", COMP=1200, LARG=600) == 5
    assert _q("5 if COMP > 1000 and LARG < 700 else 0", COMP=900, LARG=600) == 0
    assert _q("1 if not (COMP == 0) else 0", COMP=10) == 1
    assert _q("1 if COMP >= 100 or LARG >= 100 else 0", COMP=10, LARG=200) == 1


def test_dobradica_por_altura_da_porta() -> None:
    assert _q(DOBRADICA, COMP=850, LARG=600) == 2
    assert _q(DOBRADICA, COMP=851, LARG=600) == 3
    assert _q(DOBRADICA, COMP=1600, LARG=600) == 3
    assert _q(DOBRADICA, COMP=1601, LARG=600) == 4
    assert _q(DOBRADICA, COMP=2000, LARG=600) == 4
    assert _q(DOBRADICA, COMP=2600, LARG=600) == 5
    assert _q(DOBRADICA, COMP=2601, LARG=600) == 6  # 6 + (1 // 600 = 0)
    assert _q(DOBRADICA, COMP=3200, LARG=600) == 7  # 6 + (600 // 600 = 1)
    assert _q(DOBRADICA, COMP=3800, LARG=600) == 8  # 6 + (1200 // 600 = 2)
    # +1 hinge when LARG >= 605.
    assert _q(DOBRADICA, COMP=2000, LARG=605) == 5
    assert _q(DOBRADICA, COMP=2000, LARG=604) == 4


def test_pes_niveladores() -> None:
    assert _q(PES_NIVELADORES, COMP=600, LARG=700) == 4
    assert _q(PES_NIVELADORES, COMP=650, LARG=700) == 6
    assert _q(PES_NIVELADORES, COMP=700, LARG=799) == 6
    assert _q(PES_NIVELADORES, COMP=700, LARG=800) == 8
    assert _q(PES_NIVELADORES, COMP=600, LARG=900) == 8


def test_suporte_prateleira() -> None:
    assert _q(SUPORTE_PRATELEIRA, COMP=1100, LARG=800) == 8
    assert _q(SUPORTE_PRATELEIRA, COMP=1200, LARG=700) == 6  # COMP >= 1100
    assert _q(SUPORTE_PRATELEIRA, COMP=900, LARG=900) == 6  # LARG > 800 and COMP < 1100
    assert _q(SUPORTE_PRATELEIRA, COMP=900, LARG=700) == 4


def test_suporte_varao_central_e_terminais() -> None:
    assert _q("1 if COMP > 1100 else 0", COMP=1101) == 1
    assert _q("1 if COMP > 1100 else 0", COMP=1100) == 0
    assert _q("2") == 2


def test_expressao_vazia_devolve_motivo() -> None:
    quantidade, motivo = avaliar_regra_quantidade("", CONTEXTO_EXEMPLO)
    assert quantidade is None
    assert motivo is not None


def test_sintaxe_invalida_devolve_motivo() -> None:
    quantidade, motivo = avaliar_regra_quantidade("2 +", CONTEXTO_EXEMPLO)
    assert quantidade is None
    assert "sintaxe" in motivo.lower()


def test_variavel_desconhecida_devolve_motivo() -> None:
    quantidade, motivo = avaliar_regra_quantidade("ALTURA + 1", CONTEXTO_EXEMPLO)
    assert quantidade is None
    assert "ALTURA" in motivo


def test_funcao_nao_permitida_devolve_motivo() -> None:
    quantidade, motivo = avaliar_regra_quantidade("ABS(COMP)", CONTEXTO_EXEMPLO)
    assert quantidade is None
    assert "ABS" in motivo


def test_divisao_por_zero_devolve_motivo() -> None:
    quantidade, motivo = avaliar_regra_quantidade("COMP / 0", CONTEXTO_EXEMPLO)
    assert quantidade is None
    assert "zero" in motivo.lower()


def test_elemento_nao_permitido_devolve_motivo() -> None:
    # Attribute access / dunder must never be allowed (no eval, AST whitelist).
    quantidade, motivo = avaliar_regra_quantidade(
        "COMP.__class__", CONTEXTO_EXEMPLO
    )
    assert quantidade is None
    assert motivo is not None


def test_variaveis_e_funcoes_publicadas() -> None:
    assert VARIAVEIS_REGRA == ("COMP", "LARG", "ESP", "QT_PAI")
    assert set(FUNCOES_REGRA) == {"CEIL", "FLOOR", "MIN", "MAX"}
    assert CONTEXTO_EXEMPLO["COMP"] == Decimal("2000")
