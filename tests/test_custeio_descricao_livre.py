"""Tests for the per-line free-text note (descricao_livre, phase 8V.1)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
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


def _criar_item(session) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=1, ordem=1, tipo_item="OUTRO", item="Item",
        quantidade=Decimal("1"), altura=Decimal("2000"),
        largura=Decimal("1000"), profundidade=Decimal("500"),
    )
    session.add(item)
    session.flush()
    return item.id


def _criar_linha(session, item_id, **fields):
    base = dict(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Lateral",
        quantidade=Decimal("1"), nivel=0, ativo=True,
    )
    base.update(fields)
    linha = OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)
    session.commit()
    return linha


def test_descricao_livre_persiste_numa_peca(session) -> None:
    item_id = _criar_item(session)
    linha = _criar_linha(session, item_id, tipo_linha="PECA", descricao="Lateral")
    service = OrcamentoItemCusteioLinhaService(session)

    service.atualizar_medidas_linha(
        linha.id, descricao_livre="nota do utilizador", propagar_item=False
    )

    atual = OrcamentoItemCusteioLinhaRepository(session).get_by_id(linha.id)
    assert atual.descricao_livre == "nota do utilizador"
    # The piece's own description is NOT touched by the free note.
    assert atual.descricao == "Lateral"


def test_descricao_livre_pode_ser_limpa(session) -> None:
    item_id = _criar_item(session)
    linha = _criar_linha(
        session, item_id, tipo_linha="FERRAGEM", descricao="Pé",
        descricao_livre="antiga",
    )
    service = OrcamentoItemCusteioLinhaService(session)

    service.atualizar_medidas_linha(linha.id, descricao_livre="", propagar_item=False)

    atual = OrcamentoItemCusteioLinhaRepository(session).get_by_id(linha.id)
    assert atual.descricao_livre is None  # empty text clears the note


def test_descricao_livre_nao_e_tocada_ao_editar_medida(session) -> None:
    item_id = _criar_item(session)
    linha = _criar_linha(
        session, item_id, tipo_linha="PECA", descricao="Lateral",
        descricao_livre="manter",
    )
    service = OrcamentoItemCusteioLinhaService(session)

    # Editing a measure (no descricao_livre argument) must keep the note.
    service.atualizar_medidas_linha(linha.id, comp="H", propagar_item=False)

    atual = OrcamentoItemCusteioLinhaRepository(session).get_by_id(linha.id)
    assert atual.descricao_livre == "manter"
    assert atual.comp == "H"


def test_divisao_continua_a_usar_descricao(session) -> None:
    item_id = _criar_item(session)
    linha = _criar_linha(
        session, item_id, tipo_linha="DIVISAO_INDEPENDENTE",
        descricao="Divisão independente",
    )
    service = OrcamentoItemCusteioLinhaService(session)

    # A division's identifying text is its descricao (edited via Descrição livre).
    service.atualizar_medidas_linha(
        linha.id, descricao="Corpo", propagar_item=False
    )

    atual = OrcamentoItemCusteioLinhaRepository(session).get_by_id(linha.id)
    assert atual.descricao == "Corpo"
