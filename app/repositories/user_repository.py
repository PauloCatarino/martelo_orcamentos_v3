"""Repository for user list reads."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


@dataclass(frozen=True)
class UserResumo:
    """Read model for selecting active users in the UI."""

    id: int
    username: str
    nome: str


class UserRepository:
    """Repository for user read operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_active_users(self) -> list[UserResumo]:
        """List active users ordered by username."""
        rows = (
            self.session.execute(
                select(User)
                .where(User.is_active.is_(True))
                .order_by(User.username.asc())
            )
            .scalars()
            .all()
        )
        return [
            UserResumo(id=user.id, username=user.username, nome=user.nome)
            for user in rows
        ]
