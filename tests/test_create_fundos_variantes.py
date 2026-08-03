"""Tests for the FUNDOS variants seed script."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.associado_types import DOIS_TOPOS, MEDIDA_TOPO, POR_TOPO
from app.domain.componente_types import FERRAGEM, PECA
from app.domain.peca_natureza_types import MATERIAL, NEUTRA
from app.domain.peca_types import SIMPLES
from app.models import (
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefRegraQuantidade,
)
from scripts.create_fundos_variantes import (
    CODIGO_PECA_UNIOES,
    FUNDOS_COM_PES,
    FUNDOS_SIMPLES,
    REGRA_PES,
    REGRA_UNIOES,
    seed_fundos_variantes,
)


def _catalogo_base(session) -> DefPeca:
    """Operacoes, regras e a peça de unioes que o seed espera encontrar."""
    for codigo in (
        "CORTE_PAINEL",
        "ORLAGEM_PECA",
        "CNC_5_EIXOS",
        "CNC_ABD",
        "SETUP_MAQUINA",
    ):
        session.add(DefOperacao(codigo=codigo, nome=codigo.title(), ativo=True))

    for codigo in (REGRA_PES, REGRA_UNIOES):
        session.add(
            DefRegraQuantidade(codigo=codigo, nome=codigo, expressao="2", ativo=True)
        )

    unioes = DefPeca(
        codigo=CODIGO_PECA_UNIOES,
        nome="Sistemas Uniao",
        grupo="FERRAGENS",
        tipo_peca=SIMPLES,
        natureza=MATERIAL,
        orientacao=NEUTRA,
        ativo=True,
    )
    session.add(unioes)
    session.flush()
    return unioes


def _componentes(session, codigo_peca: str) -> list[DefPecaComponente]:
    peca = session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo_peca)
    ).scalar_one()
    return list(
        session.execute(
            select(DefPecaComponente)
            .where(DefPecaComponente.def_peca_pai_id == peca.id)
            .order_by(DefPecaComponente.ordem)
        ).scalars()
    )


def test_fundos_simples_nascem_com_as_unioes_nos_topos(session) -> None:
    unioes = _catalogo_base(session)

    seed_fundos_variantes(session)

    for seed in FUNDOS_SIMPLES:
        componentes = _componentes(session, seed.codigo)
        assert [c.def_peca_componente_id for c in componentes] == [unioes.id] * 2
        assert [c.prioridade_valueset for c in componentes] == [1, 2]
        for componente in componentes:
            assert componente.tipo_componente == PECA
            assert componente.ativo is True
            assert componente.zona_aplicacao == DOIS_TOPOS
            assert componente.dimensao_referencia == MEDIDA_TOPO
            assert componente.numero_topos == 2
            assert componente.modo_quantidade == POR_TOPO
            assert componente.def_regra_quantidade_id is not None


def test_conjuntos_ficam_so_com_fundo_e_pes(session) -> None:
    unioes = _catalogo_base(session)

    seed_fundos_variantes(session)

    for seed in FUNDOS_COM_PES:
        componentes = _componentes(session, seed.codigo)
        # So' o fundo e os pes: as unioes vem por arrasto, do fundo la dentro.
        assert len(componentes) == 2
        assert [c.tipo_componente for c in componentes] == [PECA, FERRAGEM]
        assert all(c.def_peca_componente_id != unioes.id for c in componentes)


def test_seed_e_idempotente(session) -> None:
    _catalogo_base(session)

    seed_fundos_variantes(session)
    result = seed_fundos_variantes(session)

    assert result.pecas_criadas == 0
    assert result.componentes_criados == 0
    assert result.pecas_reutilizadas == len(FUNDOS_SIMPLES) + len(FUNDOS_COM_PES)
