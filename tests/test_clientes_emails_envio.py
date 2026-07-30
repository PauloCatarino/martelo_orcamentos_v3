"""Emails de envio (orçamentos / projeto produção) escolhidos no Martelo."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.clientes_emails import (
    emails_envio_orcamentos,
    emails_envio_projeto_producao,
)
from app.models import Cliente
from app.repositories.cliente_repository import ClienteRepository


def _cliente(**campos):
    base = {
        "email": "geral@cliente.pt",
        "email_orcamentos": None,
        "email_projeto_producao": None,
    }
    base.update(campos)
    return SimpleNamespace(**base)


def test_usa_a_coluna_configurada() -> None:
    cliente = _cliente(
        email_orcamentos="compras@cliente.pt; dir@cliente.pt",
        email_projeto_producao="producao@cliente.pt",
    )
    assert emails_envio_orcamentos(cliente) == "compras@cliente.pt; dir@cliente.pt"
    assert emails_envio_projeto_producao(cliente) == "producao@cliente.pt"


def test_cai_no_email_do_phc_quando_a_coluna_esta_vazia() -> None:
    cliente = _cliente(email_orcamentos="   ")
    assert emails_envio_orcamentos(cliente) == "geral@cliente.pt"
    assert emails_envio_projeto_producao(cliente) == "geral@cliente.pt"


def test_sem_email_nenhum_devolve_vazio() -> None:
    assert emails_envio_orcamentos(_cliente(email=None)) == ""


def test_sincronizacao_phc_nao_apaga_os_emails_escolhidos(session) -> None:
    from app.domain.clientes_phc import DadosClientePHC

    session.add(
        Cliente(
            nome="CLIENTE ANTIGO",
            num_cliente_phc="490",
            is_temporary=False,
            source_system="phc",
            email="geral@cliente.pt",
            email_orcamentos="compras@cliente.pt",
            email_projeto_producao=None,
        )
    )
    session.commit()

    ClienteRepository(session).sincronizar_phc(
        [
            DadosClientePHC(
                num_cliente_phc="490",
                nome="CLIENTE NOVO NOME",
                nome_simplex="CLIENTE",
                morada=None,
                email="novo@cliente.pt",
                pagina_web=None,
                telefone=None,
                telemovel=None,
                info_1=None,
            )
        ]
    )
    session.commit()

    cliente = session.query(Cliente).filter_by(num_cliente_phc="490").one()
    assert cliente.nome == "CLIENTE NOVO NOME"  # o PHC manda no resto
    assert cliente.email == "novo@cliente.pt"
    assert cliente.email_orcamentos == "compras@cliente.pt"  # escolha do Martelo
    # A que estava vazia é semeada com o email do PHC.
    assert cliente.email_projeto_producao == "novo@cliente.pt"


def test_sincronizacao_phc_deixa_simplex_vazio_quando_o_phc_nao_tem(session) -> None:
    from app.domain.clientes_phc import DadosClientePHC

    ClienteRepository(session).sincronizar_phc(
        [
            DadosClientePHC(
                num_cliente_phc="491",
                nome="WERNAGEN - IMOBILIARIA LDA",
                nome_simplex=None,
                morada=None,
                email=None,
                pagina_web=None,
                telefone=None,
                telemovel=None,
                info_1=None,
            )
        ]
    )
    session.commit()

    cliente = session.query(Cliente).filter_by(num_cliente_phc="491").one()
    assert cliente.nome_simplex is None
