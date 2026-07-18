"""DefPecaUserPref SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefPecaUserPref(Base):
    """One piece a user keeps visible in their costing library.

    A user without rows sees every active piece (default). Once rows exist,
    only the referenced pieces appear in that user's library; ``favorito``
    marks the ones surfaced in the Favoritos shortcut group.
    """

    __tablename__ = "def_peca_user_prefs"
    __table_args__ = (
        UniqueConstraint("user_id", "def_peca_id", name="uq_def_peca_user_prefs_user_peca"),
        Index("ix_def_peca_user_prefs_user_id", "user_id"),
        Index("ix_def_peca_user_prefs_def_peca_id", "def_peca_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    def_peca_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("def_pecas.id", ondelete="CASCADE"), nullable=False
    )
    favorito: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
