"""Account roles, menu defaults, and V2 import planning."""

from __future__ import annotations

import pytest

from app.models import User
from app.services.permission_service import DEFAULT_USER_PERMISSIONS, is_admin
from scripts.import_users_from_v2 import SourceUser, plan_migration


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _Session:
    def __init__(self, users):
        self.users = users

    def execute(self, _statement):
        return _ScalarRows(self.users)


def _user(username: str, email: str, role: str = "user") -> User:
    return User(
        id=1,
        username=username,
        nome=username,
        email=email,
        password_hash="hash",
        role=role,
        is_active=True,
    )


def _source(username: str, email: str | None, source_id: int = 7) -> SourceUser:
    return SourceUser(
        id=source_id,
        username=username,
        email=email,
        password_hash="bcrypt-hash",
        role="admin",
        is_active=True,
    )


def test_only_admin_role_has_full_access() -> None:
    assert is_admin(_user("admin", "admin@example.test", role="admin")) is True
    assert is_admin(_user("Paulo", "paulo@example.test", role="user")) is False


def test_normal_user_defaults_exclude_technical_configuration() -> None:
    assert DEFAULT_USER_PERMISSIONS["menu.orcamentos"] is True
    assert DEFAULT_USER_PERMISSIONS["menu.producao"] is True
    assert DEFAULT_USER_PERMISSIONS["menu.configuracoes"] is False


def test_import_keeps_existing_identity_and_forces_non_admin_to_user() -> None:
    session = _Session([_user("paulo", "projetos@lancaencanto.pt", role="admin")])
    report = plan_migration(
        session,
        [_source("Paulo", "projetos@lancaencanto.pt", source_id=2)],
        permission_count=3,
    )
    assert report.creates == 0
    assert report.updates == 1
    assert report.users[0].role == "user"


def test_import_rejects_email_owned_by_another_v3_user() -> None:
    session = _Session([_user("existing", "same@example.test")])
    with pytest.raises(ValueError, match="já pertence"):
        plan_migration(
            session,
            [_source("new-user", "same@example.test")],
            permission_count=0,
        )
