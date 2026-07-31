"""Authentication service logic.

Quem valida o utilizador e a password e' o **MySQL**: cada pessoa tem a sua
conta, e a app so' consegue abrir a ligacao se as credenciais estiverem certas
(ver ``app.db.session.ligar``). Este modulo trata do que vem a seguir — ir
buscar o perfil (nome, area, permissoes) a` tabela ``users``.

A verificacao de password que aqui vivia foi-se: era uma fechadura ao lado de
uma parede que nao existia, porque a ligacao a` base era a mesma para toda a
gente e estava num ficheiro em cada PC.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


class AuthenticationError(Exception):
    """Raised when user credentials are invalid."""


class InactiveUserError(AuthenticationError):
    """Raised when an inactive user attempts to authenticate."""


class PerfilEmFaltaError(AuthenticationError):
    """A conta existe na base de dados mas nao tem perfil no Martelo."""


def carregar_perfil(session: Session, username: str) -> User:
    """Devolve o perfil de quem acabou de entrar.

    A ligacao ja' esta' aberta com a conta desta pessoa; o que falta e' saber
    quem ela e' para o Martelo. Sem perfil nao se entra: criar um automatico
    daria acesso a quem tem conta na base mas nao devia usar a aplicacao.
    """
    nome_conta = str(username or "").strip()
    user = session.execute(
        select(User).where(func.lower(User.username) == nome_conta.casefold())
    ).scalar_one_or_none()

    if user is None:
        raise PerfilEmFaltaError(
            f"A conta '{nome_conta}' entra na base de dados mas nao tem perfil "
            "no Martelo. Peca ao administrador para a criar em Utilizadores."
        )

    if not user.is_active:
        raise InactiveUserError("Utilizador inativo.")

    return user
