"""Criar utilizador quando a base gere as contas por pessoa.

O caso delicado e' a meio: a conta na base de dados ja' foi criada e o perfil
rebenta a seguir. Sem desfazer, ficava uma conta a entrar no servidor sem
perfil no Martelo — e ninguem dava por ela.
"""

from __future__ import annotations

import pytest

from app.models import User
from app.services import mysql_contas_service, user_admin_service
from app.services.user_admin_service import create_user, reset_password


@pytest.fixture()
def base_com_contas(monkeypatch):
    """A base passa a dizer que tem os procedimentos; regista as chamadas."""
    chamadas: dict[str, list] = {"criar": [], "apagar": [], "repor": []}

    monkeypatch.setattr(mysql_contas_service, "contas_geridas", lambda _s: True)
    monkeypatch.setattr(
        mysql_contas_service,
        "criar_conta",
        lambda _s, **kw: chamadas["criar"].append(kw),
    )
    monkeypatch.setattr(
        mysql_contas_service,
        "apagar_conta",
        lambda _s, **kw: chamadas["apagar"].append(kw),
    )
    monkeypatch.setattr(
        mysql_contas_service,
        "repor_password",
        lambda _s, **kw: chamadas["repor"].append(kw),
    )
    return chamadas


def test_criar_utilizador_cria_tambem_a_conta_na_base(session, base_com_contas) -> None:
    create_user(
        session,
        username="ana",
        nome="Ana Silva",
        email="ana@lancaencanto.pt",
        password="password-comprida",
    )

    assert base_com_contas["criar"] == [
        {"username": "ana", "password": "password-comprida", "admin": False}
    ]
    assert session.query(User).filter_by(username="ana").one().nome == "Ana Silva"


def test_perfil_a_falhar_desfaz_a_conta_criada(session, base_com_contas, monkeypatch) -> None:
    def _rebenta(*_args, **_kwargs):
        raise RuntimeError("a gravar as permissoes correu mal")

    monkeypatch.setattr(user_admin_service, "set_user_permissions", _rebenta)

    with pytest.raises(RuntimeError):
        create_user(
            session,
            username="ana",
            nome="Ana Silva",
            email="ana@lancaencanto.pt",
            password="password-comprida",
        )

    assert base_com_contas["apagar"] == [{"username": "ana"}]
    assert session.query(User).filter_by(username="ana").one_or_none() is None


def test_nome_repetido_nem_chega_a_criar_conta(session, base_com_contas) -> None:
    create_user(
        session,
        username="ana",
        nome="Ana Silva",
        email="ana@lancaencanto.pt",
        password="password-comprida",
    )
    base_com_contas["criar"].clear()

    with pytest.raises(ValueError, match="Já existe"):
        create_user(
            session,
            username="ana",
            nome="Ana Outra",
            email="outra@lancaencanto.pt",
            password="password-comprida",
        )

    assert base_com_contas["criar"] == []


def test_repor_password_vai_a_base_e_nao_ao_hash(session, base_com_contas) -> None:
    create_user(
        session,
        username="ana",
        nome="Ana Silva",
        email="ana@lancaencanto.pt",
        password="password-comprida",
    )
    utilizador = session.query(User).filter_by(username="ana").one()
    hash_antes = utilizador.password_hash

    reset_password(session, utilizador.id, "outra-password-comprida")

    assert base_com_contas["repor"] == [
        {"username": "ana", "password": "outra-password-comprida"}
    ]
    # O hash deixou de mandar em alguma coisa: nao se toca nele.
    assert utilizador.password_hash == hash_antes


def test_sem_procedimentos_continua_como_antes(session, monkeypatch) -> None:
    """A base principal ainda nao os tem — e a app tem de funcionar na mesma."""
    monkeypatch.setattr(mysql_contas_service, "contas_geridas", lambda _s: False)

    def _nao_devia_ser_chamado(*_args, **_kwargs):
        raise AssertionError("nao deve tocar nas contas MySQL")

    monkeypatch.setattr(mysql_contas_service, "criar_conta", _nao_devia_ser_chamado)

    create_user(
        session,
        username="ana",
        nome="Ana Silva",
        email="ana@lancaencanto.pt",
        password="password-comprida",
    )

    utilizador = session.query(User).filter_by(username="ana").one()
    assert utilizador.password_hash  # o hash ainda e' quem manda
