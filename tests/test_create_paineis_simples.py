"""Tests for the simple panels seed script."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.peca_natureza_types import MATERIAL, NEUTRA
from app.domain.peca_types import SIMPLES
from app.models import DefPeca, DefValuesetChave, DefValuesetModelo, DefValuesetModeloLinha
from scripts.create_paineis_simples import (
    CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
    GRUPO_PAINEIS_SIMPLES,
    MODELO_DEFAULT_CODIGO,
    PAINEIS_SIMPLES,
    PainelSeed,
    seed_paineis_simples,
)
from scripts.create_default_valueset_chaves import DEFAULT_VALUESET_CHAVES
from scripts.create_default_valueset_modelos import ROUPEIRO_STANDARD_LINHAS


def test_seed_constants() -> None:
    codigos = [seed.codigo for seed in PAINEIS_SIMPLES]

    assert len(codigos) == 7
    assert len(codigos) == len(set(codigos))
    assert "PAINEL_0000" in codigos
    assert "PAINEL_2222" in codigos
    for seed in PAINEIS_SIMPLES:
        assert isinstance(seed, PainelSeed)
        assert seed.codigo == f"PAINEL_{seed.codigo_orlas}"
        assert seed.nome == f"Painel[{seed.codigo_orlas}]"
        assert len(seed.codigo_orlas) == 4
        assert set(seed.codigo_orlas) <= {"0", "2"}


def test_chave_incluida_nos_seeds_default() -> None:
    codigos = {seed.codigo for seed in DEFAULT_VALUESET_CHAVES}
    chaves_modelo = {linha.chave for linha in ROUPEIRO_STANDARD_LINHAS}

    assert CHAVE_MATERIAL_PECAS_SIMPLIFICADAS in codigos
    assert CHAVE_MATERIAL_PECAS_SIMPLIFICADAS in chaves_modelo


def test_seed_cria_chave_e_paineis(session) -> None:
    result = seed_paineis_simples(session)

    assert result.chave_criada is True
    assert result.modelo_default_em_falta is True
    assert result.linha_modelo_criada is False
    assert result.paineis_criados == 7
    assert result.paineis_reutilizados == 0

    chave = session.execute(
        select(DefValuesetChave).where(
            DefValuesetChave.codigo == CHAVE_MATERIAL_PECAS_SIMPLIFICADAS
        )
    ).scalar_one()
    assert chave.tipo == "MATERIAL"
    assert chave.grupo == "MATERIAIS"
    assert chave.sistema is True

    paineis = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_PAINEIS_SIMPLES)
    ).scalars().all()
    assert len(paineis) == 7
    for painel in paineis:
        assert painel.tipo_peca == SIMPLES
        assert painel.natureza == MATERIAL
        assert painel.orientacao == NEUTRA
        assert painel.funcao is None
        assert painel.chave_valueset_material == CHAVE_MATERIAL_PECAS_SIMPLIFICADAS
        assert painel.permite_acabamento is False
        assert painel.sem_material is False
        assert painel.ativo is True

    painel_2020 = next(p for p in paineis if p.codigo == "PAINEL_2020")
    assert (
        painel_2020.orla_c1,
        painel_2020.orla_c2,
        painel_2020.orla_l1,
        painel_2020.orla_l2,
    ) == (2, 0, 2, 0)


def test_seed_e_idempotente(session) -> None:
    seed_paineis_simples(session)
    result = seed_paineis_simples(session)

    assert result.chave_criada is False
    assert result.paineis_criados == 0
    assert result.paineis_reutilizados == 7

    paineis = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_PAINEIS_SIMPLES)
    ).scalars().all()
    assert len(paineis) == 7


def test_seed_cria_linha_no_modelo_default_quando_existe(session) -> None:
    modelo = DefValuesetModelo(
        codigo=MODELO_DEFAULT_CODIGO,
        nome="Roupeiro standard",
        descricao=None,
        tipo="ROUPEIRO",
        ativo=True,
    )
    session.add(modelo)
    session.flush()

    result = seed_paineis_simples(session)

    assert result.modelo_default_em_falta is False
    assert result.linha_modelo_criada is True

    linha = session.execute(
        select(DefValuesetModeloLinha).where(
            DefValuesetModeloLinha.def_valueset_modelo_id == modelo.id,
            DefValuesetModeloLinha.chave == CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
        )
    ).scalar_one()
    assert linha.padrao is True
    assert linha.ativo is True

    resultado_repetido = seed_paineis_simples(session)
    assert resultado_repetido.linha_modelo_criada is False
