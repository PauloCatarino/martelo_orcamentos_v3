"""Tests for the default quantity-rules seed script (phase 8T.5.0)."""

from __future__ import annotations

from app.domain.regras_quantidade_expr import avaliar_regra_quantidade
from scripts.create_default_regras_quantidade import (
    DEFAULT_REGRAS_QUANTIDADE,
    DefaultRegrasQuantidadeResult,
    RegraSeed,
)


def test_seed_imports() -> None:
    assert len(DEFAULT_REGRAS_QUANTIDADE) == 9


def test_seed_entries_have_structure() -> None:
    for seed in DEFAULT_REGRAS_QUANTIDADE:
        assert isinstance(seed, RegraSeed)
        assert seed.codigo.strip()
        assert seed.nome.strip()
        assert seed.expressao.strip()
        assert seed.descricao.strip()


def test_seed_codes_are_unique() -> None:
    codigos = [seed.codigo for seed in DEFAULT_REGRAS_QUANTIDADE]

    assert len(codigos) == len(set(codigos))


def test_seed_contains_expected_codes() -> None:
    codigos = {seed.codigo for seed in DEFAULT_REGRAS_QUANTIDADE}

    assert {
        "DOBRADICA",
        "PUXADOR",
        "PES_NIVELADORES",
        "SUPORTE_PRATELEIRA",
        "SUPORTE_TERMINAL_VARAO",
        "SUPORTE_VARAO_CENTRAL",
        "COSTA_NIVELADORES",
        "RODAPE_GRAMPAS",
        "VARAO_SPP",
    } == codigos


def test_seed_expressions_are_all_valid() -> None:
    # The idempotent seed only inserts valid expressions: every example must
    # evaluate without an error against the sample context.
    contexto = {"COMP": 2000, "LARG": 600, "ESP": 19, "QT_PAI": 1}
    for seed in DEFAULT_REGRAS_QUANTIDADE:
        quantidade, motivo = avaliar_regra_quantidade(seed.expressao, contexto)
        assert motivo is None, f"{seed.codigo}: {motivo}"
        assert quantidade >= 0


def test_result_dataclass() -> None:
    result = DefaultRegrasQuantidadeResult(criadas=3, reutilizadas=2, invalidas=0)

    assert result.criadas == 3
    assert result.reutilizadas == 2
    assert result.invalidas == 0
