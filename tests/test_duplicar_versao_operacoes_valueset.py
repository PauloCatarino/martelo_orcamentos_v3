"""Duplicar uma versão tem de levar as operações do ValueSet do orçamento.

Sem isto, a versão duplicada nascia com o ValueSet do orçamento vazio de
operações; a herança para o item apagava as que o item trazia e a versão nova
saía MAIS BARATA do que a original (visto no 260877_02: 113 operações → 0).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemValuesetLinha,
    OrcamentoItemValuesetLinhaOperacao,
    OrcamentoValuesetLinha,
    OrcamentoValuesetLinhaOperacao,
    OrcamentoVersao,
)
from app.repositories.orcamento_repository import OrcamentoRepository


def _versao_com_operacoes(session: Session) -> OrcamentoVersao:
    """Uma versão com ValueSet no orçamento e no item, ambos com operações."""
    cliente = Cliente(nome="Cliente Duplicacao", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(ano=2026, num_orcamento="260877", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260877_01",
        estado="Enviado",
        preco_total=Decimal("429.57"),
    )
    session.add(versao)
    session.flush()

    vsl_versao = OrcamentoValuesetLinha(
        orcamento_versao_id=versao.id,
        chave="FERRAGEM_CORREDICA",
        codigo_opcao="CORRED_SILVER",
        nome_opcao="Corrediça Silver",
        padrao=True,
        ordem=1,
        ref_le="FER0006",
        preco_liquido=Decimal("6.3250"),
        ativo=True,
    )
    session.add(vsl_versao)
    session.flush()

    session.add(
        OrcamentoValuesetLinhaOperacao(
            orcamento_valueset_linha_id=vsl_versao.id,
            def_operacao_id=1,
            ordem=1,
            acao="ADICIONAR",
            tempo_por_unidade_minutos=Decimal("1.5"),
            ativo=True,
        )
    )

    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        codigo="RP_01",
        tipo_item="ROUPEIRO_ABRIR",
        item="RP_01",
        quantidade=Decimal("1"),
        unidade="un",
    )
    session.add(item)
    session.flush()

    vsl_item = OrcamentoItemValuesetLinha(
        orcamento_item_id=item.id,
        chave="FERRAGEM_CORREDICA",
        codigo_opcao="CORRED_SILVER",
        padrao=True,
        ordem=1,
        ref_le="FER0006",
        origem_orcamento_valueset_linha_id=vsl_versao.id,
        origem_orcamento_versao_id=versao.id,
        herdado_do_orcamento=True,
        ativo=True,
    )
    session.add(vsl_item)
    session.flush()

    session.add(
        OrcamentoItemValuesetLinhaOperacao(
            orcamento_item_valueset_linha_id=vsl_item.id,
            def_operacao_id=1,
            ordem=1,
            acao="ADICIONAR",
            tempo_por_unidade_minutos=Decimal("1.5"),
            ativo=True,
        )
    )
    session.flush()

    return versao


def _operacoes_da_versao(session: Session, versao_id: int) -> list:
    linhas = session.execute(
        select(OrcamentoValuesetLinha.id).where(
            OrcamentoValuesetLinha.orcamento_versao_id == versao_id
        )
    ).scalars().all()
    if not linhas:
        return []
    return list(
        session.execute(
            select(OrcamentoValuesetLinhaOperacao).where(
                OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id.in_(linhas)
            )
        ).scalars().all()
    )


def test_duplicar_versao_copia_operacoes_do_valueset_do_orcamento(
    session: Session,
) -> None:
    versao = _versao_com_operacoes(session)

    nova = OrcamentoRepository(session).duplicar_versao_profunda(versao.id)
    session.flush()

    operacoes = _operacoes_da_versao(session, nova.orcamento_versao_id)
    assert len(operacoes) == 1
    assert operacoes[0].tempo_por_unidade_minutos == Decimal("1.5")
    # E não roubou a operação à versão de origem.
    assert len(_operacoes_da_versao(session, versao.id)) == 1


def test_duplicar_versao_continua_a_copiar_operacoes_do_valueset_do_item(
    session: Session,
) -> None:
    versao = _versao_com_operacoes(session)

    nova = OrcamentoRepository(session).duplicar_versao_profunda(versao.id)
    session.flush()

    itens = session.execute(
        select(OrcamentoItem.id).where(
            OrcamentoItem.orcamento_versao_id == nova.orcamento_versao_id
        )
    ).scalars().all()
    linhas = session.execute(
        select(OrcamentoItemValuesetLinha.id).where(
            OrcamentoItemValuesetLinha.orcamento_item_id.in_(itens)
        )
    ).scalars().all()
    operacoes = session.execute(
        select(OrcamentoItemValuesetLinhaOperacao).where(
            OrcamentoItemValuesetLinhaOperacao.orcamento_item_valueset_linha_id.in_(
                linhas
            )
        )
    ).scalars().all()

    assert len(operacoes) == 1
