"""Tests for the initial admin user script."""

from __future__ import annotations

from scripts.create_admin_user import (
    ADMIN_EMAIL,
    ADMIN_NOME,
    ADMIN_ROLE,
    ADMIN_USERNAME,
    ensure_admin_user,
    verify_password,
)


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class _FakeSession:
    def __init__(self, existing_user: object | None = None) -> None:
        self.existing_user = existing_user
        self.added: list[object] = []
        self.committed = False

    def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.existing_user)

    def add(self, value: object) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.committed = True


def test_ensure_admin_user_creates_user_with_hashed_password() -> None:
    session = _FakeSession()

    created = ensure_admin_user(session, password="secret-password")

    assert created is True
    assert session.committed is True
    assert len(session.added) == 1

    admin_user = session.added[0]
    assert admin_user.username == ADMIN_USERNAME
    assert admin_user.nome == ADMIN_NOME
    assert admin_user.email == ADMIN_EMAIL
    assert admin_user.role == ADMIN_ROLE
    assert admin_user.is_active is True
    assert admin_user.password_hash != "secret-password"
    assert verify_password("secret-password", admin_user.password_hash)


def test_ensure_admin_user_does_not_duplicate_existing_admin() -> None:
    existing_user = object()
    session = _FakeSession(existing_user=existing_user)

    created = ensure_admin_user(session, password="secret-password")

    assert created is False
    assert session.committed is False
    assert session.added == []
