"""Tests for immutable-successor catalog piece revisions."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401
from app.services.def_operacao_service import CriarDefOperacaoData, DefOperacaoService
from app.services.def_peca_componente_service import (
    CriarDefPecaComponenteData,
    DefPecaComponenteService,
)
from app.services.def_peca_operacao_service import (
    CriarDefPecaOperacaoData,
    DefPecaOperacaoService,
)
from app.services.def_peca_revisao_service import DefPecaRevisaoService
from app.services.def_peca_service import CriarDefPecaData, DefPecaService


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_criar_revisao_copia_configuracao_e_desativa_anterior(session) -> None:
    pecas = DefPecaService(session)
    operacoes = DefPecaOperacaoService(session)
    componentes = DefPecaComponenteService(session)
    corte = DefOperacaoService(session).criar_operacao(
        CriarDefOperacaoData(codigo="CORTE_REV", nome="Corte")
    )
    filho = pecas.criar_peca(CriarDefPecaData(codigo="FILHO_REV", nome="Filho"))
    original = pecas.criar_peca(
        CriarDefPecaData(
            codigo="PORTA_REV",
            nome="Porta",
            natureza="CONJUNTO",
            formula_comp="HM-4",
            formula_larg="LM-4",
        )
    )
    operacoes.adicionar_operacao_a_peca(
        CriarDefPecaOperacaoData(
            def_peca_id=original.id,
            def_operacao_id=corte.id,
            quantidade_base=Decimal("2"),
        )
    )
    componentes.criar_componente(
        CriarDefPecaComponenteData(
            def_peca_pai_id=original.id,
            def_peca_componente_id=filho.id,
            quantidade=Decimal("2"),
        )
    )

    resultado = DefPecaRevisaoService(session).criar_revisao(original.id)
    anterior = pecas.repository.get_by_id(original.id)
    nova = pecas.repository.get_by_id(resultado.nova_peca_id)

    assert anterior is not None and anterior.ativo is False
    assert nova is not None and nova.ativo is True
    assert resultado.codigo == "PORTA_REV_R2"
    assert resultado.revisao_numero == 2
    assert resultado.operacoes_copiadas == 1
    assert resultado.componentes_copiados == 1
    assert len(operacoes.listar_operacoes_da_peca(nova.id)) == 1
    assert len(componentes.listar_componentes(nova.id)) == 1


def test_revisoes_formam_uma_cadeia_e_so_a_ultima_pode_avancar(session) -> None:
    original = DefPecaService(session).criar_peca(
        CriarDefPecaData(codigo="LAT_REV", nome="Lateral")
    )
    revisoes = DefPecaRevisaoService(session)
    segunda = revisoes.criar_revisao(original.id)
    terceira = revisoes.criar_revisao(segunda.nova_peca_id)

    cadeia = revisoes.listar_revisoes(terceira.nova_peca_id)
    assert [peca.revisao_numero for peca in cadeia] == [1, 2, 3]
    assert [peca.codigo for peca in cadeia] == ["LAT_REV", "LAT_REV_R2", "LAT_REV_R3"]
    assert [peca.ativo for peca in cadeia] == [False, False, True]

    with pytest.raises(ValueError, match="mais recente"):
        revisoes.criar_revisao(original.id, novo_codigo="RAMO_INVALIDO")


def test_preparar_revisao_mostra_impacto_sem_alterar_dados(session) -> None:
    original = DefPecaService(session).criar_peca(
        CriarDefPecaData(codigo="PREP_REV", nome="Preparar")
    )
    preparacao = DefPecaRevisaoService(session).preparar_revisao(original.id)

    assert preparacao.revisao_atual == 1
    assert preparacao.proxima_revisao == 2
    assert preparacao.codigo_sugerido == "PREP_REV_R2"
    assert preparacao.operacoes_a_copiar == 0
    assert preparacao.componentes_a_copiar == 0
    assert len(DefPecaRevisaoService(session).listar_revisoes(original.id)) == 1
