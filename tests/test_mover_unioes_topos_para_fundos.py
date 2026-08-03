"""As unioes nos topos pertencem ao fundo simples, nao ao conjunto FUNDO+PES."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.domain.associado_types import DOIS_TOPOS, GERAL, MEDIDA_TOPO, POR_TOPO, TOTAL
from app.domain.componente_types import PECA
from app.domain.peca_natureza_types import CONJUNTO, MATERIAL, NEUTRA
from app.domain.peca_types import COMPOSTA, SIMPLES
from app.domain.regra_quantidade_types import FIXA as QUANTIDADE_FIXA
from app.models import DefPeca, DefPecaComponente, DefRegraQuantidade
from scripts.mover_unioes_topos_para_fundos import (
    CODIGO_PECA_UNIOES,
    FUNDOS_SIMPLES,
    REGRA_UNIOES,
    mover_unioes_topos_para_fundos,
)


def _peca(session, codigo: str, **campos) -> DefPeca:
    base = {
        "codigo": codigo,
        "nome": codigo,
        "grupo": "FUNDOS",
        "tipo_peca": SIMPLES,
        "natureza": MATERIAL,
        "orientacao": NEUTRA,
        "ativo": True,
    }
    base.update(campos)
    peca = DefPeca(**base)
    session.add(peca)
    session.flush()
    return peca


def _uniao(session, pai: DefPeca, unioes: DefPeca, ordem: int, prioridade: int, ativo=True):
    regra = session.execute(
        select(DefRegraQuantidade).where(DefRegraQuantidade.codigo == REGRA_UNIOES)
    ).scalar_one_or_none()
    componente = DefPecaComponente(
        def_regra_quantidade_id=regra.id if regra is not None else None,
        def_peca_pai_id=pai.id,
        tipo_componente=PECA,
        def_peca_componente_id=unioes.id,
        descricao=f"Unioes prioridade {prioridade}",
        ordem=ordem,
        quantidade=Decimal("1.000"),
        regra_quantidade=QUANTIDADE_FIXA,
        obrigatorio=True,
        ativo=ativo,
        zona_aplicacao=DOIS_TOPOS,
        dimensao_referencia=MEDIDA_TOPO,
        numero_topos=2,
        modo_quantidade=POR_TOPO,
        prioridade_valueset=prioridade,
    )
    session.add(componente)
    session.flush()
    return componente


def _catalogo(session) -> dict:
    """O catalogo tal como estava: unioes no FUNDO_2000 e nos conjuntos."""
    session.add(
        DefRegraQuantidade(
            codigo=REGRA_UNIOES, nome="Uniao topos", expressao="2", ativo=True
        )
    )
    unioes = _peca(session, CODIGO_PECA_UNIOES, grupo="FERRAGENS")

    fundos = {codigo: _peca(session, codigo) for codigo in FUNDOS_SIMPLES}
    # O fundo que o Paulo ja tinha montado a mao.
    _uniao(session, fundos["FUNDO_2000"], unioes, ordem=1, prioridade=1)
    _uniao(session, fundos["FUNDO_2000"], unioes, ordem=2, prioridade=2)

    conjunto = _peca(
        session,
        "FUNDO_2222+PES",
        tipo_peca=COMPOSTA,
        natureza=CONJUNTO,
        sem_material=True,
    )
    session.add(
        DefPecaComponente(
            def_peca_pai_id=conjunto.id,
            tipo_componente=PECA,
            def_peca_componente_id=fundos["FUNDO_2222"].id,
            descricao="Fundo com Orla 2222",
            ordem=1,
            quantidade=Decimal("1.000"),
            regra_quantidade=QUANTIDADE_FIXA,
            obrigatorio=True,
            ativo=True,
            zona_aplicacao=GERAL,
            modo_quantidade=TOTAL,
        )
    )
    session.flush()
    _uniao(session, conjunto, unioes, ordem=2, prioridade=1)
    _uniao(session, conjunto, unioes, ordem=3, prioridade=2)

    return {"unioes": unioes, "fundos": fundos, "conjunto": conjunto}


def _unioes_de(session, peca: DefPeca, unioes: DefPeca) -> list[DefPecaComponente]:
    return list(
        session.execute(
            select(DefPecaComponente)
            .where(
                DefPecaComponente.def_peca_pai_id == peca.id,
                DefPecaComponente.def_peca_componente_id == unioes.id,
            )
            .order_by(DefPecaComponente.ordem)
        ).scalars()
    )


def test_fundos_simples_ficam_com_as_unioes(session) -> None:
    catalogo = _catalogo(session)

    result = mover_unioes_topos_para_fundos(session)

    # Quatro fundos sem unioes x 2 unioes cada; o FUNDO_2000 ja estava certo.
    assert result.unioes_criadas == 8
    assert result.fundos_ja_certos == 1

    for codigo, fundo in catalogo["fundos"].items():
        componentes = _unioes_de(session, fundo, catalogo["unioes"])
        assert [c.prioridade_valueset for c in componentes] == [1, 2], codigo
        for componente in componentes:
            assert componente.ativo is True
            assert componente.zona_aplicacao == DOIS_TOPOS
            assert componente.dimensao_referencia == MEDIDA_TOPO
            assert componente.numero_topos == 2
            assert componente.modo_quantidade == POR_TOPO
            assert componente.def_regra_quantidade_id is not None


def test_conjunto_deixa_de_ter_unioes_ativas(session) -> None:
    catalogo = _catalogo(session)

    result = mover_unioes_topos_para_fundos(session)

    assert result.unioes_desativadas == 2
    assert result.conjuntos_ajustados == 1

    componentes = _unioes_de(session, catalogo["conjunto"], catalogo["unioes"])
    # Continuam la, a mostrar a decisao, mas desligadas: o custeio ignora-as.
    assert len(componentes) == 2
    assert all(componente.ativo is False for componente in componentes)

    # O fundo que entra no conjunto e' que passa a trazer as unioes.
    fundo = catalogo["fundos"]["FUNDO_2222"]
    assert len(_unioes_de(session, fundo, catalogo["unioes"])) == 2


def test_e_idempotente(session) -> None:
    _catalogo(session)

    mover_unioes_topos_para_fundos(session)
    result = mover_unioes_topos_para_fundos(session)

    assert result.unioes_criadas == 0
    assert result.unioes_desativadas == 0
    assert result.conjuntos_ajustados == 0
    assert result.fundos_ja_certos == len(FUNDOS_SIMPLES)


def test_nao_mexe_em_pecas_de_outros_grupos(session) -> None:
    catalogo = _catalogo(session)
    teto = _peca(session, "TETO_2000", grupo="TETOS")
    _uniao(session, teto, catalogo["unioes"], ordem=1, prioridade=1)

    mover_unioes_topos_para_fundos(session)

    componentes = _unioes_de(session, teto, catalogo["unioes"])
    assert [componente.ativo for componente in componentes] == [True]
