"""Tests for duplicating a budget version (margins inheritance, phase 8T.1).

Uses an in-memory SQLite database; BigInteger primary keys are rendered as
INTEGER on SQLite so autoincrement works (test-only compile rule).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao
from app.repositories.orcamento_repository import OrcamentoRepository


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_orcamento_com_versao(session: Session) -> OrcamentoVersao:
    cliente = Cliente(nome="Cliente Teste", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(ano=2026, num_orcamento="260001", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260001_01",
        estado="Enviado",
        preco_total=Decimal("500.00"),
        tipo_producao_default="SERIE",
        margem_lucro_pct=Decimal("10"),
        margem_mp_pct=Decimal("15"),
        margem_mao_obra_pct=Decimal("5"),
        margem_acabamentos_pct=Decimal("5"),
        custos_administrativos_pct=Decimal("3"),
    )
    session.add(versao)
    session.flush()
    return versao


def test_nova_versao_herda_margens_da_anterior(session: Session) -> None:
    origem = _criar_orcamento_com_versao(session)
    repository = OrcamentoRepository(session)

    criada = repository.criar_nova_versao(origem.id)

    nova = session.get(OrcamentoVersao, criada.orcamento_versao_id)
    assert criada.numero_versao == 2
    assert criada.codigo_versao == "260001_02"
    assert nova.margem_lucro_pct == Decimal("10")
    assert nova.margem_mp_pct == Decimal("15")
    assert nova.margem_mao_obra_pct == Decimal("5")
    assert nova.margem_acabamentos_pct == Decimal("5")
    assert nova.custos_administrativos_pct == Decimal("3")
    # The production default travels with the version; the new version starts
    # with the canonical initial status and records where its price came from.
    assert nova.tipo_producao_default == "SERIE"
    assert nova.estado == ESTADO_INICIAL
    assert nova.preco_total == Decimal("0")
    assert nova.preco_origem == Decimal("500.00")


def test_nova_versao_usa_proximo_numero(session: Session) -> None:
    origem = _criar_orcamento_com_versao(session)
    repository = OrcamentoRepository(session)

    primeira = repository.criar_nova_versao(origem.id)
    segunda = repository.criar_nova_versao(primeira.orcamento_versao_id)

    assert segunda.numero_versao == 3
    assert segunda.codigo_versao == "260001_03"


def test_nova_versao_de_versao_inexistente_falha(session: Session) -> None:
    repository = OrcamentoRepository(session)

    with pytest.raises(ValueError, match="orcamento_versao"):
        repository.criar_nova_versao(999)


def test_get_cliente_id_by_versao(session: Session) -> None:
    origem = _criar_orcamento_com_versao(session)
    repository = OrcamentoRepository(session)

    cliente_id = repository.get_cliente_id_by_versao(origem.id)

    assert cliente_id is not None
    assert repository.get_cliente_id_by_versao(999) is None
