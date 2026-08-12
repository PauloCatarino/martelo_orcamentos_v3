"""Tempo ativo de trabalho por versão de orçamento e utilizador."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrcamentoTempoAtividade(Base):
    """Acumulado de segundos realmente ativos numa versão de orçamento."""

    __tablename__ = "orcamento_tempo_atividade"
    __table_args__ = (
        UniqueConstraint(
            "orcamento_versao_id",
            "user_id",
            name="uq_orc_tempo_versao_user",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    orcamento_versao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_versoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    segundos_ativos: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
