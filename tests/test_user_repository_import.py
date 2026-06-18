"""Import checks for the User repository."""

from __future__ import annotations


def test_user_repository_imports() -> None:
    from app.repositories.user_repository import UserRepository, UserResumo

    assert UserRepository is not None
    assert UserResumo is not None
