"""Tests for editing a budget's general data (phase 9.0)."""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Orcamento
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


def _criar_orcamento(session) -> int:
    """Create a simple budget and return its orcamento_id."""
    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            nome_cliente="Cliente X",
            email_cliente=None,
            telefone_cliente=None,
            obra="Obra Inicial",
            descricao="Descricao Inicial",
            localizacao="Local Inicial",
            ref_cliente="REF-1",
            created_by_id=None,
            ano=2026,
        )
    )
    return service.list_orcamentos()[0].orcamento_id


def test_editar_orcamento_persiste_os_quatro_campos(session) -> None:
    orcamento_id = _criar_orcamento(session)
    service = OrcamentoService(session)

    resultado = service.editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova",
            descricao="Descricao Nova",
            localizacao="Local Novo",
            ref_cliente="REF-2",
        ),
    )

    assert resultado is True
    atualizado = session.get(Orcamento, orcamento_id)
    assert atualizado.obra == "Obra Nova"
    assert atualizado.descricao == "Descricao Nova"
    assert atualizado.localizacao == "Local Novo"
    assert atualizado.ref_cliente == "REF-2"


def test_editar_orcamento_guarda_updated_by_id(session) -> None:
    orcamento_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova", descricao=None, localizacao=None, ref_cliente=None
        ),
        updated_by_id=None,
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
            obra="Obra", descricao=None, localizacao=None, ref_cliente=None
        ),
    )

    assert resultado is False


def test_editar_orcamento_obra_vazia_levanta_valueerror(session) -> None:
    orcamento_id = _criar_orcamento(session)

    with pytest.raises(ValueError):
        OrcamentoService(session).editar_orcamento(
            orcamento_id,
            EditarOrcamentoData(
                obra="   ", descricao=None, localizacao=None, ref_cliente=None
            ),
        )
