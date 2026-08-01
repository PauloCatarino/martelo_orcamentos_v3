"""Tests for the VARAO+SUPORTES assembly seed script."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.domain.associado_types import COMP, GERAL, TOTAL
from app.domain.componente_types import PECA
from app.domain.peca_natureza_types import CONJUNTO, FERRAGEM, MATERIAL, NEUTRA
from app.domain.peca_types import COMPOSTA, SIMPLES
from app.models import DefPeca, DefPecaComponente, DefRegraQuantidade
from scripts.configurar_varao_suportes import (
    ASSOCIADOS,
    CODIGO_CONJUNTO,
    configurar_varao_suportes,
)


REGRAS = {
    "VARAO_SPP": "1",
    "SUPORTE_VARAO_CENTRAL": "1 if COMP > 1100 else 0",
    "SUPORTE_TERMINAL_VARAO": "2",
}


def _criar_catalogo(session) -> None:
    """Create the assembly, its hardware pieces and the quantity rules."""
    session.add(
        DefPeca(
            codigo=CODIGO_CONJUNTO,
            nome="Varão",
            grupo="FERRAGENS",
            tipo_peca=COMPOSTA,
            natureza=CONJUNTO,
            orientacao=NEUTRA,
            sem_material=True,
            ativo=True,
        )
    )
    for codigo, natureza in (
        ("VARAO", MATERIAL),
        ("SUPORTE_CENTRAL_VARAO", FERRAGEM),
        ("SUPORTE_LATERAL_VARAO", FERRAGEM),
    ):
        session.add(
            DefPeca(
                codigo=codigo,
                nome=codigo.title(),
                grupo="FERRAGENS",
                tipo_peca=SIMPLES,
                natureza=natureza,
                orientacao=NEUTRA,
                ativo=True,
            )
        )
    for codigo, expressao in REGRAS.items():
        session.add(
            DefRegraQuantidade(
                codigo=codigo, nome=codigo.title(), expressao=expressao, ativo=True
            )
        )
    session.flush()


def _associados(session) -> list[DefPecaComponente]:
    conjunto = session.execute(
        select(DefPeca).where(DefPeca.codigo == CODIGO_CONJUNTO)
    ).scalar_one()
    return list(
        session.execute(
            select(DefPecaComponente)
            .where(DefPecaComponente.def_peca_pai_id == conjunto.id)
            .order_by(DefPecaComponente.ordem)
        ).scalars()
    )


def test_seed_constants() -> None:
    codigos = [seed.codigo_peca for seed in ASSOCIADOS]

    assert codigos == ["VARAO", "SUPORTE_CENTRAL_VARAO", "SUPORTE_LATERAL_VARAO"]
    assert [seed.ordem for seed in ASSOCIADOS] == [1, 2, 3]


def test_seed_monta_os_tres_associados(session) -> None:
    _criar_catalogo(session)

    result = configurar_varao_suportes(session)

    assert result.associados_criados == 3
    assert result.associados_reutilizados == 0

    varao, central, laterais = _associados(session)

    # O varão traz a medida do módulo; as regras leem-na a partir dele.
    assert varao.formula_comp == "LM"
    assert varao.quantidade == Decimal("1.000")
    assert varao.tipo_componente == PECA

    # O suporte central só entra acima de 1100 mm (a regra decide).
    assert central.formula_comp is None
    assert central.quantidade == Decimal("1.000")

    # Os laterais arrancam a 2 por varão.
    assert laterais.quantidade == Decimal("2.000")

    for associado in (varao, central, laterais):
        assert associado.ativo is True
        assert associado.obrigatorio is True
        assert associado.zona_aplicacao == GERAL
        assert associado.dimensao_referencia == COMP
        assert associado.modo_quantidade == TOTAL
        assert associado.numero_topos == 0
        assert associado.prioridade_valueset == 1
        assert associado.def_regra_quantidade_id is not None


def test_cada_associado_fica_ligado_a_sua_regra(session) -> None:
    _criar_catalogo(session)

    configurar_varao_suportes(session)

    regras_por_id = {
        regra.id: regra.codigo
        for regra in session.execute(select(DefRegraQuantidade)).scalars()
    }
    ligacoes = {
        associado.descricao.split()[0]: regras_por_id[
            associado.def_regra_quantidade_id
        ]
        for associado in _associados(session)
    }
    assert ligacoes == {
        "Varao": "VARAO_SPP",
        "Suporte": "SUPORTE_VARAO_CENTRAL",
        "Suportes": "SUPORTE_TERMINAL_VARAO",
    }


def test_seed_e_idempotente(session) -> None:
    _criar_catalogo(session)

    configurar_varao_suportes(session)
    result = configurar_varao_suportes(session)

    assert result.associados_criados == 0
    assert result.associados_reutilizados == 3
    assert len(_associados(session)) == 3


def test_seed_avisa_quando_falta_uma_peca(session) -> None:
    _criar_catalogo(session)
    peca = session.execute(
        select(DefPeca).where(DefPeca.codigo == "SUPORTE_LATERAL_VARAO")
    ).scalar_one()
    session.delete(peca)
    session.flush()

    with pytest.raises(ValueError, match="SUPORTE_LATERAL_VARAO"):
        configurar_varao_suportes(session)
