"""Tests for editing a budget's general data (phase 9.0)."""

from __future__ import annotations

import pytest

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    EditarOrcamentoData,
    OrcamentoService,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_orcamento(session) -> tuple[int, int]:
    """Create a simple budget and return its orcamento_id and version id."""
    cliente = Cliente(nome="Cliente X", is_temporary=True)
    session.add(cliente)
    session.flush()

    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente.id,
            obra="Obra Inicial",
            descricao="Descricao Inicial",
            localizacao="Local Inicial",
            ref_cliente="REF-1",
            created_by_id=None,
            ano=2026,
        )
    )
    orcamento = service.list_orcamentos()[0]
    return orcamento.orcamento_id, orcamento.orcamento_versao_id


def test_criar_orcamento_usa_estado_inicial(session) -> None:
    _orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    versao = session.get(OrcamentoVersao, orcamento_versao_id)
    assert versao.estado == ESTADO_INICIAL


def test_editar_orcamento_persiste_os_campos_e_estado(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)
    service = OrcamentoService(session)

    resultado = service.editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova",
            descricao="Descricao Nova",
            localizacao="Local Novo",
            ref_cliente="REF-2",
            estado="Enviado",
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert resultado is True
    atualizado = session.get(Orcamento, orcamento_id)
    assert atualizado.obra == "Obra Nova"
    assert atualizado.descricao == "Descricao Nova"
    assert atualizado.localizacao == "Local Novo"
    assert atualizado.ref_cliente == "REF-2"
    assert session.get(OrcamentoVersao, orcamento_versao_id).estado == "Enviado"


def test_editar_orcamento_guarda_updated_by_id(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        updated_by_id=None,
        orcamento_versao_id=orcamento_versao_id,
    )

    atualizado = session.get(Orcamento, orcamento_id)
    # Optional fields cleared; obra kept.
    assert atualizado.obra == "Obra Nova"
    assert atualizado.descricao is None
    assert atualizado.localizacao is None
    assert atualizado.ref_cliente is None


def test_editar_orcamento_inexistente_devolve_false(session) -> None:
    resultado = OrcamentoService(session).editar_orcamento(
        9999,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        orcamento_versao_id=9999,
    )

    assert resultado is False


def test_editar_orcamento_aceita_obra_vazia(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    resultado = OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="   ",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert resultado is True
    assert session.get(Orcamento, orcamento_id).obra == ""


def test_editar_orcamento_troca_o_cliente(session) -> None:
    outro = Cliente(nome="Cliente Y", is_temporary=True)
    session.add(outro)
    session.flush()

    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
            cliente_id=outro.id,
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert session.get(Orcamento, orcamento_id).cliente_id == outro.id


def test_lista_marca_orcamento_com_preco_manual(session) -> None:
    from app.models import OrcamentoItem
    from decimal import Decimal

    _orcamento_id, orcamento_versao_id = _criar_orcamento(session)
    service = OrcamentoService(session)

    # sem itens manuais -> tem_preco_manual False
    resumo = service.list_orcamentos()[0]
    assert resumo.tem_preco_manual is False

    # adicionar um item com preço manual -> passa a True
    session.add(
        OrcamentoItem(
            orcamento_versao_id=orcamento_versao_id,
            ordem=1,
            item="Externo",
            quantidade=Decimal("1"),
            preco_unitario=Decimal("100"),
            preco_total=Decimal("100"),
            preco_manual=True,
        )
    )
    session.flush()
    resumo = service.list_orcamentos()[0]
    assert resumo.tem_preco_manual is True
