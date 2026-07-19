"""Tests for the additive sandwich-panel catalog seed."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.metodo_calculo_types import REVESTIMENTO
from app.domain.peca_natureza_types import CONJUNTO, MATERIAL
from app.domain.peca_types import COMPOSTA, SIMPLES
from app.models import DefOperacao, DefPeca, DefPecaComponente, DefPecaOperacao
from scripts.create_default_pecas_sandwich import (
    CHAVE_MATERIAL_FACE,
    CHAVE_MATERIAL_NUCLEO,
    COMPONENTES_SANDWICH,
    GRUPO_PAINEIS_SANDWICH,
    OPERACAO_REVESTIMENTO_CODIGO,
    PECAS_SANDWICH,
    seed_pecas_sandwich,
)


def _criar_operacao_revestimento(session) -> DefOperacao:
    operacao = DefOperacao(
        codigo=OPERACAO_REVESTIMENTO_CODIGO,
        nome="Revestimento Sandwich",
        tipo_operacao=REVESTIMENTO,
        unidade_calculo="M2",
        ativo=True,
    )
    session.add(operacao)
    session.flush()
    return operacao


def test_seeds_sandwich_declaram_catalogo_esperado() -> None:
    assert [seed.codigo for seed in PECAS_SANDWICH] == [
        "FACE_SANDWICH",
        "NUCLEO_SANDWICH",
        "PAINEL_SANDWICH_1F",
        "PAINEL_SANDWICH_2F",
    ]
    assert len(COMPONENTES_SANDWICH) == 5
    assert {CHAVE_MATERIAL_FACE, CHAVE_MATERIAL_NUCLEO} == {
        seed.chave_valueset_material
        for seed in PECAS_SANDWICH
        if seed.chave_valueset_material is not None
    }


def test_seed_cria_pecas_componentes_e_operacao_por_face(session) -> None:
    _criar_operacao_revestimento(session)

    result = seed_pecas_sandwich(session)

    assert result.pecas_criadas == 4
    assert result.componentes_criados == 5
    assert result.operacao_revestimento_criada is True
    assert result.operacao_revestimento_em_falta is False

    pecas = {
        p.codigo: p
        for p in session.execute(
            select(DefPeca).where(DefPeca.grupo == GRUPO_PAINEIS_SANDWICH)
        ).scalars()
    }
    assert pecas["FACE_SANDWICH"].tipo_peca == SIMPLES
    assert pecas["FACE_SANDWICH"].natureza == MATERIAL
    assert pecas["FACE_SANDWICH"].chave_valueset_material == CHAVE_MATERIAL_FACE
    assert pecas["NUCLEO_SANDWICH"].chave_valueset_material == CHAVE_MATERIAL_NUCLEO
    for codigo in ("PAINEL_SANDWICH_1F", "PAINEL_SANDWICH_2F"):
        assert pecas[codigo].tipo_peca == COMPOSTA
        assert pecas[codigo].natureza == CONJUNTO
        assert pecas[codigo].sem_material is True

    dois_faces = session.execute(
        select(DefPecaComponente).where(
            DefPecaComponente.def_peca_pai_id == pecas["PAINEL_SANDWICH_2F"].id
        ).order_by(DefPecaComponente.ordem)
    ).scalars().all()
    assert [componente.formula_esp for componente in dois_faces] == [
        "0.8",
        "PAI_ESP-1.6",
        "0.8",
    ]
    assert [componente.def_peca_componente_id for componente in dois_faces].count(
        pecas["FACE_SANDWICH"].id
    ) == 2

    ligacao = session.execute(
        select(DefPecaOperacao).where(
            DefPecaOperacao.def_peca_id == pecas["FACE_SANDWICH"].id
        )
    ).scalar_one()
    assert ligacao.metodo_calculo == REVESTIMENTO
    assert ligacao.quantidade_base == 1


def test_seed_e_idempotente_e_espera_operacao_quando_em_falta(session) -> None:
    primeiro = seed_pecas_sandwich(session)
    assert primeiro.operacao_revestimento_em_falta is True

    _criar_operacao_revestimento(session)
    segundo = seed_pecas_sandwich(session)
    assert segundo.pecas_criadas == 0
    assert segundo.componentes_criados == 0
    assert segundo.operacao_revestimento_criada is True

    terceiro = seed_pecas_sandwich(session)
    assert terceiro.operacao_revestimento_reutilizada is True
    assert terceiro.componentes_reutilizados == 5
