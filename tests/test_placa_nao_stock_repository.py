"""Tests for the board Não-Stock repository (phase 8W.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.domain.consumos import chave_placa
from app.repositories.orcamento_versao_placa_nao_stock_repository import (
    OrcamentoVersaoPlacaNaoStockRepository,
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


def test_set_e_chaves_ativas(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)

    repo.set_estado(1, "LE01", "AGL 19mm", Decimal("19"), True)
    session.commit()

    assert repo.chaves_ativas(1) == {chave_placa("LE01", "AGL 19mm", Decimal("19"))}
    # esp matches regardless of trailing zeros (canonical key).
    assert chave_placa("LE01", "AGL 19mm", Decimal("19.0000")) in repo.chaves_ativas(1)


def test_unset_remove_a_chave(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    repo.set_estado(1, "LE01", "AGL", Decimal("19"), True)
    session.commit()
    assert repo.chaves_ativas(1)

    repo.set_estado(1, "LE01", "AGL", Decimal("19"), False)
    session.commit()

    assert repo.chaves_ativas(1) == set()
    assert repo.list_by_versao(1) == []


def test_isolado_por_versao(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    repo.set_estado(1, "LE01", "AGL", Decimal("19"), True)
    session.commit()

    assert repo.chaves_ativas(2) == set()
