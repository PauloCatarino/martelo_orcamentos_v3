"""Per-user AI profile entries (vocabulary and preferences)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IaPerfilEntrada(Base):
    """One line of what a user taught the assistant.

    Uma linha por expressão: «roupeiro» significa X e procura-se nos campos Y.
    O ``tipo`` diz de que quadro do questionário a linha veio.
    """

    __tablename__ = "ia_perfil_entradas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    expressao: Mapped[str] = mapped_column(String(255), nullable=False)
    significado: Mapped[str | None] = mapped_column(Text, nullable=True)
    campos: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
