"""Test the customer-of-version read used by the budget report (phase 8W.1)."""

from __future__ import annotations

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao
from app.services.orcamento_service import OrcamentoService


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


def test_email_do_orcamento_usa_o_email_envio_orcamentos(session) -> None:
    """O MÓVEIS J.F. VIVA tinha «Email envio orçamentos» = geral@jfviva.com,
    mas o email do orçamento saía para os dois endereços do PHC: o resumo do
    cliente não trazia o campo e a prioridade caía sempre no PHC."""
    from app.domain.clientes_emails import emails_envio_orcamentos

    cliente = Cliente(
        nome="MÓVEIS J.F. VIVA", num_cliente_phc="35",
        email="geral@jfviva.com; paulo.sousa@jfviva.com",
        email_orcamentos="geral@jfviva.com",
    )
    sem_escolha = Cliente(
        nome="SÓ PHC", num_cliente_phc="36", email="phc@cliente.pt",
    )
    sem_nada = Cliente(nome="SEM EMAIL", num_cliente_phc="37")
    session.add_all([cliente, sem_escolha, sem_nada])
    session.flush()
    versoes = []
    for numero, c in enumerate((cliente, sem_escolha, sem_nada), start=1):
        orcamento = Orcamento(ano=2026, num_orcamento=f"000{numero}", cliente_id=c.id)
        session.add(orcamento)
        session.flush()
        versao = OrcamentoVersao(
            orcamento_id=orcamento.id, numero_versao=1,
            codigo_versao=f"000{numero}_01", estado="ATIVO",
        )
        session.add(versao)
        session.flush()
        versoes.append(versao.id)
    session.commit()

    service = OrcamentoService(session)
    destinos = [
        emails_envio_orcamentos(service.get_cliente_da_versao(versao_id))
        for versao_id in versoes
    ]

    assert destinos == ["geral@jfviva.com", "phc@cliente.pt", ""]


def test_get_cliente_da_versao_inexistente(session) -> None:
    assert OrcamentoService(session).get_cliente_da_versao(9999) is None
