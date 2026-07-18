"""Repository for per-user piece library preferences."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import DefPecaUserPref


class DefPecaUserPrefRepository:
    """Repository for DefPecaUserPref operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_user(self, user_id: int) -> list[DefPecaUserPref]:
        """List one user's piece preferences."""
        statement = select(DefPecaUserPref).where(DefPecaUserPref.user_id == user_id)
        return list(self.session.execute(statement).scalars().all())

    def replace_for_user(
        self, user_id: int, selecionadas: set[int], favoritas: set[int]
    ) -> None:
        """Replace one user's preferences with the given selection."""
        self.session.execute(
            delete(DefPecaUserPref).where(DefPecaUserPref.user_id == user_id)
        )
        for def_peca_id in sorted(selecionadas):
            self.session.add(
                DefPecaUserPref(
                    user_id=user_id,
                    def_peca_id=def_peca_id,
                    favorito=def_peca_id in favoritas,
                )
            )
        self.session.flush()

    def delete_for_user(self, user_id: int) -> int:
        """Remove every preference of one user. Returns removed row count."""
        result = self.session.execute(
            delete(DefPecaUserPref).where(DefPecaUserPref.user_id == user_id)
        )
        self.session.flush()
        return int(result.rowcount or 0)
