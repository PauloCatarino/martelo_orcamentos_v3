"""Tests for the trims (REMATES/GUARNICOES) seed script."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.medidas import validar_formula_dimensional
from app.domain.peca_funcao_types import REMATE
from app.domain.peca_natureza_types import MATERIAL, VERTICAL
from app.domain.peca_types import SIMPLES
from app.models import DefOperacao, DefPeca, DefPecaOperacao, DefValuesetChave
from scripts.create_remates_guarnicoes import (
    CHAVE_REMATES_VERTICAIS,
    GRUPO_REMATES_GUARNICOES,
    PECAS,
    seed_remates_guarnicoes,
)


def _criar_operacoes_base(session) -> None:
    """Create the cut/edging operations the seed attaches to each piece."""
    for codigo in ("CORTE_PAINEL", "ORLAGEM_PECA"):
        session.add(DefOperacao(codigo=codigo, nome=codigo.title(), ativo=True))
    session.flush()


def test_seed_constants() -> None:
    codigos = [seed.codigo for seed in PECAS]

    assert codigos == ["REMATE_VERTICAL_2220"]
    for seed in PECAS:
        assert seed.chave_material == CHAVE_REMATES_VERTICAIS
        assert len(seed.codigo_orlas) == 4


def test_formulas_do_remate_sao_validas() -> None:
    seed = PECAS[0]

    assert validar_formula_dimensional(seed.formula_comp, campo="Comp") == "HM"
    assert validar_formula_dimensional(seed.formula_larg, campo="Larg") == "100"


def test_seed_cria_chave_e_remate(session) -> None:
    _criar_operacoes_base(session)

    result = seed_remates_guarnicoes(session)

    assert result.chaves_criadas == 1
    assert result.pecas_criadas == 1
    assert result.pecas_reutilizadas == 0
    assert result.operacoes_criadas == 2

    chave = session.execute(
        select(DefValuesetChave).where(
            DefValuesetChave.codigo == CHAVE_REMATES_VERTICAIS
        )
    ).scalar_one()
    assert chave.nome == "Remates Verticais"
    assert chave.tipo == "MATERIAL"
    assert chave.grupo == "MATERIAIS"

    remate = session.execute(
        select(DefPeca).where(DefPeca.codigo == "REMATE_VERTICAL_2220")
    ).scalar_one()
    assert remate.grupo == GRUPO_REMATES_GUARNICOES
    assert remate.tipo_peca == SIMPLES
    assert remate.natureza == MATERIAL
    assert remate.orientacao == VERTICAL
    assert remate.funcao == REMATE
    assert (remate.formula_comp, remate.formula_larg) == ("HM", "100")
    assert (remate.orla_c1, remate.orla_c2, remate.orla_l1, remate.orla_l2) == (
        2,
        2,
        2,
        0,
    )
    assert remate.chave_valueset_material == CHAVE_REMATES_VERTICAIS
    assert remate.sem_material is False
    assert remate.ativo is True

    operacoes = session.execute(
        select(DefPecaOperacao).where(DefPecaOperacao.def_peca_id == remate.id)
    ).scalars().all()
    assert [operacao.ordem for operacao in operacoes] == [1, 2]
    assert all(operacao.ativo is True for operacao in operacoes)


def test_seed_e_idempotente(session) -> None:
    _criar_operacoes_base(session)

    seed_remates_guarnicoes(session)
    result = seed_remates_guarnicoes(session)

    assert result.chaves_criadas == 0
    assert result.pecas_criadas == 0
    assert result.pecas_reutilizadas == 1
    assert result.operacoes_criadas == 0

    pecas = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_REMATES_GUARNICOES)
    ).scalars().all()
    assert len(pecas) == 1
