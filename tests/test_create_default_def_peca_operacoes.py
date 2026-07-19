"""Tests for the default piece-operation seed script."""

from __future__ import annotations

from app.domain.regra_operacao_types import REGRA_OPERACAO_LABELS
from scripts.create_default_def_peca_operacoes import (
    DEFAULT_PECA_OPERACOES,
    DefaultPecaOperacoesResult,
    PecaOperacaoSeed,
)


def _by_codigo() -> dict[str, tuple[PecaOperacaoSeed, ...]]:
    return {codigo: seeds for codigo, seeds in DEFAULT_PECA_OPERACOES}


def test_seed_constants_import() -> None:
    assert len(DEFAULT_PECA_OPERACOES) > 0


def test_seed_covers_expected_pieces() -> None:
    codigos = {codigo for codigo, _ in DEFAULT_PECA_OPERACOES}

    assert {
        "PORTA",
        "PORTA_SIMPLES",
        "PRATELEIRA",
        "PRATELEIRA_AMOVIVEL",
        "LATERAL",
        "TAMPO",
        "FUNDO",
        "COSTA",
        "LADO_GAVETA",
        "FUNDO_GAVETA",
        "TRASEIRA_GAVETA",
        "FRENTE_GAVETA",
        "GAVETA",
    } <= codigos


def test_no_empty_codes_and_valid_ordens() -> None:
    for peca_codigo, seeds in DEFAULT_PECA_OPERACOES:
        assert peca_codigo.strip()
        assert len(seeds) > 0
        for seed in seeds:
            assert seed.operacao_codigo.strip()
            assert seed.ordem >= 1


def test_rules_are_valid() -> None:
    for _, seeds in DEFAULT_PECA_OPERACOES:
        for seed in seeds:
            assert seed.regra_calculo in REGRA_OPERACAO_LABELS


def test_porta_operacoes() -> None:
    porta = {seed.operacao_codigo: seed for seed in _by_codigo()["PORTA"]}

    assert set(porta) == {"CORTE_PAINEL", "ORLAGEM_PECA", "CNC_VERTICAL"}
    assert porta["CORTE_PAINEL"].ordem == 1
    assert porta["CORTE_PAINEL"].regra_calculo == "POR_PECA"
    assert porta["ORLAGEM_PECA"].regra_calculo == "POR_ORLAS"
    assert porta["CNC_VERTICAL"].metodo_calculo == "ESCALAO_AREA"


def test_costa_has_only_corte() -> None:
    costa = [seed.operacao_codigo for seed in _by_codigo()["COSTA"]]

    assert costa == ["CORTE_PAINEL"]


def test_gaveta_has_montagem_geral() -> None:
    gaveta = {seed.operacao_codigo: seed for seed in _by_codigo()["GAVETA"]}

    assert "MONTAGEM_GERAL" in gaveta
    assert gaveta["MONTAGEM_GERAL"].ordem == 10
    assert gaveta["MONTAGEM_GERAL"].regra_calculo == "POR_PECA"


def test_no_duplicate_operations_per_piece() -> None:
    for _, seeds in DEFAULT_PECA_OPERACOES:
        codigos = [seed.operacao_codigo for seed in seeds]
        assert len(codigos) == len(set(codigos))


def test_result_dataclass() -> None:
    result = DefaultPecaOperacoesResult(
        ligacoes_criadas=3,
        ligacoes_reutilizadas=2,
        pecas_nao_encontradas=1,
        operacoes_nao_encontradas=0,
        ligacoes_inativas=0,
    )

    assert result.ligacoes_criadas == 3
    assert result.ligacoes_reutilizadas == 2
    assert result.pecas_nao_encontradas == 1
