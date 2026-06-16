"""Test the customer-of-version read used by the budget report (phase 8W.1)."""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao
from app.services.orcamento_service import OrcamentoService


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_get_cliente_da_versao(session) -> None:
    cliente = Cliente(
        nome="Lança Encanto", morada="Rua A, 1", email="le@example.pt",
        telefone="912345678", num_cliente_phc="C-001",
    )
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(ano=2026, num_orcamento="0001", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id, numero_versao=1, codigo_versao="0001_01",
        estado="ATIVO",
    )
    session.add(versao)
    session.flush()
    session.commit()

    resumo = OrcamentoService(session).get_cliente_da_versao(versao.id)

    assert resumo is not None
    assert resumo.nome == "Lança Encanto"
    assert resumo.morada == "Rua A, 1"
    assert resumo.email == "le@example.pt"
    assert resumo.telefone == "912345678"
    assert resumo.num_cliente == "C-001"


def test_get_cliente_da_versao_inexistente(session) -> None:
    assert OrcamentoService(session).get_cliente_da_versao(9999) is None
