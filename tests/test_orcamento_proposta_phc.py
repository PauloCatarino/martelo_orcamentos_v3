"""Tests for linking a budget to its PHC proposal number.

The PHC assigns the proposal number and the V3 adopts it: the budget number
becomes ``<ano2><nº4>`` and ``proposta_phc`` keeps the raw PHC number, which
also guards against registering the same budget twice.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    OrcamentoService,
)


@pytest.fixture()
def cliente(session: Session) -> Cliente:
    registo = Cliente(nome="MÓVEIS J.F. VIVA", num_cliente_phc="35")
    session.add(registo)
    session.flush()
    return registo


def _criar(session: Session, cliente: Cliente, **kwargs):
    dados = {
        "cliente_id": cliente.id,
        "obra": "Cozinha",
        "descricao": None,
        "localizacao": None,
        "ref_cliente": "25100010",
    }
    dados.update(kwargs)
    return OrcamentoService(session).criar_orcamento_simples(
        CriarOrcamentoSimplesData(**dados)
    )


def _orcamento(session: Session, orcamento_id: int) -> Orcamento:
    return session.get(Orcamento, orcamento_id)


def test_orcamento_criado_com_numero_do_phc(session: Session, cliente: Cliente):
    """O número vem do PHC (806/2026 -> 260806), não da sequência do V3."""
    criado = _criar(
        session,
        cliente,
        ano=2026,
        num_orcamento="260806",
        proposta_phc="806",
    )
    registo = _orcamento(session, criado.orcamento_id)
    assert registo.num_orcamento == "260806"
    assert registo.proposta_phc == "806"
    assert registo.ano == 2026


def test_orcamento_sem_phc_fica_sem_proposta(session: Session, cliente: Cliente):
    """Fluxo antigo: sem registo no PHC, proposta_phc fica a NULL."""
    criado = _criar(session, cliente)
    assert _orcamento(session, criado.orcamento_id).proposta_phc is None


def test_proposta_phc_vazia_e_guardada_como_null(session: Session, cliente: Cliente):
    criado = _criar(session, cliente, proposta_phc="   ")
    assert _orcamento(session, criado.orcamento_id).proposta_phc is None


def test_numero_do_phc_duplicado_e_recusado(session: Session, cliente: Cliente):
    """O par (ano, número) é único — não dá para registar a mesma proposta."""
    _criar(session, cliente, ano=2026, num_orcamento="260806", proposta_phc="806")
    with pytest.raises(ValueError, match="Já existe o orçamento"):
        _criar(
            session, cliente, ano=2026, num_orcamento="260806", proposta_phc="806"
        )


def test_mesmo_numero_phc_em_anos_diferentes_e_permitido(
    session: Session, cliente: Cliente
):
    """No PHC o OBRANO reinicia por ano: 806/2025 e 806/2026 coexistem."""
    _criar(session, cliente, ano=2025, num_orcamento="250806", proposta_phc="806")
    _criar(session, cliente, ano=2026, num_orcamento="260806", proposta_phc="806")

    numeros = session.execute(
        select(Orcamento.num_orcamento).order_by(Orcamento.num_orcamento)
    ).scalars().all()
    assert numeros == ["250806", "260806"]


def test_proposta_phc_e_pesquisavel(session: Session, cliente: Cliente):
    """A coluna é indexada para se poder ir do nº PHC ao orçamento."""
    _criar(session, cliente, ano=2026, num_orcamento="260806", proposta_phc="806")
    encontrado = session.execute(
        select(Orcamento).where(Orcamento.proposta_phc == "806")
    ).scalar_one()
    assert encontrado.num_orcamento == "260806"
