"""Occurrence log of one production work (obra)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProducaoOcorrencia(Base):
    """One line of the obra's diary: quando, quem e o quê.

    Não é auditoria do que o programa mudou — é o registo do que aconteceu na
    vida real: o que o cliente reportou, o que se combinou, o que correu mal.
    """

    __tablename__ = "producao_ocorrencias"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("producao.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    #: Nome de quem escreveu, guardado à cabeça (sobrevive a contas apagadas).
    autor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
