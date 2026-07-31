"""Testes do perfil de quem entra.

A password deixou de se verificar aqui: quem a valida e' o MySQL, ao aceitar
(ou recusar) a ligacao com a conta da pessoa. O que sobra e' o perfil.
"""

from __future__ import annotations

import pytest

from app.models import User
from app.services.auth_service import (
    InactiveUserError,
    PerfilEmFaltaError,
    carregar_perfil,
)


class _ScalarResult:
    def __init__(self, value: User | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> User | None:
        return self.value


class _FakeSession:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.user)


def _make_user(is_active: bool = True) -> User:
    return User(
        username="paulo",
        nome="Paulo Catarino",
        email="projetos@lancaencanto.pt",
        password_hash="ja-nao-e-usado",
        role="admin",
        is_active=is_active,
    )


def test_carregar_perfil_devolve_o_utilizador() -> None:
    user = _make_user()

    assert carregar_perfil(_FakeSession(user=user), "paulo") is user


def test_carregar_perfil_recusa_conta_sem_perfil() -> None:
    """Entrar na base nao chega: sem perfil no Martelo, nao se entra."""
    with pytest.raises(PerfilEmFaltaError, match="nao tem perfil"):
        carregar_perfil(_FakeSession(user=None), "estranho")


def test_carregar_perfil_recusa_utilizador_inativo() -> None:
    with pytest.raises(InactiveUserError):
        carregar_perfil(_FakeSession(user=_make_user(is_active=False)), "paulo")
