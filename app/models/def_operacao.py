"""DefOperacao SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_maquina import DefMaquina


class DefOperacao(Base):
    """Reusable production operation definition."""

    __tablename__ = "def_operacoes"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_operacoes_codigo"),
        Index("ix_def_operacoes_tipo_operacao", "tipo_operacao"),
        Index("ix_def_operacoes_unidade_calculo", "unidade_calculo"),
        Index("ix_def_operacoes_ativo", "ativo"),
        Index("ix_def_operacoes_maquina_id", "maquina_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_operacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unidade_calculo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tempo_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_setup: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_hora: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_minimo: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    maquina_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_maquinas.id"),
        nullable=True,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    maquina: Mapped["DefMaquina | None"] = relationship(
        "DefMaquina",
        back_populates="operacoes",
    )
