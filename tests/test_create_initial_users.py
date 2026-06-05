"""Tests for the initial users seed script."""

from __future__ import annotations

from app.models import User
from scripts.create_initial_users import (
    ADMIN_EMAIL,
    ADMIN_NOME,
    ADMIN_ROLE,
    ADMIN_USERNAME,
    PAULO_EMAIL,
    PAULO_NOME,
    PAULO_ROLE,
    PAULO_USERNAME,
    ensure_initial_users,
    verify_password,
)


class _ScalarResult:
    def __init__(self, value: User | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> User | None:
        return self.value


class _FakeSession:
    def __init__(self, results: list[User | None]) -> None:
        self.results = results
        self.added: list[User] = []
        self.committed = False
        self.flush_count = 0

    def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.results.pop(0))

    def add(self, value: User) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.committed = True


def test_ensure_initial_users_updates_admin_and_creates_paulo() -> None:
    existing_admin = User(
        username=ADMIN_USERNAME,
        nome="Old Admin",
        email=PAULO_EMAIL,
        password_hash="existing-hash",
        role="old-role",
        is_active=False,
    )
    session = _FakeSession(results=[existing_admin, None])

    result = ensure_initial_users(
        session,
        admin_password="admin-secret",
        paulo_password="paulo-secret",
    )

    assert result.admin_status == "updated"
    assert result.paulo_status == "created"
    assert session.committed is True
    assert session.flush_count == 2
    assert len(session.added) == 1

    assert existing_admin.nome == ADMIN_NOME
    assert existing_admin.email == ADMIN_EMAIL
    assert existing_admin.role == ADMIN_ROLE
    assert existing_admin.is_active is True
    assert existing_admin.password_hash == "existing-hash"

    paulo_user = session.added[0]
    assert paulo_user.username == PAULO_USERNAME
    assert paulo_user.nome == PAULO_NOME
    assert paulo_user.email == PAULO_EMAIL
    assert paulo_user.role == PAULO_ROLE
    assert paulo_user.is_active is True
    assert paulo_user.password_hash != "paulo-secret"
    assert verify_password("paulo-secret", paulo_user.password_hash)


def test_ensure_initial_users_creates_both_users_when_missing() -> None:
    session = _FakeSession(results=[None, None])

    result = ensure_initial_users(
        session,
        admin_password="admin-secret",
        paulo_password="paulo-secret",
    )

    assert result.admin_status == "created"
    assert result.paulo_status == "created"
    assert session.committed is True
    assert len(session.added) == 2

    admin_user, paulo_user = session.added
    assert admin_user.username == ADMIN_USERNAME
    assert admin_user.email == ADMIN_EMAIL
    assert verify_password("admin-secret", admin_user.password_hash)
    assert paulo_user.username == PAULO_USERNAME
    assert paulo_user.email == PAULO_EMAIL
    assert verify_password("paulo-secret", paulo_user.password_hash)


def test_ensure_initial_users_does_not_duplicate_paulo() -> None:
    existing_admin = User(
        username=ADMIN_USERNAME,
        nome=ADMIN_NOME,
        email=ADMIN_EMAIL,
        password_hash="existing-admin-hash",
        role=ADMIN_ROLE,
        is_active=True,
    )
    existing_paulo = User(
        username=PAULO_USERNAME,
        nome=PAULO_NOME,
        email=PAULO_EMAIL,
        password_hash="existing-paulo-hash",
        role=PAULO_ROLE,
        is_active=True,
    )
    session = _FakeSession(results=[existing_admin, existing_paulo])

    result = ensure_initial_users(session)

    assert result.admin_status == "updated"
    assert result.paulo_status == "exists"
    assert session.committed is True
    assert session.added == []
