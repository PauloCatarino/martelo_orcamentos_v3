"""Tests for the authentication service."""

from __future__ import annotations

import pytest

from app.models import User
from app.services.auth_service import (
    AuthenticationError,
    InactiveUserError,
    authenticate_user,
    verify_password,
)
from scripts.create_initial_users import hash_password


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


def _make_user(password: str = "secret", is_active: bool = True) -> User:
    return User(
        username="paulo",
        nome="Paulo Catarino",
        email="projetos@lancaencanto.pt",
        password_hash=hash_password(password),
        role="admin",
        is_active=is_active,
    )


def test_verify_password_accepts_valid_password() -> None:
    password_hash = hash_password("secret")

    assert verify_password("secret", password_hash) is True


def test_authenticate_user_returns_user_when_credentials_are_valid() -> None:
    user = _make_user(password="secret")
    session = _FakeSession(user=user)

    authenticated_user = authenticate_user(session, "paulo", "secret")

    assert authenticated_user is user


def test_authenticate_user_rejects_missing_user() -> None:
    session = _FakeSession(user=None)

    with pytest.raises(AuthenticationError):
        authenticate_user(session, "missing", "secret")


def test_authenticate_user_rejects_wrong_password() -> None:
    user = _make_user(password="secret")
    session = _FakeSession(user=user)

    with pytest.raises(AuthenticationError):
        authenticate_user(session, "paulo", "wrong-password")


def test_authenticate_user_rejects_inactive_user() -> None:
    user = _make_user(password="secret", is_active=False)
    session = _FakeSession(user=user)

    with pytest.raises(InactiveUserError):
        authenticate_user(session, "paulo", "secret")
