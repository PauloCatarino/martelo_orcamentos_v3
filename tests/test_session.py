"""Tests for the application session state."""

from __future__ import annotations

from app.core.session import AppSession, app_session
from app.models import User


def _make_user() -> User:
    return User(
        username="paulo",
        nome="Paulo Catarino",
        email="projetos@lancaencanto.pt",
        password_hash="hashed-password",
        role="admin",
        is_active=True,
    )


def test_app_session_imports() -> None:
    assert app_session is not None


def test_set_current_user() -> None:
    session = AppSession()
    user = _make_user()

    session.set_current_user(user)

    assert session.current_user is user
    assert session.is_authenticated() is True


def test_clear_current_user() -> None:
    session = AppSession(current_user=_make_user())

    session.clear_current_user()

    assert session.current_user is None
    assert session.is_authenticated() is False


def test_is_authenticated_without_user() -> None:
    session = AppSession()

    assert session.is_authenticated() is False
