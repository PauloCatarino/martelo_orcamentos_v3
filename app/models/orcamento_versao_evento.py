"""OrcamentoVersaoEvento - audit log de alteracoes da versao (R2.6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrcamentoVersaoEvento(Base):
    """Um evento de auditoria de uma versao de orcamento (quem/o que/quando)."""

    __tablename__ = "orcamento_versao_eventos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_versao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_versoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
