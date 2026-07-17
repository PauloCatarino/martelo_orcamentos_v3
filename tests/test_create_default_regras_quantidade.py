"""Tests for the default quantity-rules seed script (phase 8T.5.0)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.domain.regras_quantidade_expr import avaliar_regra_quantidade
from app.models import DefRegraQuantidade
from scripts.create_default_regras_quantidade import (
    DEFAULT_REGRAS_QUANTIDADE,
    DefaultRegrasQuantidadeResult,
    RegraSeed,
    ensure_default_regras_quantidade,
)


def test_seed_imports() -> None:
    assert len(DEFAULT_REGRAS_QUANTIDADE) == 10


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
        "UNIAO_TOPOS_128",
    } == codigos


def test_seed_expressions_are_all_valid() -> None:
    # The idempotent seed only inserts valid expressions: every example must
    # evaluate without an error against the sample context.
    contexto = {
        "COMP": 2000,
        "LARG": 600,
        "ESP": 19,
        "QT_PAI": 1,
        "MEDIDA_TOPO": 600,
        "NUM_TOPOS": 1,
    }
    for seed in DEFAULT_REGRAS_QUANTIDADE:
        quantidade, motivo = avaliar_regra_quantidade(seed.expressao, contexto)
        assert motivo is None, f"{seed.codigo}: {motivo}"
        assert quantidade >= 0


def test_result_dataclass() -> None:
    result = DefaultRegrasQuantidadeResult(criadas=3, reutilizadas=2, invalidas=0)

    assert result.criadas == 3
    assert result.reutilizadas == 2
    assert result.invalidas == 0


def test_seed_cria_as_dez_regras_sem_invalidas(session) -> None:
    # The seed validates each expression with the sample context, so every rule
    # (including the ones with COMP/LARG variables) is created — none ignored.
    resultado = ensure_default_regras_quantidade(session)

    assert resultado.criadas == 10
    assert resultado.invalidas == 0
    assert resultado.reutilizadas == 0

    codigos = set(
        session.execute(select(DefRegraQuantidade.codigo)).scalars().all()
    )
    assert codigos == {seed.codigo for seed in DEFAULT_REGRAS_QUANTIDADE}


def test_seed_e_idempotente(session) -> None:
    ensure_default_regras_quantidade(session)
    segunda = ensure_default_regras_quantidade(session)

    # The second run creates nothing and reuses all nine; no duplicates.
    assert segunda.criadas == 0
    assert segunda.reutilizadas == 10
    assert segunda.invalidas == 0
    total = session.execute(
        select(DefRegraQuantidade.codigo)
    ).scalars().all()
    assert len(total) == 10
