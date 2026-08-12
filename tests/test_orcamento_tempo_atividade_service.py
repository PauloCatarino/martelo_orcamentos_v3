from __future__ import annotations

from app.models import Cliente, Orcamento, OrcamentoVersao, User
from app.repositories.orcamento_repository import OrcamentoRepository
from app.services.orcamento_tempo_atividade_service import (
    OrcamentoTempoAtividadeService,
)


def _base(session):
    user = User(
        username="paulo",
        nome="Paulo",
        email="paulo@example.test",
        password_hash="x",
        role="USER",
        is_active=True,
    )
    cliente = Cliente(nome="Cliente Tempo")
    session.add_all([user, cliente])
    session.flush()
    orcamento = Orcamento(
        ano=2026,
        num_orcamento="260900",
        cliente_id=cliente.id,
    )
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260900_01",
        estado="Falta Orçamentar",
    )
    session.add(versao)
    session.commit()
    return user, versao


def test_acumula_tempo_por_versao_e_utilizador(session) -> None:
    user, versao = _base(session)
    service = OrcamentoTempoAtividadeService(session)

    assert service.adicionar_segundos(versao.id, user.id, 60) == 60
    assert service.adicionar_segundos(versao.id, user.id, 45) == 105
    assert service.total_da_versao(versao.id) == 105


def test_soma_utilizadores_da_mesma_versao(session) -> None:
    user, versao = _base(session)
    outro = User(
        username="ana",
        nome="Ana",
        email="ana@example.test",
        password_hash="x",
        role="USER",
        is_active=True,
    )
    session.add(outro)
    session.commit()
    service = OrcamentoTempoAtividadeService(session)

    service.adicionar_segundos(versao.id, user.id, 60)
    assert service.adicionar_segundos(versao.id, outro.id, 30) == 90


def test_resumo_do_orcamento_expoe_total_da_versao(session) -> None:
    user, versao = _base(session)
    service = OrcamentoTempoAtividadeService(session)
    service.adicionar_segundos(versao.id, user.id, 75)

    resumo = OrcamentoRepository(session).get_orcamento_by_versao_id(versao.id)

    assert resumo is not None
    assert resumo.tempo_ativo_segundos == 75
