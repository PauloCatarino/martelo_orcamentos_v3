"""Tests for the finishing panels (PAINEIS ACABAMENTO) seed script."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.peca_natureza_types import HORIZONTAL, MATERIAL, NEUTRA, VERTICAL
from app.domain.peca_types import SIMPLES
from app.models import DefOperacao, DefPeca, DefPecaOperacao, DefValuesetChave
from scripts.create_paineis_acabamento import (
    CHAVES,
    CODIGO_TAMPO_ANTIGO,
    GRUPO_PAINEIS_ACABAMENTO,
    PECAS,
    TAMPO,
    seed_paineis_acabamento,
)


def _criar_operacoes_base(session) -> None:
    """Create the cut/edging operations the seed attaches to each piece."""
    for codigo in ("CORTE_PAINEL", "ORLAGEM_PECA"):
        session.add(DefOperacao(codigo=codigo, nome=codigo.title(), ativo=True))
    session.flush()


def test_seed_constants() -> None:
    codigos = [seed.codigo for seed in PECAS]
    chaves = [seed.codigo for seed in CHAVES]

    assert len(codigos) == 5
    assert len(codigos) == len(set(codigos))
    assert len(chaves) == 5
    assert len(chaves) == len(set(chaves))
    assert set(chaves) == {seed.chave_material for seed in PECAS}
    for seed in PECAS:
        assert seed.codigo.endswith("_ACABAMENTO_2222")
        assert seed.codigo_orlas == "2222"


def test_seed_cria_chaves_e_pecas(session) -> None:
    _criar_operacoes_base(session)

    result = seed_paineis_acabamento(session)

    assert result.chaves_criadas == 5
    assert result.tampo_renomeado is False
    assert result.pecas_criadas == 5
    assert result.pecas_reutilizadas == 0
    assert result.operacoes_criadas == 10

    for seed in CHAVES:
        chave = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one()
        assert chave.tipo == "MATERIAL"
        assert chave.grupo == "MATERIAIS"
        assert chave.sistema is True
        assert chave.ativo is True

    pecas = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_PAINEIS_ACABAMENTO)
    ).scalars().all()
    assert len(pecas) == 5
    for peca in pecas:
        assert peca.tipo_peca == SIMPLES
        assert peca.natureza == MATERIAL
        assert (peca.orla_c1, peca.orla_c2, peca.orla_l1, peca.orla_l2) == (2, 2, 2, 2)
        assert peca.sem_material is False
        assert peca.ativo is True
        # Aceita acabamento, mas sem chaves: e o utilizador que o define no custeio.
        assert peca.permite_acabamento is True
        assert peca.chave_valueset_acabamento_sup is None
        assert peca.chave_valueset_acabamento_inf is None

    lateral = next(p for p in pecas if p.codigo == "LATERAL_ACABAMENTO_2222")
    assert lateral.orientacao == VERTICAL
    assert (lateral.formula_comp, lateral.formula_larg) == ("HM", "LM")
    assert lateral.chave_valueset_material == "MATERIAL_LATERAL_ACABAMENTO"

    fundo = next(p for p in pecas if p.codigo == "FUNDO_ACABAMENTO_2222")
    assert fundo.orientacao == HORIZONTAL
    assert (fundo.formula_comp, fundo.formula_larg) == ("LM", "PM")

    painel = next(p for p in pecas if p.codigo == "PAINEL_ACABAMENTO_2222")
    assert painel.orientacao == NEUTRA
    assert painel.funcao is None
    assert (painel.formula_comp, painel.formula_larg) == (None, None)

    operacoes = session.execute(
        select(DefPecaOperacao).where(DefPecaOperacao.def_peca_id == lateral.id)
    ).scalars().all()
    assert [operacao.ordem for operacao in operacoes] == [1, 2]
    assert all(operacao.ativo is True for operacao in operacoes)


def test_seed_renomeia_o_tampo_que_ja_existia(session) -> None:
    _criar_operacoes_base(session)
    session.add(
        DefPeca(
            codigo=CODIGO_TAMPO_ANTIGO,
            nome="Tampo[2222]",
            grupo=GRUPO_PAINEIS_ACABAMENTO,
            tipo_peca=SIMPLES,
            natureza=MATERIAL,
            orientacao=HORIZONTAL,
            chave_valueset_material="MATERIAL_TAMPOS",
            orla_c1=2,
            orla_c2=2,
            orla_l1=2,
            orla_l2=2,
            permite_acabamento=True,
            ativo=True,
        )
    )
    session.flush()

    result = seed_paineis_acabamento(session)

    assert result.tampo_renomeado is True
    # O tampo nao e recriado: so mudou de codigo, nome e chave.
    assert result.pecas_criadas == 4
    assert result.pecas_reutilizadas == 1

    assert session.execute(
        select(DefPeca).where(DefPeca.codigo == CODIGO_TAMPO_ANTIGO)
    ).scalar_one_or_none() is None

    tampo = session.execute(
        select(DefPeca).where(DefPeca.codigo == TAMPO.codigo)
    ).scalar_one()
    assert tampo.nome == TAMPO.nome
    assert tampo.chave_valueset_material == TAMPO.chave_material


def test_seed_e_idempotente(session) -> None:
    _criar_operacoes_base(session)

    seed_paineis_acabamento(session)
    result = seed_paineis_acabamento(session)

    assert result.chaves_criadas == 0
    assert result.tampo_renomeado is False
    assert result.pecas_criadas == 0
    assert result.pecas_reutilizadas == 5
    assert result.operacoes_criadas == 0

    pecas = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_PAINEIS_ACABAMENTO)
    ).scalars().all()
    assert len(pecas) == 5
